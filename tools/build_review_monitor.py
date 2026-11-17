"""Build a public, source-linked snapshot from an ai4s-crawler checkout."""
import argparse
import csv
import hashlib
import json
import subprocess
from urllib.parse import urlparse
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO = 'https://github.com/BUPT-AI4S/ai4s-crawler/blob/'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def number(value):
    try:
        return int(value) if value is not None and str(value).strip() != '' else None
    except (TypeError, ValueError):
        return None


STATUS_ORDER = {'not_started': 0, 'in_progress': 1, 'complete': 2}


def load_owner_activity(root):
    """Per-owner git activity, produced by tools/build_owner_activity.py."""
    path = Path(root) / 'reviews' / 'owner-activity.json'
    if not path.exists():
        return {'available': False, 'owners': {}, 'generated_at': None, 'history_available': None, 'commit': None, 'commits_scanned': None}
    doc = read_json(path)
    return {'available': True, 'owners': doc.get('owners') or {}, 'generated_at': doc.get('generated_at'),
            'history_available': doc.get('history_available'), 'commit': doc.get('commit'),
            'commits_scanned': doc.get('commits_scanned')}


def classify_owner(row):
    """未开始/进行中/已交齐 for one owner in one year (delivery, not crawl completion)."""
    if not row['delivered']:
        return 'not_started' if row['sources'] else 'unknown'
    if row['delivered'] >= row['sources'] and not row['pending'] and row['official'] >= row['sources'] and not row['open_issues']:
        return 'complete'
    return 'in_progress'


def summarize_owners(sources, activity):
    rows = {}
    for s in sources:
        name = (s.get('owner') or '').strip()
        if not name: continue
        row = rows.setdefault(name, {'owner': name, 'sources': 0, 'delivered': 0, 'official': 0, 'pending': 0, 'open_issues': 0})
        row['sources'] += 1
        if s.get('decisions') is not None: row['delivered'] += 1
        if s.get('official_total') is not None or s.get('reference_check'): row['official'] += 1
        decisions = s.get('decisions') or {}
        row['pending'] += number(decisions.get('pending')) or 0
        row['pending'] += number(decisions.get('unreviewed')) or 0
        if s.get('issues'): row['open_issues'] += 1
    for row in rows.values():
        row['status'] = classify_owner(row)
        act = activity.get(row['owner']) or {}
        row['last_update'] = act.get('last')
        row['commits_7d'] = act.get('commits_7d') or 0
    return sorted(rows.values(), key=lambda r: (STATUS_ORDER.get(r['status'], 3), -r['sources'], r['owner']))


def abstract_not_required(record):
    requirement = record.get('abstract_requirement') or {}
    if not isinstance(requirement, dict): return False
    links = requirement.get('evidence_urls')
    try:
        has_evidence = isinstance(links, list) and any(
            isinstance(u, str) and urlparse(u).scheme == 'https' and urlparse(u).netloc for u in links)
    except ValueError:
        return False
    return (requirement.get('status') == 'not_required'
            and requirement.get('reason') == 'official_source_has_no_independent_abstract'
            and bool(requirement.get('checked_at')) and bool(requirement.get('checked_by'))
            and has_evidence)


def owner_closed_abstract(record, owner):
    """An explicit access-limited exclusion is distinct from an absent publisher abstract."""
    proof = record.get('abstract_requirement')
    if not isinstance(proof, dict): return False
    links = proof.get('evidence_urls')
    try:
        evidence = isinstance(links, list) and any(isinstance(u, str)
            and urlparse(u).scheme == 'https' and urlparse(u).netloc for u in links)
    except ValueError:
        return False
    return (proof.get('status') == 'closed_by_owner'
            and proof.get('reason') == 'access_restricted_excluded_by_owner'
            and proof.get('checked_by') == owner and bool(proof.get('checked_at'))
            and bool(proof.get('user_instruction')) and bool(proof.get('access_status'))
            and evidence)


def full_text_abstract_exemption(review, owner):
    """Close an unavailable publisher abstract only with a completed full-text review."""
    proof = review.get('abstract_requirement') or {}
    metadata = review.get('verified_metadata') or {}
    resolution = review.get('abstract_resolution') or {}
    if not all(isinstance(value, dict) for value in (proof, metadata, resolution)):
        return False
    full_text_url = proof.get('full_text_url')
    if not isinstance(full_text_url, str) or not isinstance(metadata.get('evidence_urls'), list):
        return False
    try:
        full_text = urlparse(full_text_url)
    except ValueError:
        return False
    return (abstract_not_required(review)
            and proof.get('checked_by') == owner
            and proof.get('review_basis') == 'verified_full_text'
            and full_text.scheme == 'https' and bool(full_text.netloc)
            and full_text_url in proof.get('evidence_urls', [])
            and full_text_url in (metadata.get('evidence_urls') or [])
            and metadata.get('abstract_status') == 'not_provided_by_publisher'
            and isinstance(metadata.get('full_text_evidence_location'), str)
            and bool(metadata['full_text_evidence_location'].strip())
            and isinstance(metadata.get('full_text_summary_zh'), str)
            and bool(metadata['full_text_summary_zh'].strip())
            and resolution.get('status') == 'publisher_no_text_abstract_full_text_reviewed'
            and resolution.get('requires_abstract_backfill') is False
            and resolution.get('original_abstract_preserved') is True)


def catalogue_audit_inputs(root, year, source, row):
    """Read a self-contained owner audit in sparse builds, otherwise full source evidence."""
    audit = row.get('catalogue_audit')
    if audit is not None:
        if (not isinstance(audit, dict) or audit.get('source_code') != source['code']
                or audit.get('year') != year or audit.get('owner') != source['owner']
                or audit.get('snapshot_at') != source['snapshot_at']
                or audit.get('details_file') != f"metadata/{source['code']}/{year}/catalogue-reconciliation.json"
                or not isinstance(audit.get('input_main_commit'),str) or len(audit['input_main_commit']) != 40
                or any(c not in '0123456789abcdef' for c in audit['input_main_commit'])
                or not isinstance(audit.get('raw_sha256'),str) or len(audit['raw_sha256']) != 64
                or any(c not in '0123456789abcdef' for c in audit['raw_sha256'])):
            raise ValueError('Invalid self-contained catalogue audit')
        return audit.get('raw_identities'), audit.get('additions'), audit.get('report')
    directory = Path(root) / 'metadata' / source['code'] / str(year)
    return (read_json(directory / 'papers.json'), read_json(directory / 'catalogue-additions.json'),
            read_json(directory / 'catalogue-reconciliation.json'))


