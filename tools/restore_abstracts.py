"""Restore abstracts that a rewrite of metadata/<year>/ai4s.json dropped.

The AI4S candidate files duplicate the abstract that also lives in the much
larger papers.json.  When a candidate file is regenerated from papers.json the
copies come back as null, which makes the review monitor report
"AI4S候选缺少摘要" for work that was already done.  This tool copies the
abstracts (and the matching screening_status) back from an earlier revision of
the same file, so the only change is the data that was lost.

The candidate files keep one record per line, so untouched records are copied
through byte for byte and the diff stays readable.

Usage:
    python tools/restore_abstracts.py --repo <crawler checkout> --year 2024 \
        --base-rev 76cf5f2 --owner 乔徐阳 --dry-run
"""

from __future__ import annotations

import argparse
import io
import json
import subprocess
import sys
from pathlib import Path

SEPARATORS = (',', ':')


def git_show(repo: Path, rev: str, path: str) -> bytes:
    proc = subprocess.run(
        ['git', 'show', f'{rev}:{path}'], cwd=repo, capture_output=True, check=False
    )
    if proc.returncode != 0:
        raise SystemExit(
            f'git show {rev}:{path} failed: {proc.stderr.decode("utf-8", "replace")}'
        )
    return proc.stdout


def load_owner_venues(repo: Path, year: int, owner: str) -> set[str]:
    path = repo / 'reviews' / f'source-assignments-{year}.json'
    if not path.exists():
        raise SystemExit(f'missing {path}')
    doc = json.loads(path.read_text(encoding='utf-8'))
    return {
        row['code']
        for row in doc.get('sources', [])
        if row.get('owner') == owner and row.get('code')
    }


def load_base(repo: Path, rev: str, path: str) -> dict:
    records = json.loads(git_show(repo, rev, path).decode('utf-8'))
    return {row['id']: row for row in records if isinstance(row, dict) and row.get('id')}


def decide(record: dict, base: dict, venues: set[str] | None) -> tuple[str, str | None] | None:
    """Return (abstract, screening_status) to write, or None to leave alone."""
    if venues is not None and record.get('venue') not in venues:
        return None
    old = base.get(record.get('id'))
    if not old:
        return None
    recovered = old.get('abstract')
    if not isinstance(recovered, str) or not recovered.strip():
        return None
    current = record.get('abstract')
    if isinstance(current, str) and current.strip():
        return None
    status = None
    old_status = old.get('screening_status')
    if record.get('screening_status') == 'needs_abstract':
        if isinstance(old_status, str) and old_status.strip():
            status = old_status
    return recovered, status


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', default='.', help='crawler checkout')
    parser.add_argument('--year', type=int, required=True)
    parser.add_argument('--base-rev', required=True, help='revision that still has the abstracts')
    parser.add_argument('--owner', help='only restore venues assigned to this owner')
    parser.add_argument('--dry-run', action='store_true')
    args = parser.parse_args(argv)

    repo = Path(args.repo).resolve()
    rel = f'metadata/{args.year}/ai4s.json'
    target = repo / 'metadata' / str(args.year) / 'ai4s.json'
    if not target.exists():
        raise SystemExit(f'missing {target}')

    venues = load_owner_venues(repo, args.year, args.owner) if args.owner else None
    base = load_base(repo, args.base_rev, rel)

    report: list[dict] = []
    out: list[str] = []
    with io.open(target, encoding='utf-8', newline='') as handle:
        for line in handle:
            body = line.strip()
            if not body.startswith('{"id":'):
                out.append(line)
                continue
            trailing = ',' if body.endswith(',') else ''
            payload = body[:-1] if trailing else body
            record = json.loads(payload)
            decision = decide(record, base, venues)
            if decision is None:
                out.append(line)
                continue
            abstract, status = decision
            updated = dict(record)
            updated['abstract'] = abstract
            if status is not None:
                updated['screening_status'] = status
            rebuilt = json.dumps(updated, ensure_ascii=False, separators=SEPARATORS)
            out.append(rebuilt + trailing + ('\n' if line.endswith('\n') else ''))
            report.append({'id': record.get('id'), 'venue': record.get('venue'),
                           'abstract_chars': len(abstract.strip())})

    if not report:
        print('no abstracts to restore')
        return 0

    total_chars = sum(row['abstract_chars'] for row in report)
    print(f'restored {len(report)} abstracts ({total_chars} chars) in {rel}')
    for row in report[:10]:
        print(f"  {row['id']}  {row['venue']}  {row['abstract_chars']}")
    if len(report) > 10:
        print(f'  ... {len(report) - 10} more')
    if args.dry_run:
        print('dry run: nothing written')
        return 0
    with io.open(target, 'w', encoding='utf-8', newline='') as handle:
        handle.writelines(out)
    print(f'wrote {target}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
