import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from test_full_text_abstract_exemptions import FullTextAbstractExemptionTest
from tools.build_review_monitor import build


class LiXuetingFullTextMetricsTest(unittest.TestCase):
    def fixture(self, year=2025, owner='李雪婷'):
        snapshot, candidates, reviews, feedback = FullTextAbstractExemptionTest().fixture()
        snapshot['year'] = year
        feedback.update(year=year, owner=owner)
        feedback['collection_state_resolution']['checked_by'] = owner
        for record in candidates + reviews:
            record['year'] = year
            proof = record.get('abstract_requirement')
            if proof:
                proof.update(checked_by=owner, owner_instruction='允许，确认原本无摘要时可依据原始全文筛选')
        for record in reviews:
            review = record['ai4s_review']
            review['owner'] = owner
            review['abstract_requirement'].update(checked_by=owner,
                owner_instruction='允许，确认原本无摘要时可依据原始全文筛选')
        return snapshot, candidates, reviews, feedback

    def render(self, fixture, owner='李雪婷'):
        snapshot, candidates, reviews, feedback = fixture
        year = snapshot['year']
        before = deepcopy(fixture)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            documents = {
                f'metadata/{year}/snapshot.json': snapshot,
                f'metadata/{year}/ai4s.json': candidates,
                f'reviews/source-assignments-{year}.json': {'year': year, 'sources': [
                    {'code': 'v', 'owner': owner}, {'code': 'untouched', 'owner': owner}]},
                f'reviews/{year}/a.json': reviews,
                f'reviews/{year}/feedback/a.json': feedback,
            }
            for path, value in documents.items():
                target = root / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(json.dumps(value), encoding='utf-8')
            result = build(root)['years'][0]['sources']
            for path, value in documents.items():
                self.assertEqual(json.loads((root / path).read_text()), value)
        self.assertEqual(fixture, before)
        return {source['code']: source for source in result}

    def test_completed_body_reviews_are_separate_from_unresolved_abstracts(self):
        for year in (2025, 2026):
            with self.subTest(year=year):
                rows = self.render(self.fixture(year))
                source = rows['v']
                self.assertEqual(source['final_included'], 1)
                self.assertEqual(source['final_originally_missing_abstract'], 1)
                self.assertEqual(source['final_no_abstract_full_text_reviewed'], 1)
                self.assertEqual(source['final_missing_abstract'], 0)
                self.assertEqual(source['missing_abstract'], 1)
                self.assertEqual(source['abstract_supplement_required'], 0)
                self.assertIn('原始空值保留', source['coverage_note'])
                self.assertTrue(rows['untouched']['issues'])

    def test_another_missing_inclusion_stays_open(self):
        fixture = self.fixture()
        fixture[1].append({'year': 2025, 'venue': 'v', 'id': 'two', 'abstract': None})
        fixture[2].append({'year': 2025, 'venue': 'v', 'id': 'two', 'abstract': None,
            'ai4s_review': {'owner': '李雪婷', 'snapshot_at': 'current', 'decision': 'include'}})
        source = self.render(fixture)['v']
        self.assertEqual(source['final_originally_missing_abstract'], 2)
        self.assertEqual(source['final_missing_abstract'], 1)
        self.assertEqual(source['abstract_supplement_required'], 1)

    def test_other_owners_keep_the_existing_metric(self):
        source = self.render(self.fixture(owner='A'), owner='A')['v']
        self.assertEqual(source['final_missing_abstract'], 1)
        self.assertNotIn('final_originally_missing_abstract', source)

    def test_invalid_or_conflicting_proofs_cannot_change_display_metric(self):
        cases = [
            lambda f: f[1][0].pop('abstract_requirement'),
            lambda f: f[2][0]['ai4s_review'].pop('verified_metadata'),
            lambda f: f[2][0]['ai4s_review']['abstract_requirement'].update(checked_by='other'),
            lambda f: f[2][0]['ai4s_review'].update(snapshot_at='old'),
            lambda f: f[2].append(dict(deepcopy(f[2][0]), ai4s_review={
                'owner': '李雪婷', 'snapshot_at': 'current', 'decision': 'exclude'})),
        ]
        for index, mutate in enumerate(cases):
            with self.subTest(case=index):
                fixture = self.fixture()
                mutate(fixture)
                source = self.render(fixture)['v']
                self.assertNotIn('final_no_abstract_full_text_reviewed', source)
                self.assertEqual(source['abstract_full_text_reviewed'], 0)
