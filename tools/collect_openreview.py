"""Collect public OpenReview notes into the static paper catalog (Python stdlib only)."""
import argparse
import csv
import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CURATED = ('titleZh', 'abstractZh', 'summaryZh', 'summaryEn', 'disciplines', 'subfield',
           'classificationReason', 'topics', 'notes', 'codeUrl', 'sample', 'translationSource')
RULES = {
    'mathematics': r'\b(mathematics|theorem|theorem proving|symbolic regression)\b',
    'physics': r'\b(physics|physical simulation|partial differential|fluid|quantum)\b',
    'chemistry': r'\b(chemistry|chemical|molecule|molecular)\b',
    'materials': r'\b(materials|crystal|alloy)\b',
    'biology': r'\b(biology|biological|protein|genomic|genome)\b',
    'medicine': r'\b(medical|clinical|patient|diagnosis|radiology)\b',
    'weather': r'\b(weather|climate|meteorological|atmospheric)\b',
    'communications': r'\b(wireless|telecommunication|channel estimation|communication systems)\b',
    'earth': r'\b(geoscience|seismic|geological|remote sensing)\b',
    'chips': r'\b(chip design|circuit design|electronic design automation)\b',
}

def value(content, key, default=''):
    v = content.get(key, default)
    if isinstance(v, dict):
        if 'readers' in v and 'everyone' not in v['readers']:
            return default
        return v.get('value', default)
    return v

def normalize_note(note):
    if 'everyone' not in note.get('readers', []):
        raise ValueError('Only explicitly public submission notes can be exported')
    c = note.get('content', {})
    title = value(c, 'title')
    if not note.get('id') or not isinstance(title, str) or not title.strip():
        raise ValueError('Submission must have a stable id and nonempty title')
    abstract = value(c, 'abstract') or ''
    venue = value(c, 'venue') or ''
    venue_id = value(c, 'venueid') or ''
    year = re.search(r'\b(20\d{2})\b', venue + ' ' + venue_id)
    decision = value(c, 'decision') or ''
    for reply in note.get('details', {}).get('directReplies', []):
        if 'everyone' not in reply.get('readers', []):
            continue
        invitations = reply.get('invitations', [reply.get('invitation', '')])
        if any(i.endswith('/Decision') for i in invitations):
            decision = value(reply.get('content', {}), 'decision') or decision
    if not decision:
        for label in ('Oral', 'Spotlight', 'Poster'):
            if label.lower() in venue.lower():
                decision = label
                break
    date_key = 'odate' if note.get('odate') else 'cdate'
    stamp = note.get(date_key)
    published = datetime.fromtimestamp(stamp / 1000, timezone.utc).date().isoformat() if stamp else ''
    forum = note.get('forum') or note['id']
    pdf = value(c, 'pdf')
    keywords = value(c, 'keywords', []) or []
    authors = value(c, 'authors', []) or []
    if isinstance(keywords, str): keywords = [keywords]
    if isinstance(authors, str): authors = [authors]
    text = ' '.join([title, abstract, *keywords]).lower()
    return {
        'id': note['id'], 'number': note.get('number'), 'title': title, 'titleZh': '',
        'abstract': abstract, 'abstractZh': '', 'authors': authors, 'keywords': keywords,
        'venue': venue or venue_id, 'venueId': venue_id, 'year': year.group(1) if year else '',
        'decision': decision, 'published': published, 'dateType': 'public' if date_key == 'odate' else 'submitted',
        'disciplines': [], 'subfield': '', 'classificationReason': '', 'topics': [],
        'disciplineSuggestions': [d for d, rule in RULES.items() if re.search(rule, text)],
        'forumUrl': 'https://openreview.net/forum?' + urlencode({'id': forum}),
        'paperUrl': 'https://openreview.net/forum?' + urlencode({'id': forum}),
        'pdfUrl': urljoin('https://openreview.net', pdf) if pdf else '',
        'source': 'OpenReview', 'sourceUpdated': note.get('mdate') or note.get('tcdate'),
    }

def merge_papers(existing, incoming):
    merged = {p['id']: dict(p) for p in existing}
    for paper in incoming:
        old = merged.get(paper['id'], {})
        fresh = {**old, **paper}
        for key in CURATED:
            if key in old: fresh[key] = old[key]
        merged[paper['id']] = fresh
    return list(merged.values())