def verified_catalogue_normalization(root, year, source, row):
    """Verify a documented nonresearch addition and withdrawn unassigned raw extra."""
    if root is None or type(year) is not int: return False
    code = source['code']
    if not isinstance(code, str) or '/' in code or code in ('.', '..'): return False
    try:
        raw, additions, report = catalogue_audit_inputs(root, year, source, row)
    except (OSError, ValueError, TypeError): return False
    if not isinstance(report, dict) or not isinstance(raw, list) or not isinstance(additions, list): return False
    official = report.get('matched_canonical_records')
    canonical = report.get('canonical_resolution')
    if not isinstance(official, list) or not isinstance(canonical, dict): return False
    if (report.get('source_code') != code or report.get('year') != year
            or report.get('owner') != source['owner'] or report.get('snapshot_at') != source['snapshot_at']
            or report.get('official_total') != source['official_total']
            or canonical.get('status') != 'complete' or canonical.get('canonical_missing') != []
            or canonical.get('canonical_extra') != [] or report.get('raw_page_differences') != []): return False
    def unique(records):
        if not all(isinstance(x, dict) and isinstance(x.get('id'), str) and x['id'] for x in records): return None
        result = {x['id']: x for x in records}
        return result if len(result) == len(records) else None
    raw_by, add_by, official_by = unique(raw), unique(additions), unique(official)
    removed = canonical.get('excluded_raw_ids')
    extras = report.get('raw_only_before_overlay')
    missing = report.get('raw_missing_before_overlay')
    if (raw_by is None or add_by is None or official_by is None
            or not isinstance(removed, list) or not removed or not all(isinstance(x,str) for x in removed)
            or len(set(removed)) != len(removed) or not set(removed) <= raw_by.keys()
            or raw_by.keys() & add_by.keys() or len(raw_by) != source['papers']
            or (raw_by.keys() - set(removed)) | add_by.keys() != official_by.keys()
            or len(official_by) != source['official_total'] or canonical.get('canonical_total') != len(official_by)
            or not isinstance(extras, list) or not all(isinstance(x,dict) for x in extras)
            or {x.get('id') for x in extras} != set(removed) or len(extras) != len(removed)
            or not isinstance(missing, list) or len(missing) != len(additions)
            or not all(isinstance(x,dict) for x in missing)
            or any(x.get('venue') != code or x.get('year') != year for x in raw)): return False
    rec = row.get('catalogue_reconciliation') or {}
    if (rec.get('same_scope_missing') != len(additions) or rec.get('same_scope_extra') != len(removed)
            or rec.get('same_scope_duplicate') != 0 or rec.get('canonical_missing') != 0
            or rec.get('canonical_extra') != 0 or rec.get('canonical_total') != len(official_by)): return False
    for id in removed:
        if not raw_by[id].get('title', '').startswith('WITHDRAWN:'): return False
    if not canonical.get('excluded_raw_reason'): return False
    link = canonical.get('evidence_url')
    if link:
        if (not isinstance(link,str) or not link.startswith('https://www.sciencedirect.com/science/article/pii/')
                or not all(x.get('pii') and link.endswith(x['pii']) for x in extras)): return False
    else:
        for item in extras:
            proof = item.get('withdrawal_evidence')
            if (not isinstance(proof,dict) or proof.get('status') != 'withdrawn_unassigned_online'
                    or proof.get('id') != item['id'] or proof.get('pii') != item.get('pii')
                    or not item.get('pii') or not proof.get('checked_at')
                    or proof.get('checked_by') != source['owner']
                    or not proof.get('publisher_withdrawal_notice')
                    or not isinstance(proof.get('evidence_urls'),list)
                    or not any(isinstance(u,str) and (u.startswith('https://pubmed.ncbi.nlm.nih.gov/')
                        or u.startswith('https://www.journal-of-hepatology.eu/article/')
                        or u.startswith('https://www.sciencedirect.com/science/article/pii/'))
                        for u in proof['evidence_urls'])): return False
    for id, item in add_by.items():
        entry = official_by[id]
        if (item.get('venue') != code or item.get('year') != year
                or item.get('article_type') not in ('Corrigendum', 'Erratum', 'Correction')
                or item.get('screening_disposition') != 'exclude_non_original_corrigendum'
                or item.get('title') != entry.get('title') or item.get('pii') != entry.get('pii')
                or item.get('url') != entry.get('url') or item.get('url') not in item.get('evidence_urls', [])
                or not any(x.get('pii') == item.get('pii') for x in missing if isinstance(x,dict))): return False
    return True


