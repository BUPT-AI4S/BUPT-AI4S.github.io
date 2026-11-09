import json, os, subprocess, tempfile, unittest
from datetime import timedelta
from pathlib import Path

from tools.build_review_monitor import build
from tools.build_owner_activity import build as build_activity
from tools.build_owner_activity import parse_history, review_account


class RelevantPathTest(unittest.TestCase):
    def test_repo_level_and_generated_paths_do_not_count_as_owner_work(self):
        from tools.build_owner_activity import is_relevant
        for path in ['reviews/owners.json', 'reviews/owner-activity.json', 'reviews/monitor-data.json',
                     'reviews/venue-review.csv', 'monitor-feedback-format.md',
                     'reviews/source-assignments-2024.json', 'reviews/2024/actions/乔徐阳.md']:
            self.assertFalse(is_relevant(path), path)
        for path in ['reviews/2024/Roman100021.json', 'reviews/2024/feedback/nydiii.json',
                     'reviews/venue-review-dlj.csv', 'metadata/2024/snapshot.json', 'metadata/icml/2025/papers.json']:
            self.assertTrue(is_relevant(path), path)


class ReviewAccountTest(unittest.TestCase):
    def test_owner_paths_resolve_and_shared_or_generated_paths_do_not(self):
        shared = {'lixueting-haozhuodi': ['李雪婷', '郝卓迪']}
        self.assertEqual(review_account('reviews/2024/nydiii.json', shared), 'nydiii')
        self.assertEqual(review_account('reviews/2024/feedback/Roman100021.json', shared), 'Roman100021')
        self.assertEqual(review_account('reviews/2024/zch66883/coverage.csv', shared), 'zch66883')
        self.assertIsNone(review_account('reviews/2024/actions/乔徐阳.md', shared))
        self.assertIsNone(review_account('reviews/2024/lixueting-haozhuodi/progress.json', shared))
        self.assertIsNone(review_account('reviews/venue-review.csv', shared))
        self.assertIsNone(review_account('reviews/monitor-data.json', shared))
        self.assertIsNone(review_account('metadata/2024/ai4s.json', shared))


class HistoryParseTest(unittest.TestCase):
    def test_commits_and_paths_are_split_on_control_marker(self):
        text = ('@@@abc123\x1fRoman\x1f2602123393@qq.com\x1f2026-11-09T19:38:04+08:00\x1f2024 精筛\n'
                'reviews/2024/Roman100021.json\n\n'
                '@@@def456\x1fbot\x1fbot@users.noreply.github.com\x1f2026-11-09T10:00:00+00:00\x1f更新论文审核行动清单\n'
                'reviews/2024/actions/乔徐阳.md\n')
        commits = parse_history(text)
        self.assertEqual([c['sha'] for c in commits], ['abc123', 'def456'])
        self.assertEqual(commits[0]['paths'], ['reviews/2024/Roman100021.json'])
        self.assertEqual(commits[0]['subject'], '2024 精筛')
        self.assertEqual(commits[1]['paths'], ['reviews/2024/actions/乔徐阳.md'])
        self.assertEqual(commits[0]['when'].utcoffset(), timedelta(hours=8))


