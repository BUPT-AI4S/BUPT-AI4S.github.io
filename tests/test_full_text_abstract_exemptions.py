import unittest
from copy import deepcopy
from test_review_monitor import HistoricalAbstractStateTest


class FullTextAbstractExemptionTest(unittest.TestCase):
    def fixture(self):
        fixture = HistoricalAbstractStateTest().fixture()
        proof = {'status': 'not_required', 'reason': 'official_source_has_no_independent_abstract',
                 'checked_at': '2026-11-16', 'checked_by': 'A', 'review_basis': 'verified_full_text',
                 'full_text_url': 'https://publisher.example/full.pdf',
                 'evidence_urls': ['https://publisher.example/full.pdf']}
        fixture[1][0].update(abstract=None, abstract_requirement=deepcopy(proof))
        fixture[2][0]['ai4s_review'].update(
            abstract_requirement=deepcopy(proof),
            verified_metadata={'abstract_status': 'not_provided_by_publisher',
                'full_text_evidence_location': 'Methods and Figure 1',
                'full_text_summary_zh': '全文说明科学任务及AI方法。',
                'evidence_urls': ['https://publisher.example/full.pdf']},
            abstract_resolution={'status': 'publisher_no_text_abstract_full_text_reviewed',
                'requires_abstract_backfill': False, 'original_abstract_preserved': True})
        return fixture

    def test_verified_full_text_closes_only_the_abstract_task(self):
        fixture = self.fixture()
        fixture[2].append({'year': 2025, 'venue': 'v', 'id': 'still-pending',
                          'ai4s_review': {'owner': 'A', 'snapshot_at': 'current', 'decision': 'pending'}})
        source, untouched = HistoricalAbstractStateTest().render(fixture)
        self.assertEqual(source['missing_abstract'], 1)
        self.assertEqual(source['abstract_full_text_reviewed'], 1)
        self.assertEqual(source['abstract_supplement_required'], 0)
        self.assertEqual(source['abstract_not_required'], 0)
        self.assertEqual(source['decisions']['include'], 1)
        self.assertEqual(source['decisions']['pending'], 1)
        self.assertTrue(any('待定或未审' in s for s in source['issues']))
        self.assertFalse(any('候选缺少摘要' in s for s in source['issues']))
        self.assertTrue(untouched['issues'])

    def test_unverified_stale_conflicting_or_mismatched_proofs_remain_open(self):
        cases = [
            ('pending', lambda f: f[2][0]['ai4s_review'].update(decision='pending')),
            ('wrong owner', lambda f: f[2][0]['ai4s_review'].update(owner='B')),
            ('stale', lambda f: f[2][0]['ai4s_review'].update(snapshot_at='old')),
            ('candidate mismatch', lambda f: f[1][0]['abstract_requirement'].update(checked_by='B')),
            ('no candidate proof', lambda f: f[1][0].pop('abstract_requirement')),
            ('no review proof', lambda f: f[2][0]['ai4s_review'].pop('abstract_requirement')),
            ('no metadata', lambda f: f[2][0]['ai4s_review'].pop('verified_metadata')),
            ('no resolution', lambda f: f[2][0]['ai4s_review'].pop('abstract_resolution')),
            ('conflict', lambda f: f[2].append(dict(deepcopy(f[2][0]), ai4s_review={
                'owner': 'A', 'snapshot_at': 'current', 'decision': 'exclude'}))),
        ]
        for key in ('full_text_summary_zh', 'full_text_evidence_location', 'abstract_status', 'evidence_urls'):
            cases.append((key, lambda f, key=key: f[2][0]['ai4s_review']['verified_metadata'].pop(key)))
        for key in ('review_basis', 'full_text_url', 'checked_at', 'checked_by', 'evidence_urls'):
            cases.append((key, lambda f, key=key: f[2][0]['ai4s_review']['abstract_requirement'].pop(key)))
        for key in ('requires_abstract_backfill', 'original_abstract_preserved'):
            cases.append((key, lambda f, key=key: f[2][0]['ai4s_review']['abstract_resolution'].update({key: True if key == 'requires_abstract_backfill' else False})))
        for name, mutate in cases:
            with self.subTest(name=name):
                fixture = self.fixture()
                mutate(fixture)
                source = HistoricalAbstractStateTest().render(fixture)[0]
                self.assertEqual(source['abstract_supplement_required'], 1)
                self.assertEqual(source['abstract_full_text_reviewed'], 0)