def verified_nonresearch_additions(root, year, source, row):
    """Accept only a complete, identity-matched official overlay of excluded nonresearch items."""
    if root is None or type(year) is not int: return False
    code = source['code']
    if not isinstance(code, str) or '/' in code or code in ('.', '..'): return False
    try:
        raw, additions, report = catalogue_audit_inputs(root, year, source, row)
    except (OSError, ValueError, TypeError):
        return False
    if (not isinstance(raw, list) or not isinstance(additions, list) or not additions
            or not isinstance(report, dict) or not isinstance(report.get('rows'), list)
            or not isinstance(report.get('missing'), list)):
        return False
    if (report.get('source_code') != code or report.get('year') != year
            or report.get('owner') != source['owner']
            or report.get('snapshot_at') != source['snapshot_at']
            or report.get('official_total') != source['official_total']
            or report.get('extra') != [] or report.get('duplicates') != 0):
        return False
    def ids(records):
        values = [r.get('id') for r in records if isinstance(r, dict)]
        if (len(values) != len(records) or not all(isinstance(v, str) and v for v in values)
                or len(set(values)) != len(values)):
            return None
        return set(values)
    raw_ids, add_ids, official_ids = ids(raw), ids(additions), ids(report['rows'])
    if (raw_ids is None or add_ids is None or official_ids is None
            or len(raw_ids) != source['papers'] or raw_ids & add_ids
            or raw_ids | add_ids != official_ids
            or len(official_ids) != source['official_total']
            or not all(isinstance(v, str) for v in report['missing'])
            or len(report['missing']) != len(additions)
            or set(report['missing']) != add_ids
            or any(r.get('venue') != code or r.get('year') != year for r in raw)):
        return False
    reconciliation = row.get('catalogue_reconciliation') or {}
    if (reconciliation.get('same_scope_missing') != len(additions)
            or reconciliation.get('verified_nonresearch_additions') != len(additions)
            or reconciliation.get('canonical_unresolved_missing') != 0):
        return False
    nonresearch = {'Research Highlight', 'Milestone', 'Milestones', 'Nature Briefing',
                   'Author Correction', 'Publisher Correction', 'Correction',
                   'Research Briefing', 'Editorial', 'News', 'News & Views', 'Comment'}
    official = {r['id']: r for r in report['rows']}
    for record in additions:
        proof = record.get('catalogue_supplement')
        entry = official[record['id']]
        if not isinstance(proof, dict): return False
        links = proof.get('evidence_urls')
        if (record.get('venue') != code or record.get('year') != year
                or record.get('document_type') not in nonresearch
                or record.get('document_type') != entry.get('type')
                or not record.get('title') or record['title'] != entry.get('title')
                or record.get('url') != entry.get('url')
                or record.get('published') != entry.get('date')
                or proof.get('owner') != source['owner']
                or proof.get('snapshot_at') != source['snapshot_at']
                or not proof.get('checked_at')
                or proof.get('reason') != 'official_catalogue_item_missing_from_fixed_raw'
                or proof.get('disposition') not in ('exclude_nonoriginal',
                    'exclude_nonoriginal_research_highlight')
                or not isinstance(links, list) or entry.get('url') not in links):
            return False
        try:
            parsed = urlparse(record['url'])
            if parsed.scheme != 'https' or not parsed.netloc: return False
        except ValueError:
            return False
    return True


def verified_reference_catalogue(root, year, source, row):
    """Close a historical gap only after exact, current-owner reference reconciliation."""
    if root is None or type(year) is not int or source.get('official_total') is not None: return False
    check = source.get('reference_check')
    if not isinstance(check, dict) or check != row.get('reference_check'): return False
    if (check.get('status') != 'complete' or check.get('unresolved') != 0
            or check.get('total') != source.get('papers') or not check.get('scope')): return False
    try:
        raw, additions, report = catalogue_audit_inputs(root, year, source, row)
    except (OSError, ValueError, TypeError): return False
    if (not isinstance(raw, list) or additions != [] or not isinstance(report, dict)
            or report.get('source_code') != source['code'] or report.get('year') != year
            or report.get('owner') != source['owner'] or report.get('snapshot_at') != source['snapshot_at']
            or report.get('reference_check') != check): return False
    matched = report.get('matched_reference_ids')
    if not isinstance(matched, list) or any(not isinstance(x, str) or not x for x in matched): return False
    if any(not isinstance(x, dict) or x.get('venue') != source['code'] or x.get('year') != year
            or not isinstance(x.get('id'), str) or not x['id'] for x in raw): return False
    ids = [x['id'] for x in raw]
    reconciliation = row.get('catalogue_reconciliation')
    return (len(ids) == len(set(ids)) == len(matched) == len(set(matched)) == source['papers']
            and set(ids) == set(matched) and isinstance(reconciliation, dict)
            and all(reconciliation.get(k) == 0 for k in ('same_scope_missing','same_scope_extra','same_scope_duplicate')))


def verified_audited_catalogue(root, year, source, row):
    """Close authorized Nydiii 2026 history only after exact per-record audits."""
    if root is None or type(year) is not int or year != 2026 or source.get('owner') != '南耀笛': return False
    try:
        raw, additions, report = catalogue_audit_inputs(root, year, source, row)
    except (OSError, ValueError, TypeError): return False
    if (not isinstance(report, dict) or report.get('source_code') != source['code']
            or report.get('year') != year or report.get('owner') != source['owner']
            or report.get('snapshot_at') != source['snapshot_at']
            or report.get('extra') != [] or report.get('duplicates') != 0
            or report.get('unresolved') != [] or not report.get('scope')): return False
    total = source.get('official_total')
    if total is not None:
        if report.get('official_total') != total or report['scope'] != source.get('official_scope'): return False
    else:
        check = source.get('reference_check')
        if (not isinstance(check, dict) or check != row.get('reference_check')
                or check != report.get('reference_check') or check.get('status') != 'complete'
                or check.get('unresolved') != 0 or not check.get('scope')
                or report['scope'] != check['scope']): return False
        total = check.get('total')
    if type(total) is not int or total < 0 or report.get('normalized_count') != total: return False
    def index(records):
        if not isinstance(records, list) or not all(isinstance(z,dict)
                and isinstance(z.get('id'),str) and z['id'] and z.get('title') for z in records): return None
        result = {z['id']:z for z in records}
        return result if len(result) == len(records) else None
    rb, ab, cb, eb = (index(x) for x in (raw, additions, report.get('canonical_records'), report.get('scope_exclusions')))
    if (any(x is None for x in (rb,ab,cb,eb)) or len(rb) != source['papers']
            or rb.keys() & ab.keys() or not eb.keys() <= rb.keys()
            or (rb.keys() - eb.keys()) | ab.keys() != cb.keys() or len(cb) != total
            or any(z.get('venue') != source['code'] or z.get('year') != year for z in raw)
            or not isinstance(report.get('missing'), list) or len(report['missing']) != len(ab)
            or not all(isinstance(k,str) and k for k in report['missing'])
            or set(report['missing']) != ab.keys()): return False
    def proof(z):
        if z.get('checked_by') != source['owner'] or not z.get('checked_at'): return False
        links = z.get('evidence_urls')
        try:
            return isinstance(links,list) and bool(links) and all(isinstance(u,str)
                and urlparse(u).scheme == 'https' and urlparse(u).netloc for u in links)
        except ValueError: return False
    for key,z in ab.items():
        if (not proof(z) or z.get('venue') != source['code'] or z.get('year') != year
                or z['title'] != cb[key]['title'] or not z.get('published')
                or z.get('url') != cb[key].get('url') or z['url'] not in z['evidence_urls']): return False
    for key,z in eb.items():
        status, verified = z.get('status'), z.get('verified_year')
        if not proof(z) or z['title'] != rb[key]['title']: return False
        if status in ('different_formal_year','different_publisher_published_year'):
            if type(verified) is not int or verified == year or not z.get('verified_volume'): return False
        elif status == 'unassigned_formal_volume':
            if verified is not None or z.get('verified_volume') is not None: return False
        else: return False
    rec = row.get('catalogue_reconciliation')
    return (isinstance(rec,dict) and rec.get('normalized_count') == total
            and rec.get('same_scope_missing') == len(ab) and rec.get('same_scope_extra') == 0
            and rec.get('same_scope_duplicate') == 0 and rec.get('canonical_unresolved_missing') == 0)