class OwnerSummaryTest(unittest.TestCase):
    def _fixture(self, root, activity=True):
        (root / 'metadata/2024').mkdir(parents=True)
        (root / 'reviews/2024').mkdir(parents=True)
        (root / 'metadata/2024/snapshot.json').write_text(json.dumps({'year': 2024, 'captured_at': 'c', 'sources': [
            {'source': 'a', 'state': 'completed', 'papers': 1, 'ai4s': 0},
            {'source': 'b', 'state': 'completed', 'papers': 1, 'ai4s': 0}]}), encoding='utf8')
        (root / 'reviews/source-assignments-2024.json').write_text(json.dumps({'year': 2024, 'sources': [
            {'code': 'a', 'title': 'A', 'owner': '甲'}, {'code': 'b', 'title': 'B', 'owner': '乙'}]}), encoding='utf8')
        (root / 'reviews/2024/jia.json').write_text(json.dumps([
            {'venue': 'a', 'year': 2024, 'id': '1', 'ai4s_review': {'decision': 'include', 'snapshot_at': 'c'}}]),
            encoding='utf8')
        if activity:
            (root / 'reviews/owner-activity.json').write_text(json.dumps({
                'generated_at': 'g', 'history_available': True, 'commit': 'x', 'commits_scanned': 1,
                'owners': {'甲': {'last': {'at': '2026-11-09T10:00:00+08:00', 'author': 'Roman', 'subject': 's',
                                          'area': 'reviews', 'paths': ['reviews/2024/jia.json']},
                                  'commits_7d': 3}}}), encoding='utf8')

    def test_not_started_differs_from_in_progress_and_uses_git_activity(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self._fixture(p)
            data = build(p)
            owners = {o['owner']: o for o in data['owners']}
            self.assertEqual(owners['甲']['years']['2024']['status'], 'in_progress')
            self.assertEqual(owners['乙']['years']['2024']['status'], 'not_started')
            self.assertEqual(owners['乙']['not_started'], ['2024'])
            self.assertEqual(owners['甲']['last_update']['author'], 'Roman')
            self.assertEqual(owners['甲']['commits_7d'], 3)
            self.assertIsNone(owners['乙']['last_update'])
            self.assertEqual(data['owners'][0]['owner'], '乙')
            self.assertTrue(data['owner_activity']['available'])

    def test_missing_activity_file_keeps_summary_without_dates(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            self._fixture(p, activity=False)
            data = build(p)
            self.assertFalse(data['owner_activity']['available'])
            self.assertTrue(all(o['last_update'] is None for o in data['owners']))
            self.assertEqual({o['owner']: o['years']['2024']['status'] for o in data['owners']},
                             {'甲': 'in_progress', '乙': 'not_started'})


class ActivityFromGitHistoryTest(unittest.TestCase):
    def _commit(self, root, message, author, email, when):
        env = dict(os.environ, GIT_AUTHOR_NAME=author, GIT_AUTHOR_EMAIL=email,
                   GIT_COMMITTER_NAME=author, GIT_COMMITTER_EMAIL=email,
                   GIT_AUTHOR_DATE=when, GIT_COMMITTER_DATE=when)
        subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True, capture_output=True)
        subprocess.run(['git', '-C', str(root), 'commit', '-q', '-m', message], check=True, capture_output=True, env=env)

    def test_owner_files_credit_file_owner_over_committer(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            (p / 'reviews/2024').mkdir(parents=True)
            (p / 'reviews/owners.json').write_text(json.dumps({'schema': 1, 'owners': [
                {'name': '乔徐阳', 'accounts': ['Roman100021'], 'authors': ['Roman'], 'emails': ['r@qq.com']},
                {'name': '郝卓迪', 'accounts': ['zch66883-haozhuodi'], 'authors': [], 'emails': []}],
                'shared_accounts': {}}), encoding='utf8')
            subprocess.run(['git', '-C', str(p), 'init', '-q'], check=True, capture_output=True)
            (p / 'reviews/2024/Roman100021.json').write_text('[]', encoding='utf8')
            self._commit(p, 'setup owners', 'Roman', 'r@qq.com', '2026-11-09T09:00:00+08:00')
            (p / 'reviews/2024/zch66883-haozhuodi.json').write_text('[]', encoding='utf8')
            self._commit(p, '别人的文件', 'zch66883', 'z@qq.com', '2026-11-09T18:00:00+08:00')
            data = build_activity(p, 50)
            self.assertTrue(data['history_available'])
            self.assertEqual(data['owners']['郝卓迪']['last']['author'], 'zch66883')
            self.assertEqual(data['owners']['郝卓迪']['last']['area'], 'reviews')
            self.assertEqual(data['owners']['乔徐阳']['commits_7d'], 1)
            self.assertEqual(data['owners']['乔徐阳']['last']['subject'], 'setup owners')


class ActionFileActivityTest(unittest.TestCase):
    def test_action_file_states_last_update_and_delivery_progress(self):
        from tools.generate_review_actions import write_actions
        data = {'commit': 'sha', 'repository': 'https://github.com/x/y',
                'years': [{'year': 2024, 'captured_at': 'c', 'sources': [
                    {'owner': '甲', 'title': 'A', 'code': 'a', 'issues': [], 'actions': [], 'files': []}]}],
                'owners': [{'owner': '甲', 'last_update': {'at': '2026-11-09T19:38:04+08:00', 'author': 'Roman',
                                                          'subject': '2024 精筛', 'area': 'reviews'},
                            'years': {'2024': {'delivered': 1, 'sources': 2}}}]}
        with tempfile.TemporaryDirectory() as d:
            files = write_actions(data, Path(d) / 'reviews')
            text = files[0].read_text(encoding='utf8')
        self.assertIn('上次更新：2026-11-09 19:38（Roman 提交，审核交付）', text)
        self.assertIn('逐篇交付进度：2024 1/2', text)


if __name__ == '__main__':
    unittest.main()