import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tools import restore_abstracts  # noqa: E402

SEP = (',', ':')


def record(paper_id, venue, abstract, status='ready'):
    return {'id': paper_id, 'venue': venue, 'year': 2024, 'title': 'Title ' + paper_id,
            'abstract': abstract, 'screening_status': status}


class RestoreAbstractsTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name)
        (self.repo / 'metadata' / '2024').mkdir(parents=True)
        (self.repo / 'reviews').mkdir()
        (self.repo / 'reviews' / 'source-assignments-2024.json').write_text(
            json.dumps({'year': 2024, 'sources': [
                {'code': 'j-a', 'title': 'A', 'owner': '乔徐阳'},
                {'code': 'j-b', 'title': 'B', 'owner': '丁利军'},
            ]}, ensure_ascii=False), encoding='utf-8')
        self.git('init', '-q')

    def tearDown(self):
        self._tmp.cleanup()

    def git(self, *args):
        subprocess.run(['git', '-c', 'user.name=test', '-c', 'user.email=t@example.com', *args],
                       cwd=self.repo, check=True, capture_output=True)

    def write_records(self, records):
        lines = '[\n' + ',\n'.join(
            json.dumps(r, ensure_ascii=False, separators=SEP) for r in records) + '\n]\n'
        (self.repo / 'metadata' / '2024' / 'ai4s.json').write_text(lines, encoding='utf-8')

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)

    def load(self):
        return json.loads((self.repo / 'metadata' / '2024' / 'ai4s.json').read_text(encoding='utf-8'))

    def run_tool(self, *extra):
        return restore_abstracts.main([
            '--repo', str(self.repo), '--year', '2024', '--base-rev', 'HEAD~1', *extra])

    def test_restores_abstract_and_status(self):
        self.write_records([record('p1', 'j-a', 'Full abstract text.')])
        self.commit('with abstract')
        self.write_records([record('p1', 'j-a', None, 'needs_abstract')])
        self.commit('abstract dropped')

        self.assertEqual(self.run_tool(), 0)

        row = self.load()[0]
        self.assertEqual(row['abstract'], 'Full abstract text.')
        self.assertEqual(row['screening_status'], 'ready')

    def test_keeps_existing_abstract(self):
        self.write_records([record('p1', 'j-a', 'Old text.')])
        self.commit('with abstract')
        self.write_records([record('p1', 'j-a', 'Newer text.')])
        self.commit('updated abstract')

        self.assertEqual(self.run_tool(), 0)

        self.assertEqual(self.load()[0]['abstract'], 'Newer text.')

    def test_owner_filter_leaves_other_venues_alone(self):
        self.write_records([record('p1', 'j-a', 'Abstract A.'),
                            record('p2', 'j-b', 'Abstract B.')])
        self.commit('with abstracts')
        self.write_records([record('p1', 'j-a', None, 'needs_abstract'),
                            record('p2', 'j-b', None, 'needs_abstract')])
        self.commit('both dropped')

        self.assertEqual(self.run_tool('--owner', '乔徐阳'), 0)

        rows = {row['id']: row for row in self.load()}
        self.assertEqual(rows['p1']['abstract'], 'Abstract A.')
        self.assertIsNone(rows['p2']['abstract'])

    def test_untouched_lines_are_byte_identical(self):
        self.write_records([record('p1', 'j-a', 'Abstract A.'), record('p2', 'j-b', 'Abstract B.')])
        self.commit('with abstracts')
        self.write_records([record('p1', 'j-a', None, 'needs_abstract'),
                            record('p2', 'j-b', 'Abstract B.')])
        self.commit('one dropped')
        before = (self.repo / 'metadata' / '2024' / 'ai4s.json').read_text(encoding='utf-8').splitlines()

        self.assertEqual(self.run_tool(), 0)

        after = (self.repo / 'metadata' / '2024' / 'ai4s.json').read_text(encoding='utf-8').splitlines()
        self.assertEqual(len(before), len(after))
        self.assertEqual(before[0], after[0])
        self.assertEqual(before[2], after[2])
        self.assertEqual(before[3], after[3])

    def test_dry_run_does_not_write(self):
        self.write_records([record('p1', 'j-a', 'Abstract A.')])
        self.commit('with abstract')
        self.write_records([record('p1', 'j-a', None, 'needs_abstract')])
        self.commit('dropped')
        before = (self.repo / 'metadata' / '2024' / 'ai4s.json').read_text(encoding='utf-8')

        self.assertEqual(self.run_tool('--dry-run'), 0)

        self.assertEqual((self.repo / 'metadata' / '2024' / 'ai4s.json')
                         .read_text(encoding='utf-8'), before)

    def test_from_history_finds_abstracts_dropped_earlier(self):
        self.write_records([record('p1', 'j-a', 'Abstract A.'), record('p2', 'j-b', 'Abstract B.')])
        self.commit('with abstracts')
        self.write_records([record('p1', 'j-a', None, 'needs_abstract'), record('p2', 'j-b', None, 'needs_abstract')])
        self.commit('both dropped')
        rewritten = [record('p1', 'j-a', None, 'needs_abstract'), record('p2', 'j-b', None, 'needs_abstract')]
        for row in rewritten:
            row['title'] = 'Rewritten ' + row['id']
        self.write_records(rewritten)
        self.commit('unrelated rewrite on top')

        self.assertEqual(restore_abstracts.main([
            '--repo', str(self.repo), '--year', '2024', '--from-history']), 0)

        rows = {row['id']: row for row in self.load()}
        self.assertEqual(rows['p1']['abstract'], 'Abstract A.')
        self.assertEqual(rows['p2']['abstract'], 'Abstract B.')
        self.assertEqual(rows['p1']['screening_status'], 'ready')


if __name__ == '__main__':
    unittest.main()