def historical_abstract_gap_resolved(source, row, candidates, completed_reviews, root=None, year=None):
    """Resolve only an explicitly audited historical full-catalogue abstract gap."""
    resolution = row.get('collection_state_resolution')
    if not isinstance(resolution, dict): return False
    if (source['state'] != 'abstract_incomplete' or source['issues']
            or row.get('owner') != source['owner']
            or resolution.get('status') != 'resolved_for_candidate_review'
            or resolution.get('original_state') != source['state']
            or resolution.get('reason') not in ('full_catalogue_abstract_gap_candidates_complete',
                'full_catalogue_with_nonresearch_additions_candidates_complete',
                'full_catalogue_with_documented_normalization_candidates_complete',
                'full_catalogue_no_candidates',
                'full_reference_catalogue_candidates_complete',
                'full_audited_catalogue_candidates_complete')
            or resolution.get('checked_by') != source['owner']
            or not resolution.get('checked_at')
            or source['abstract_supplement_required'] != 0
            or not (source['official_scope'] or (resolution.get('reason') in ('full_reference_catalogue_candidates_complete',
                    'full_audited_catalogue_candidates_complete')
                and (source.get('reference_check') or {}).get('scope')))):
        return False
    links = resolution.get('evidence_urls')
    try:
        if not isinstance(links, list) or not any(isinstance(u, str) and urlparse(u).scheme == 'https'
                and urlparse(u).netloc for u in links): return False
    except ValueError:
        return False
    reconciliation = row.get('catalogue_reconciliation')
    if not isinstance(reconciliation, dict): return False
    if resolution['reason'] in ('full_catalogue_abstract_gap_candidates_complete', 'full_catalogue_no_candidates'):
        if (source['official_total'] != source['papers']
                or any(reconciliation.get(k) != 0 for k in ('same_scope_missing','same_scope_extra','same_scope_duplicate'))): return False
    elif resolution['reason'] == 'full_audited_catalogue_candidates_complete':
        if not verified_audited_catalogue(root, year, source, row): return False
    elif resolution['reason'] == 'full_reference_catalogue_candidates_complete':
        if not verified_reference_catalogue(root, year, source, row): return False
    elif resolution['reason'] == 'full_catalogue_with_documented_normalization_candidates_complete':
        if not verified_catalogue_normalization(root, year, source, row): return False
    elif any(reconciliation.get(k) != 0 for k in ('same_scope_extra', 'same_scope_duplicate')): return False
    elif not verified_nonresearch_additions(root, year, source, row):
        return False
    if reconciliation.get('current_raw_count') != source['papers']: return False
    records = [r for r in candidates if isinstance(r, dict) and r.get('venue') == source['code']]
    ids = [r.get('id') for r in records]
    if not ids:
        return (resolution['reason'] == 'full_catalogue_no_candidates'
                and source.get('candidates') == 0
                and row.get('candidate_count') == 0
                and row.get('own_review_count') == 0
                and row.get('work_status') == 'complete'
                and row.get('own_review_counts') == dict.fromkeys(('include','exclude','pending','unreviewed'), 0)
                and not any(key[0] == source['code'] for key in completed_reviews)
                and not any((source['decisions'] or {}).values()))
    if resolution['reason'] == 'full_catalogue_no_candidates': return False
    if not all(ids) or len(set(ids)) != len(ids): return False
    decisions = source['decisions'] or {}
    return (not decisions.get('pending') and not decisions.get('unreviewed')
            and all((source['code'], key) in completed_reviews for key in ids))


def current_review_scopes(root, year, sources, snapshot, candidates):
    """Validate an owner's explicit batch scope against the current candidate identities."""
    scopes, documents = {}, {}
    captured_at = snapshot.get('captured_at')
    if not captured_at:
        return scopes
    for path in sorted((root / 'reviews' / str(year) / 'feedback').glob('*.json')):
        document = read_json(path)
        for row in document if isinstance(document, list) else [document]:
            if not isinstance(row, dict) or row.get('year') != year:
                continue
            code = row.get('source_code')
            source = sources.get(code)
            proof = row.get('review_scope')
            if (not source or not isinstance(proof, dict)
                    or row.get('owner') != source['owner'] or row.get('snapshot_at') != captured_at
                    or proof.get('status') != 'current_candidates_and_verified_additions'
                    or proof.get('checked_by') != source['owner'] or not proof.get('checked_at')
                    or proof.get('candidate_file') != f'metadata/{year}/ai4s.json'
                    or not proof.get('scope_instruction') or not proof.get('audit_file')):
                continue
            rel = proof.get('review_file')
            if not isinstance(rel, str):
                continue
            parts = Path(rel).parts
            if (len(parts) != 3 or parts[:2] != ('reviews', str(year))
                    or Path(rel).suffix != '.json' or not (root / rel).is_file()
                    or not (root / rel).resolve().is_relative_to((root / 'reviews' / str(year)).resolve())):
                continue
            ids = [r.get('id') for r in candidates if isinstance(r, dict)
                   and r.get('year') == year and r.get('venue') == code]
            if not all(ids) or len(set(ids)) != len(ids):
                continue
            digest = hashlib.sha256(json.dumps(sorted(ids), ensure_ascii=False,
                                              separators=(',', ':')).encode()).hexdigest()
            if type(proof.get('candidate_count')) is not int or proof.get('candidate_count') != len(ids) or proof.get('candidate_ids_sha256') != digest:
                continue
            if rel not in documents:
                documents[rel] = read_json(root / rel)
            records = documents[rel]
            if not isinstance(records, list):
                continue
            own = [r for r in records if isinstance(r, dict) and r.get('year') == year
                   and r.get('venue') == code]
            reviews = [r.get('ai4s_review') for r in own]
            own_ids = [r.get('id') for r in own]
            if (not all(own_ids) or len(set(own_ids)) != len(own_ids) or not set(ids).issubset(own_ids)
                    or any(not isinstance(r, dict) or r.get('owner') != source['owner']
                           or r.get('snapshot_at') != captured_at
                           or r.get('decision') not in ('include', 'exclude', 'pending', 'unreviewed')
                           for r in reviews)):
                continue
            scopes[code] = {'review_file': rel, 'feedback_file': path.relative_to(root).as_posix(),
                            'candidate_ids': set(ids), 'proof': proof}
    return scopes


