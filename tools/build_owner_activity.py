"""Summarize per-owner commit activity from a crawler checkout that has git history.

The output is ``reviews/owner-activity.json``: for every registered owner, when their
files were last touched, who committed that change, and how many commits landed in the
last 7 / 30 days. Attribution prefers the owner-specific review paths and only falls
back to the git author identity, so files that one person commits on behalf of another
are still credited to the file owner.

Requires history: ``git log`` must reach back far enough (``fetch-depth: 0`` or a
``--filter=blob:none`` shallow-then-deepen clone). When history looks shallow the
script warns and reports ``history_available: false`` instead of inventing dates.
"""
import argparse
import json
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

FIELD = '\x1f'
MARK = '@@@'


def git(repo, *args):
    proc = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                          encoding='utf-8', errors='replace')
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.strip() or 'git failed: ' + ' '.join(args))
    return proc.stdout


def load_owners(root):
    path = Path(root) / 'reviews/owners.json'
    if not path.exists():
        raise SystemExit(f'Missing owner registry: {path}')
    doc = json.loads(path.read_text(encoding='utf-8-sig'))
    names, by_account, by_author, by_email = [], {}, {}, {}
    for entry in doc.get('owners', []):
        name = (entry.get('name') or '').strip()
        if not name:
            continue
        names.append(name)
        for account in entry.get('accounts') or []:
            if account:
                by_account[str(account).strip()] = name
        for author in entry.get('authors') or []:
            if author:
                by_author[str(author).strip().lower()] = name
        for email in entry.get('emails') or []:
            if email:
                by_email[str(email).strip().lower()] = name
    shared = {str(k).strip(): list(v) for k, v in (doc.get('shared_accounts') or {}).items()}
    return names, by_account, by_author, by_email, shared


def review_account(path, shared):
    """Return the review account that owns a crawler path, or None."""
    parts = path.split('/')
    if len(parts) < 3 or parts[0] != 'reviews' or not parts[1].isdigit():
        return None
    head = parts[2]
    if head == 'actions':
        return None
    if head == 'feedback':
        if len(parts) < 4:
            return None
        token = parts[3]
    else:
        token = head
    if token.endswith('.json'):
        token = token[:-5]
    if token in shared:
        return None
    return token or None


def parse_history(text):
    commits, current = [], None
    for line in text.splitlines():
        if line.startswith(MARK):
            fields = line[len(MARK):].split(FIELD)
            if len(fields) < 5:
                current = None
                continue
            try:
                when = datetime.fromisoformat(fields[3])
            except ValueError:
                current = None
                continue
            current = {'sha': fields[0], 'author': fields[1], 'email': fields[2],
                       'when': when, 'subject': FIELD.join(fields[4:]), 'paths': []}
            commits.append(current)
        elif line.strip() and current is not None:
            current['paths'].append(line.strip())
    return commits


def area_of(paths):
    areas = set()
    for path in paths:
        if path.startswith('metadata/'):
            areas.add('metadata')
        elif path.startswith('reviews/') and '/actions/' not in path:
            areas.add('reviews')
        else:
            areas.add('other')
    for preferred in ('reviews', 'metadata', 'other'):
        if preferred in areas:
            return preferred
    return 'other'


IGNORED_PATHS = {'reviews/owners.json', 'reviews/owner-activity.json', 'reviews/monitor-data.json',
                 'reviews/venue-review.csv', 'monitor-feedback-format.md'}


def is_relevant(path):
    """Repo-level or generated files say nothing about who did review work."""
    if path in IGNORED_PATHS or path.startswith('reviews/source-assignments-'):
        return False
    parts = path.split('/')
    if parts[0] == 'reviews' and 'actions' in parts[1:]:
        return False
    return path.startswith('reviews/') or path.startswith('metadata/')


def build(root, limit):
    root = Path(root)
    try:
        commit = git(root, 'rev-parse', 'HEAD').strip()
        count = int(git(root, 'rev-list', '--count', 'HEAD').strip() or 0)
    except (RuntimeError, ValueError):
        commit, count = None, 0
    names, by_account, by_author, by_email, shared = load_owners(root)
    log = git(root, 'log', '--no-merges', f'-n{limit}', '--name-only',
              f'--format={MARK}%H{FIELD}%an{FIELD}%ae{FIELD}%aI{FIELD}%s')
    commits = parse_history(log) if count else []
    history_available = count > 0 and len(commits) > 0

    track = {name: {'last': None, 'review': None, 'metadata': None, 'counts': []} for name in names}
    for item in commits:
        paths = [path for path in item['paths'] if is_relevant(path)]
        if not paths:
            continue
        touched = set()
        for path in paths:
            account = review_account(path, shared)
            if account and account in by_account:
                touched.add(by_account[account])
        if not touched:
            name = by_author.get(item['author'].strip().lower()) or by_email.get(item['email'].strip().lower())
            if name in track:
                touched.add(name)
        for name in touched:
            slot = track[name]
            record = {'when': item['when'], 'author': item['author'], 'sha': item['sha'],
                      'subject': item['subject'], 'area': area_of(paths),
                      'paths': paths[:4]}
            if slot['last'] is None or record['when'] > slot['last']['when']:
                slot['last'] = record
            if record['area'] == 'reviews' and (slot['review'] is None or record['when'] > slot['review']['when']):
                slot['review'] = record
            if record['area'] == 'metadata' and (slot['metadata'] is None or record['when'] > slot['metadata']['when']):
                slot['metadata'] = record
            slot['counts'].append(record['when'])

    now = datetime.now(timezone.utc)
    owners = {}
    for name, slot in track.items():
        def summarize(record):
            if not record:
                return None
            return {'at': record['when'].isoformat(), 'author': record['author'],
                    'subject': record['subject'], 'area': record['area'],
                    'paths': record['paths']}
        owners[name] = {
            'last': summarize(slot['last']),
            'last_review': summarize(slot['review']),
            'last_metadata': summarize(slot['metadata']),
            'commits_7d': sum(1 for when in slot['counts'] if now - when <= timedelta(days=7)),
            'commits_30d': sum(1 for when in slot['counts'] if now - when <= timedelta(days=30)),
        }
    oldest = min((c['when'] for c in commits), default=None)
    return {
        'generated_at': now.isoformat(),
        'history_available': history_available,
        'commit': commit,
        'commits_scanned': len(commits),
        'commits_in_repo': count,
        'oldest_scanned_commit': oldest.isoformat() if oldest else None,
        'owners': owners,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True, help='crawler checkout with git history')
    parser.add_argument('--output', type=Path, default=None, help='defaults to <repo>/reviews/owner-activity.json')
    parser.add_argument('--limit', type=int, default=3000, help='max commits to scan')
    args = parser.parse_args()
    data = build(args.repo, args.limit)
    output = args.output or (args.repo / 'reviews' / 'owner-activity.json')
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    known = sum(1 for row in data['owners'].values() if row['last'])
    print(f"Wrote {output} owners={len(data['owners'])} with commits={known} scanned={data['commits_scanned']}")
    if not data['history_available']:
        print('WARNING: git history is shallow; per-owner dates are incomplete.', flush=True)
        raise SystemExit(2)


if __name__ == '__main__':
    main()
