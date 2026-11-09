"""Build a public, source-linked snapshot from an ai4s-crawler checkout."""
import argparse
import csv
import json
import subprocess
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
    years = []
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
            source_map[code] = {'code':code, 'title':assignment.get('title') or info.get('title') or code, 'owner':assignment.get('owner') or ((info.get('owner') or '') if year == 2024 and assignments is None else ''),
                'venue_decision':('清单保留' if assignments is not None else (info.get('是否建议纳入') or '') if year == 2024 else ''), 'state':item.get('state') or 'unknown',
                'papers':papers, 'snapshot_candidates':number(item.get('ai4s')), 'candidates':candidate_counts[code] if candidate_path.exists() else number(item.get('ai4s')), 'missing_abstract':candidate_missing[code] if candidate_path.exists() else None,
                'official_total':None, 'official_scope':'', 'coverage_note':'', 'evidence_urls':[], 'decisions':None,
                'issues':[], 'actions':[], 'files':[], 'snapshot_at':snapshot.get('captured_at')}
        review_dir = root / 'reviews' / str(year)
        counts, seen, conflicts = {}, {}, set()
        for path in sorted(review_dir.glob('*.json')):
            records = read_json(path)
            if not isinstance(records, list): continue
            for record in records:
                if not isinstance(record, dict) or record.get('year') != year: continue
                code = record.get('venue'); review = record.get('ai4s_review') or {}
                if code not in source_map or not isinstance(review, dict): continue
                key = (code, record.get('id'))
                if not key[1]: continue
                decision = review.get('decision')
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
        for path in sorted((review_dir / 'feedback').glob('*.json')):
            obj = read_json(path); rows = obj if isinstance(obj,list) else [obj]
            for row in rows:
                if not isinstance(row,dict) or row.get('year') != year: continue
                s = source_map.get(row.get('source_code'))
                if not s: continue
                s['files'].append(path.relative_to(root).as_posix())
                s['issues'].extend(str(x) for x in row.get('issues',[]) if isinstance(x,str))
                s['actions'].extend(str(x) for x in row.get('next_actions',[]) if isinstance(x,str))
                if not snapshot.get('captured_at') or row.get('snapshot_at') != snapshot.get('captured_at'):
                    s['issues'].append('阶段反馈对应的采集快照缺失或不一致，需重新核对。'); continue
                total, scope = number(row.get('official_total')), str(row.get('official_scope') or '').strip()
                if total is not None and total >= 0 and scope:
                    s['official_total'], s['official_scope'] = total, scope
                s['coverage_note'] = str(row.get('coverage_note') or s['coverage_note'])
                if isinstance(row.get('evidence_urls'), list): s['evidence_urls'].extend(x for x in row['evidence_urls'] if isinstance(x,str))
        for s in source_map.values():
            if not s['owner']: s['issues'].append('负责人尚未明确。'); s['actions'].append('确认并登记负责人。')
            if s['state'] == 'unknown': s['issues'].append('缺少该年份的采集快照，采集总数和状态未知。'); s['actions'].append('提交或更新年度采集快照，核对采集范围和状态。')
            elif s['state'] not in ('completed','not_held'): s['issues'].append('采集状态尚未完成：'+s['state']); s['actions'].append('检查采集状态与失败日志，必要时补采。')
            if s['official_total'] is None and s['state'] != 'not_held': s['issues'].append('官网同口径总数尚未确认。'); s['actions'].append('核对官网全年目录，记录统计口径及证据。')
            if s['official_total'] is not None: s['actions'].append('核对已报告的官网总数与采集范围、年份和文献类型是否可比。')
            if s['missing_abstract'] is not None and s['missing_abstract'] > 0: s['issues'].append('AI4S候选缺少摘要：'+str(s['missing_abstract'])+' 篇。'); s['actions'].append('为缺摘要的AI4S候选补充可核实的摘要或证据，无法判断的论文标为待定。')
            if s['venue_decision'] in ('建议纳入', '清单保留') and s['candidates'] and s['decisions'] is None: s['issues'].append('尚未找到逐篇审核交付。'); s['actions'].append('提交逐篇审核结果或说明当前进度。')
            if s['decisions'] and (s['decisions']['pending'] or s['decisions']['unreviewed']): s['issues'].append('交付中存在待定或未审论文。'); s['actions'].append('按交付文件逐篇补证并处理待定、未审记录。')
        years.append({'year':year,'captured_at':snapshot.get('captured_at'),'sources':list(source_map.values()),'snapshot_file':snapshot_path.relative_to(root).as_posix() if snapshot_path.exists() else None,'candidate_file':candidate_path.relative_to(root).as_posix() if candidate_path.exists() else None,'assignments_file':assignments_path.relative_to(root).as_posix() if assignments_path.exists() else None})
    return {'generated_at':datetime.now(timezone.utc).isoformat(), 'commit':commit, 'repository':REPO+ref+'/', 'years':years}


def main():
    p=argparse.ArgumentParser(); p.add_argument('--source',type=Path,required=True); p.add_argument('--output',type=Path,default=Path('data/review-monitor.json')); args=p.parse_args()
    result=build(args.source)
    if not result['years']: raise SystemExit('No annual snapshot or AI4S candidate file found')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Built',args.output, 'years:', ', '.join(str(y['year']) for y in result['years']))

if __name__ == '__main__': main()