def build(root):
    root = Path(root)
    try:
        commit = subprocess.check_output(['git', '-C', str(root), 'rev-parse', 'HEAD'], text=True, stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        commit = None
    ref = commit or 'main'
    venues = {}
    csv_path = root / 'reviews/venue-review.csv'
    if csv_path.exists():
        with csv_path.open(encoding='utf-8-sig', newline='') as f:
            venues = {row['source_code']: row for row in csv.DictReader(f) if row.get('source_code')}
    activity = load_owner_activity(root)
    years, merged = [], {}
    for year_dir in sorted((root / 'metadata').glob('[0-9][0-9][0-9][0-9]')):
        if not year_dir.is_dir(): continue
        snapshot_path = year_dir / 'snapshot.json'
        candidate_path = year_dir / 'ai4s.json'
        if not snapshot_path.exists() and not candidate_path.exists(): continue
        snapshot = read_json(snapshot_path) if snapshot_path.exists() else {'year': int(year_dir.name), 'sources': []}
        year = snapshot.get('year')
        if not isinstance(year, int) or year != int(year_dir.name) or not isinstance(snapshot.get('sources'), list):
            raise ValueError(f'Invalid snapshot: {snapshot_path}')
        assignments_path = root / 'reviews' / f'source-assignments-{year}.json'
        assignments = None
        if assignments_path.exists():
            assignment_doc = read_json(assignments_path)
            if assignment_doc.get('year') != year or not isinstance(assignment_doc.get('sources'), list):
                raise ValueError(f'Invalid source assignments: {assignments_path}')
            assignments = {r['code']: r for r in assignment_doc['sources']}
            if len(assignments) != len(assignment_doc['sources']): raise ValueError('Duplicate source assignments')
        candidate_counts, candidate_missing = Counter(), Counter()
        candidate_records = []
        if candidate_path.exists():
            candidate_records = read_json(candidate_path)
            if not isinstance(candidate_records, list): raise ValueError(f'Invalid AI4S candidates: {candidate_path}')
            for record in candidate_records:
                if not isinstance(record, dict) or record.get('year') != year or not record.get('venue'): continue
                code = record['venue']; candidate_counts[code] += 1
                abstract = record.get('abstract')
                if not isinstance(abstract, str) or not abstract.strip(): candidate_missing[code] += 1
        if not snapshot_path.exists():
            codes = assignments.keys() if assignments is not None else candidate_counts.keys()
            snapshot['sources'] = [{'source': code, 'state': 'unknown'} for code in codes]
        source_map = {}
        for item in snapshot['sources']:

            code = item.get('source')
            if not code: continue
            if assignments is not None and code not in assignments: continue
            info = venues.get(code, {})
            assignment = assignments.get(code, {}) if assignments is not None else {}
            papers = number(item.get('papers'))
            with_abstract = number(item.get('with_abstract'))
            papers_missing = papers - with_abstract if papers is not None and with_abstract is not None and 0 <= with_abstract <= papers else None
            source_map[code] = {'code':code, 'title':assignment.get('title') or info.get('title') or code, 'owner':assignment.get('owner') or ((info.get('owner') or '') if year == 2024 and assignments is None else ''),
                'venue_decision':('清单保留' if assignments is not None else (info.get('是否建议纳入') or '') if year == 2024 else ''), 'state':item.get('state') or 'unknown',
                'papers':papers, 'papers_missing_abstract':papers_missing, 'snapshot_candidates':number(item.get('ai4s')), 'candidates':candidate_counts[code] if candidate_path.exists() else number(item.get('ai4s')), 'missing_abstract':candidate_missing[code] if candidate_path.exists() else None,
                'official_total':None, 'official_scope':'', 'reference_check':None, 'coverage_note':'', 'evidence_urls':[], 'decisions':None,
                'issues':[], 'actions':[], 'files':[], 'snapshot_at':snapshot.get('captured_at')}
        review_dir = root / 'reviews' / str(year)
        scopes = current_review_scopes(root, year, source_map, snapshot, candidate_records)
        for code, scope in scopes.items():
            source_map[code].update(active_review_file=scope['review_file'],
                                    catalogue_reference_records=0, historical_review_files=[])
        counts, seen, conflicts = {}, {}, set()
        candidate_keys = {(r.get('venue'), r.get('id')) for r in candidate_records
                          if isinstance(r, dict) and r.get('year') == year and r.get('id')}
        unsynced_reviews = {}
        final_reviews, final_review_sources = {}, set()
        candidate_abstracts = {(r.get('venue'), r.get('id')) for r in candidate_records
                               if isinstance(r, dict) and r.get('year') == year and r.get('id')
                               and isinstance(r.get('abstract'), str) and r['abstract'].strip()}
        abstract_exemption_reviews = set()
        full_text_exemption_reviews = {}
        owner_closed_reviews = {}
        completed_reviews = set()
        recovered_abstract_reviews = {}
        for path in sorted(review_dir.glob('*.json')):
            records = read_json(path)
            if not isinstance(records, list): continue
            for record in records:
                if not isinstance(record, dict) or record.get('year') != year: continue
                code = record.get('venue'); review = record.get('ai4s_review') or {}
                if code not in source_map or not isinstance(review, dict): continue
                scope = scopes.get(code)
                rel = path.relative_to(root).as_posix()
                if scope and rel != scope['review_file']:
                    historical = source_map[code]['historical_review_files']
                    if rel not in historical: historical.append(rel)
                    continue
                key = (code, record.get('id'))
                if not key[1]: continue
                decision = review.get('decision')
                if (snapshot.get('captured_at') and review.get('snapshot_at') == snapshot.get('captured_at')
                        and review.get('owner') == source_map[code]['owner']
                        and decision in ('include','exclude','pending','unreviewed')):
                    final_review_sources.add(code)
                    entry = final_reviews.setdefault(key, {'decisions': set(), 'has_abstract': key in candidate_abstracts})
                    entry['decisions'].add(decision)
                    verified = review.get('verified_metadata')
                    verified_abstract = verified.get('abstract') if isinstance(verified, dict) else None
                    entry['has_abstract'] |= any(isinstance(a, str) and bool(a.strip()) for a in (record.get('abstract'), verified_abstract))
                if (candidate_path.exists() and key not in candidate_keys and snapshot.get('captured_at')
                        and review.get('snapshot_at') == snapshot.get('captured_at')
                        and review.get('owner') == source_map[code]['owner']
                        and decision in ('include','exclude','pending','unreviewed')):
                    entry = unsynced_reviews.setdefault(key, {'decisions': set(), 'has_abstract': False})
                    entry['decisions'].add(decision)
                    verified = review.get('verified_metadata')
                    verified_abstract = verified.get('abstract') if isinstance(verified, dict) else None
                    entry['has_abstract'] |= any(isinstance(a, str) and bool(a.strip())
                                                 for a in (record.get('abstract'), verified_abstract))
                metadata = review.get('verified_metadata')
                if (decision in ('include', 'exclude', 'pending', 'unreviewed')
                        and snapshot.get('captured_at')
                        and review.get('snapshot_at') == snapshot['captured_at']
                        and review.get('owner') == source_map[code]['owner']
                        and isinstance(metadata, dict)
                        and isinstance(metadata.get('abstract'), str) and metadata['abstract'].strip()):
                    links = metadata.get('evidence_urls')
                    try:
                        has_evidence = isinstance(links, list) and any(isinstance(u, str)
                            and urlparse(u).scheme == 'https' and urlparse(u).netloc for u in links)
                    except ValueError:
                        has_evidence = False
                    if has_evidence:
                        recovered_abstract_reviews.setdefault(key, set()).add(metadata['abstract'].strip())
                queue = review.get('review_scope')
                if (scope and key[1] not in scope['candidate_ids']
                        and decision in ('pending', 'unreviewed') and isinstance(queue, dict)
                        and queue.get('status') == 'reference_only'
                        and queue.get('reason') == 'unverified_catalogue_record_outside_current_candidates'
                        and queue.get('checked_by') == source_map[code]['owner']
                        and queue.get('checked_at') and queue.get('audit_file') == scope['proof']['audit_file']):
                    source_map[code]['catalogue_reference_records'] += 1
                    counts.setdefault(code, Counter())
                    if rel not in source_map[code]['files']: source_map[code]['files'].append(rel)
                    continue
                if (decision == 'include' and snapshot.get('captured_at')
                        and review.get('snapshot_at') == snapshot.get('captured_at')
                        and review.get('owner') == source_map[code]['owner']
                        and full_text_abstract_exemption(review, source_map[code]['owner'])):
                    full_text_exemption_reviews[key] = review['abstract_requirement']
                if (decision == 'exclude' and review.get('snapshot_at') == snapshot.get('captured_at')
                        and snapshot.get('captured_at') and review.get('owner') == source_map[code]['owner']
                        and owner_closed_abstract(review, source_map[code]['owner'])):
                    owner_closed_reviews[key] = review['abstract_requirement']
                if (decision in ('include', 'exclude') and snapshot.get('captured_at')
                        and review.get('snapshot_at') == snapshot.get('captured_at')
                        and review.get('owner') == source_map[code]['owner']):
                    completed_reviews.add(key)
                if (decision == 'exclude' and snapshot.get('captured_at')
                        and review.get('snapshot_at') == snapshot.get('captured_at')
                        and review.get('owner') == source_map[code]['owner']
                        and abstract_not_required({'abstract_requirement': review.get('abstract_requirement')})):
                    abstract_exemption_reviews.add(key)
                if review.get('snapshot_at') != snapshot.get('captured_at'):
                    warning = '逐篇交付与当前采集快照不同或未标注，需核对批次后再比较。'
                    if warning not in source_map[code]['issues']:
                        source_map[code]['issues'].append(warning)
                        source_map[code]['actions'].append('核对逐篇交付与采集快照的批次及覆盖范围。')
                if key in seen:
                    if seen[key] != decision and key not in conflicts:
                        if seen[key] in ('include','exclude','pending','unreviewed'): counts[code][seen[key]] -= 1
                        conflicts.add(key)
                        warning = '同一论文的交付判定存在冲突，冲突记录不计入统计。'
                        if warning not in source_map[code]['issues']:
                            source_map[code]['issues'].append(warning)
                            source_map[code]['actions'].append('由负责人核对重复论文的不同判定。')
                    continue
                seen[key] = decision
                if decision in ('include','exclude','pending','unreviewed'):
                    counts.setdefault(code, Counter())[decision] += 1
                    rel = path.relative_to(root).as_posix()
                    if rel not in source_map[code]['files']: source_map[code]['files'].append(rel)
        for code, count in counts.items(): source_map[code]['decisions'] = {k:count[k] for k in ('include','exclude','pending','unreviewed')}
        unsynced_included, unsynced_missing = Counter(), Counter()
        final_included, final_missing = Counter(), Counter()
        for (code, _), entry in final_reviews.items():
            if entry['decisions'] == {'include'}:
                final_included[code] += 1
                if year != 2024 and not entry['has_abstract']: final_missing[code] += 1
        for (code, _), entry in unsynced_reviews.items():
            if entry['decisions'] != {'include'}: continue
            unsynced_included[code] += 1
            if not entry['has_abstract']: unsynced_missing[code] += 1
        # Keep physical missingness, but distinguish verified non-actionable records.
        no_abstract_required = Counter()
        full_text_reviewed = Counter()
        recovered_abstracts = Counter()
        owner_closed = Counter()
        for record in candidate_records:
            if not isinstance(record, dict) or record.get('year') != year: continue
            key = (record.get('venue'), record.get('id'))
            abstract = record.get('abstract')
            if (key not in conflicts and len(recovered_abstract_reviews.get(key, ())) == 1
                    and (not isinstance(abstract, str) or not abstract.strip())):
                recovered_abstracts[key[0]] += 1
            elif (key in abstract_exemption_reviews and key not in conflicts and seen.get(key) == 'exclude'
                    and (not isinstance(abstract, str) or not abstract.strip()) and abstract_not_required(record)):
                no_abstract_required[key[0]] += 1
            elif (key in full_text_exemption_reviews and key not in conflicts and seen.get(key) == 'include'
                    and (not isinstance(abstract, str) or not abstract.strip())
                    and record.get('abstract_requirement') == full_text_exemption_reviews[key]):
                full_text_reviewed[key[0]] += 1
            elif (key in owner_closed_reviews and key not in conflicts and seen.get(key) == 'exclude'
                    and (not isinstance(abstract, str) or not abstract.strip())
                    and record.get('abstract_requirement') == owner_closed_reviews[key]
                    and owner_closed_abstract(record, source_map[key[0]]['owner'])):
                owner_closed[key[0]] += 1
        for code, source in source_map.items():
            source['final_included'] = final_included[code] if code in final_review_sources else None
            source['final_missing_abstract'] = final_missing[code] if year != 2024 and code in final_review_sources else None
            source['unsynced_included'] = unsynced_included[code] if candidate_path.exists() else None
            source['unsynced_missing_abstract'] = unsynced_missing[code] if year != 2024 and candidate_path.exists() else None
            source['abstract_recovered'] = recovered_abstracts[code] if candidate_path.exists() else None
            source['abstract_not_required'] = no_abstract_required[code] if candidate_path.exists() else None
            source['abstract_full_text_reviewed'] = full_text_reviewed[code] if candidate_path.exists() else None
            source['abstract_closed_by_owner'] = owner_closed[code] if candidate_path.exists() else None
            missing = source['missing_abstract']
            source['abstract_supplement_required'] = max(0, missing - recovered_abstracts[code] - no_abstract_required[code] - full_text_reviewed[code] - owner_closed[code]) if missing is not None else None
        # Explicit coverage adapters: only recognized fields, never guess totals from prose.
        for path in sorted(review_dir.glob('*/coverage.json')):
            obj = read_json(path)
            rows = obj if isinstance(obj, list) else obj.get('sources', []) if isinstance(obj, dict) else []
            if not isinstance(rows, list): continue
            for row in rows:
                if not isinstance(row, dict): continue
                code = row.get('source_code') or row.get('venue')
                if code not in source_map: continue
                s = source_map[code]; s['files'].append(path.relative_to(root).as_posix())
                # No implicit claim of a comparable official total when scope is absent.
                s['coverage_note'] = str(row.get('coverage_status') or row.get('coverage_rationale') or '')
                total = number(row.get('official_total'))
                scope = str(row.get('coverage_rationale') or '').strip()
                source_snapshot = obj.get('snapshot', {}).get('snapshot_at') if isinstance(obj, dict) and isinstance(obj.get('snapshot'), dict) else None
                if total is not None and total >= 0 and scope and source_snapshot == snapshot.get('captured_at'):
                    s['official_total'], s['official_scope'] = total, scope
                links = row.get('evidence_urls') or []
                if isinstance(links, list): s['evidence_urls'] = [str(x) for x in links if isinstance(x,str)]
        for path in sorted(review_dir.glob('*/coverage.csv')):
            with path.open(encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f):
                    s = source_map.get(row.get('source_code'))
                    if not s: continue
                    s['files'].append(path.relative_to(root).as_posix())
                    s['coverage_note'] = row.get('coverage_note') or s['coverage_note']
                    total = number(row.get('official_total'))
                    scope = (row.get('official_total_scope') or '').strip()
                    if total is not None and total >= 0 and scope and row.get('snapshot_at') == snapshot.get('captured_at'):
                        s['official_total'], s['official_scope'] = total, scope
                    s['evidence_urls'] = [v.strip() for v in (row.get('evidence_urls') or '').split('|') if v.strip()]
        # Conference audit handoffs list per-source blockers and concrete follow-up.
        for path in sorted(review_dir.glob('*/conference-crawl-check.csv')):
            with path.open(encoding='utf-8-sig', newline='') as f:
                for row in csv.DictReader(f):
                    s = source_map.get(row.get('source_code'))
                    if not s: continue
                    s['files'].append(path.relative_to(root).as_posix())
                    issue = (row.get('blocking_reason') or '').strip()
                    action = (row.get('next_action') or '').strip()
                    if issue: s['issues'].append(issue)
                    if action: s['actions'].append(action)
                    links = [v.strip() for v in (row.get('official_urls') or '').split('|') if v.strip()]
                    s['evidence_urls'].extend(v for v in links if v not in s['evidence_urls'])
        resolution_rows = {}
        for path in sorted((review_dir / 'feedback').glob('*.json')):
            obj = read_json(path); rows = obj if isinstance(obj,list) else [obj]
            for row in rows:
                if not isinstance(row,dict) or row.get('year') != year: continue
                s = source_map.get(row.get('source_code'))
                if not s: continue
                scope = scopes.get(s['code'])
                if scope and path.relative_to(root).as_posix() != scope['feedback_file']:
                    historical = s['historical_review_files']
                    rel = path.relative_to(root).as_posix()
                    if rel not in historical: historical.append(rel)
                    continue
                s['files'].append(path.relative_to(root).as_posix())
                s['issues'].extend(str(x) for x in row.get('issues',[]) if isinstance(x,str))
                s['actions'].extend(str(x) for x in row.get('next_actions',[]) if isinstance(x,str))
                if not snapshot.get('captured_at') or row.get('snapshot_at') != snapshot.get('captured_at'):
                    s['issues'].append('阶段反馈对应的采集快照缺失或不一致，需重新核对。'); continue
                if (path.stem == row.get('github_username') and row.get('owner') == s['owner']
                        and row.get('collection_state_resolution')):
                    resolution_rows[s['code']] = row
                total, scope = number(row.get('official_total')), str(row.get('official_scope') or '').strip()
                if total is not None and total >= 0 and scope:
                    s['official_total'], s['official_scope'] = total, scope
                check = row.get('reference_check')
                if isinstance(check, dict) and check.get('status') == 'complete' and type(check.get('total')) is int and check['total'] >= 0 and type(check.get('unresolved')) is int and check['unresolved'] == 0 and all(isinstance(check.get(k), str) and check[k].strip() for k in ('source','scope','checked_at','query_url')) and check['query_url'].startswith(('https://','http://')):
                    s['reference_check'] = check
                    if check['query_url'] not in s['evidence_urls']: s['evidence_urls'].append(check['query_url'])
                s['coverage_note'] = str(row.get('coverage_note') or s['coverage_note'])
                if isinstance(row.get('evidence_urls'), list): s['evidence_urls'].extend(x for x in row['evidence_urls'] if isinstance(x,str))
        for s in source_map.values():
            resolution_row = resolution_rows.get(s['code'], {})
            if historical_abstract_gap_resolved(s, resolution_row, [r for r in candidate_records
                    if isinstance(r, dict) and r.get('year') == year], completed_reviews, root, year):
                s['collection_state_resolution'] = resolution_row['collection_state_resolution']
            if not s['owner']: s['issues'].append('负责人尚未明确。'); s['actions'].append('确认并登记负责人。')
            if s['state'] == 'unknown': s['issues'].append('缺少该年份的采集快照，采集总数和状态未知。'); s['actions'].append('提交或更新年度采集快照，核对采集范围和状态。')
            elif s['state'] not in ('completed','not_held') and not s.get('collection_state_resolution'): s['issues'].append('采集状态尚未完成：'+s['state']); s['actions'].append('检查采集状态与失败日志，必要时补采。')
            if s['official_total'] is None and not s['reference_check'] and s['state'] != 'not_held': s['issues'].append('官网同口径总数尚未确认。'); s['actions'].append('核对官网全年目录，或使用可靠替代来源完成同口径对账并记录证据。')
            if s['official_total'] is not None: s['actions'].append('核对已报告的官网总数与采集范围、年份和文献类型是否可比。')
            if year != 2024 and s['abstract_supplement_required'] is not None and s['abstract_supplement_required'] > 0: s['issues'].append('AI4S候选缺少摘要：'+str(s['abstract_supplement_required'])+' 篇。'); s['actions'].append('为缺摘要的AI4S候选补充可核实的摘要或证据，无法判断的论文标为待定。')
            if year != 2024 and s['unsynced_included']:
                s['issues'].append('个人审核已纳入但尚未同步候选总集：'+str(s['unsynced_included'])+' 篇，其中缺少原摘要：'+str(s['unsynced_missing_abstract'])+' 篇。')
                s['actions'].append('核对已纳入论文身份和范围，补充缺失的原摘要后同步候选总集。')
            if s['venue_decision'] in ('建议纳入', '清单保留') and s['candidates'] and s['decisions'] is None: s['issues'].append('尚未找到逐篇审核交付。'); s['actions'].append('提交逐篇审核结果或说明当前进度。')
            if s['decisions'] and (s['decisions']['pending'] or s['decisions']['unreviewed']): s['issues'].append('交付中存在待定或未审论文。'); s['actions'].append('按交付文件逐篇补证并处理待定、未审记录。')
        owner_rows = summarize_owners(source_map.values(), activity['owners'])
        for row in owner_rows:
            slot = merged.setdefault(row['owner'], {'owner': row['owner'], 'years': {}})
            slot['years'][str(year)] = {k: row[k] for k in ('sources', 'delivered', 'official', 'pending', 'open_issues', 'status')}
        years.append({'year':year,'captured_at':snapshot.get('captured_at'),'sources':list(source_map.values()),'owners':owner_rows,'snapshot_file':snapshot_path.relative_to(root).as_posix() if snapshot_path.exists() else None,'candidate_file':candidate_path.relative_to(root).as_posix() if candidate_path.exists() else None,'assignments_file':assignments_path.relative_to(root).as_posix() if assignments_path.exists() else None})
    owners = []
    for name, slot in merged.items():
        act = activity['owners'].get(name) or {}
        slot['sources'] = sum(v['sources'] for v in slot['years'].values())
        slot['delivered'] = sum(v['delivered'] for v in slot['years'].values())
        slot['not_started'] = sorted(k for k, v in slot['years'].items() if v['status'] == 'not_started')
        slot['last_update'] = act.get('last')
        slot['commits_7d'] = act.get('commits_7d') or 0
        owners.append(slot)
    owners.sort(key=lambda m: (-len(m['not_started']), -sum(1 for v in m['years'].values() if v['status'] != 'complete'), -m['sources'], m['owner']))
    return {'generated_at':datetime.now(timezone.utc).isoformat(), 'commit':commit, 'repository':REPO+ref+'/', 'years':years, 'owners':owners,
            'owner_activity':{k:v for k,v in activity.items() if k != 'owners'}}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',type=Path,required=True); p.add_argument('--output',type=Path,default=Path('data/review-monitor.json')); args=p.parse_args()
    result=build(args.source)
    if not result['years']: raise SystemExit('No annual snapshot or AI4S candidate file found')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built',args.output, 'years:', ', '.join(str(y['year']) for y in result['years']))

if __name__ == '__main__': main()