def request_json(base, endpoint, params):
    url = base + endpoint + '?' + urlencode(params)
    for attempt in range(4):
        try:
            headers = {'User-Agent': 'AI4S-PaperCatalog/1.0', 'Accept': 'application/json'}
            if os.environ.get('OPENREVIEW_TOKEN'):
                headers['Authorization'] = 'Bearer ' + os.environ['OPENREVIEW_TOKEN']
            req = Request(url, headers=headers)
            with urlopen(req, timeout=40) as response:
                return json.load(response)
        except HTTPError as exc:
            if exc.code not in (429, 500, 502, 503, 504) or attempt == 3: raise
            time.sleep(2 ** (attempt + 1))

def fetch_notes(base, filters, limit, request=request_json):
    notes, offset = [], 0
    while True:
        size = min(100, limit - len(notes)) if limit else 100
        payload = request(base, '/notes', {**filters, 'limit': size, 'offset': offset, 'details': 'directReplies'})
        batch = payload.get('notes', [])
        if not batch: break
        notes.extend(n for n in batch if 'everyone' in n.get('readers', []))
        offset += len(batch)
        if (limit and len(notes) >= limit) or len(batch) < size: break
        time.sleep(0.3)
    return notes

def apply_overrides(papers, path):
    by_id = {p['id']: p for p in papers}
    with path.open(encoding='utf-8-sig', newline='') as f:
        for row in csv.DictReader(f):
            if not row.get('id') or row['id'] not in by_id:
                raise ValueError(f"Unknown override id: {row.get('id')}")
            for field in CURATED:
                if row.get(field):
                    if field in ('disciplines', 'topics'):
                        items = [v.strip() for v in row[field].split('|') if v.strip()]
                        if field == 'disciplines' and any(v not in RULES and v not in ('general', 'other') for v in items):
                            raise ValueError(f'Unknown discipline: {items}')
                        by_id[row['id']][field] = items
                    elif field not in ('notes', 'sample'):
                        by_id[row['id']][field] = row[field]
    return papers

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    scope = parser.add_mutually_exclusive_group(required=True)
    scope.add_argument('--venue', help='Accepted submissions for a venue, e.g. ICLR.cc/2025/Conference')
    scope.add_argument('--invitation', help='Explicit submission invitation (may include rejected/withdrawn papers)')
    scope.add_argument('--forum', help='Submission note ID, not a review/comment ID')
    scope.add_argument('--input', type=Path, help='Offline OpenReview notes export (array or {notes: [...]})')
    scope.add_argument('--editorial-only', action='store_true', help='Apply editorial CSV to existing catalog without network access')
    parser.add_argument('--api', choices=['1', '2'], default='2', help='Use 1 for older conferences')
    parser.add_argument('--limit', type=int, default=100, help='Maximum submissions; 0 means all')
    parser.add_argument('--output', type=Path, default=ROOT / 'data' / 'papers', help='Per-paper output directory; a .json path enables legacy aggregate export')
    parser.add_argument('--overrides', type=Path, help='Optional editorial CSV, see docs/papers.md')
    args = parser.parse_args()
    if args.limit < 0: parser.error('--limit must be nonnegative')
    if args.editorial_only and not args.overrides: parser.error('--editorial-only requires --overrides')
    directory = args.output.suffix.lower() != '.json'
    filenames = {}; bodies = {}
    if directory:
        from build_paper_index import read_json, read_markdown, markdown_source, compile_markdown, validate_paper, build_index, paper_files, paper_key, load_tag_vocabulary, normalize_paper_tags
        site_root=args.output.parent.parent if args.output.parent.name=='data' else ROOT
        existing=[];existing_stems=set()
        for file in paper_files(args.output):
            if file.name.endswith(('.local.md','.local.json')): raise ValueError(f'Reserved paper filename: {file.name}')
            if file.is_symlink() or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.(md|json)',file.name): raise ValueError(f'Invalid paper file: {file.name}')
            key=paper_key(file,args.output)
            if key.lower() in existing_stems:raise ValueError(f'Duplicate paper filename: {file.name}')
            existing_stems.add(key.lower())
            if file.suffix=='.md':
                paper,body=read_markdown(file);bodies[paper['id']]=body
            else:paper=read_json(file)
            if paper['id'] in filenames: raise ValueError(f'Duplicate existing paper id: {paper["id"]}')
            filenames[paper['id']]=file.relative_to(args.output).as_posix();existing.append(paper)
        data={'papers':existing}
    else:
        data = json.loads(args.output.read_text(encoding='utf-8')) if args.output.exists() else {'papers': []}
    if args.editorial_only and not args.output.exists(): raise ValueError('Editorial mode requires an existing catalog')
    base = 'https://api2.openreview.net' if args.api == '2' else 'https://api.openreview.net'
    filters = {'id': args.forum} if args.forum else {'content.venueid': args.venue} if args.venue else {'invitation': args.invitation}
    if args.input:
        raw = json.loads(args.input.read_text(encoding='utf-8'))
        notes = raw if isinstance(raw, list) else raw.get('notes', [])
        if args.limit: notes = notes[:args.limit]
        filters = {'input': args.input.name}
    else:
        notes = [] if args.editorial_only else fetch_notes(base, filters, args.limit)
    if not notes and not args.editorial_only: raise ValueError('No public submissions found; check venue/API version. Existing catalog has not been changed.')
    incoming = [normalize_note(n) for n in notes]
    papers = merge_papers(data.get('papers', []), incoming)
    if args.overrides: papers = apply_overrides(papers, args.overrides)
    data.update({'schemaVersion': 1, 'updated': datetime.now(timezone(timedelta(hours=8))).date().isoformat(), 'papers': papers})
    if not args.editorial_only:
        data['lastCollection'] = {'filters': filters, 'api': args.api, 'count': len(incoming), 'limit': args.limit}
    if directory:
        schema=read_json(ROOT/'data/papers.schema.json')
        config_path=args.output.parent/'papers-config.json'
        config=read_json(config_path) if config_path.exists() else {}
        from build_paper_index import validate
        validate(config.get('tagTranslations',{}),schema['properties']['tagTranslations'],schema,'tagTranslations')
        used={paper_key(args.output/name,args.output).lower() for name in filenames.values()}
        vocabulary=load_tag_vocabulary(site_root)
        for paper in papers:
            validate_paper(paper,schema,site_root,paper['id'])
            normalize_paper_tags(paper,vocabulary,paper['id'])
            if paper['id'] not in filenames:
                name=paper['id'] if re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',paper['id']) else 'paper-'+hashlib.sha256(paper['id'].encode()).hexdigest()[:16]
                if name.lower() in used or (args.output/name).exists(): raise ValueError(f'Conflicting paper filename: {name}')
                filenames[paper['id']]=name+'/paper.md';used.add(name.lower())
        # Check all Markdown bodies before changing any source file.
        for paper in papers:
            if filenames[paper['id']].endswith('.md'):
                compile_markdown(bodies.get(paper['id'],''),args.output/filenames[paper['id']],site_root)
        args.output.mkdir(parents=True,exist_ok=True)
        for paper in papers:
            output=args.output/filenames[paper['id']];temp=output.with_suffix(output.suffix+'.tmp')
            output.parent.mkdir(parents=True,exist_ok=True)
            text=markdown_source(paper,bodies.get(paper['id'],'')) if output.suffix=='.md' else json.dumps(paper,ensure_ascii=False,indent=2)+'\n'
            temp.write_text(text,encoding='utf-8');temp.replace(output)
        details={}
        index=build_index(args.output,ROOT/'data/papers.schema.json',config,site_root,details)
        built=args.output.parent/'papers-built';built.mkdir(exist_ok=True)
        for name,paper in details.items():
            output=built/name;temp=output.with_suffix('.json.tmp')
            temp.write_text(json.dumps(paper,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(output)
        output=args.output.parent/'papers-index.json';temp=output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(index,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(output)
    else:
        from build_paper_index import load_tag_vocabulary, normalize_paper_tags
        vocabulary=load_tag_vocabulary(ROOT)
        data['papers']=[normalize_paper_tags(p,vocabulary,p['id']) for p in papers]
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temp.replace(args.output)
    print(f'Collected {len(incoming)} public submissions; catalog now has {len(papers)} papers: {args.output}')

if __name__ == '__main__':
    try:
        main()
    except HTTPError as exc:
        print(f'OpenReview HTTP {exc.code}. Existing catalog was not changed. For 401/403, check public access or use a valid OPENREVIEW_TOKEN; for older venues try --api 1.', file=sys.stderr)
        sys.exit(1)
    except (ValueError, OSError) as exc:
        print(f'Collection failed: {exc}. Fix the error before rebuilding or publishing the catalog.', file=sys.stderr)
        sys.exit(1)
