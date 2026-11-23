import json
import tempfile
import unittest
from pathlib import Path

from tools.build_review_monitor import build


class AbstractStatePolicyTest(unittest.TestCase):
    def test_external_audit_can_check_timezone_aware_timestamps(self):
        from tools.build_review_monitor import aware_timestamp
        self.assertTrue(aware_timestamp('2026-11-23T10:00:00+08:00'))
        self.assertTrue(aware_timestamp('2026-11-23T02:00:00Z'))
        self.assertFalse(aware_timestamp('2026-11-23T10:00:00'))
        self.assertFalse(aware_timestamp('invalid'))

    def test_full_catalogue_gap_is_not_collection_failure_but_candidate_gap_remains(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            year = root / 'metadata' / '2025'
            year.mkdir(parents=True)
            (year / 'snapshot.json').write_text(json.dumps({'year': 2025, 'sources': [
                {'source': 'v', 'state': 'abstract_incomplete', 'papers': 2, 'with_abstract': 1},
                {'source': 'w', 'state': 'failed', 'papers': 1, 'with_abstract': 0},
            ]}), encoding='utf-8')
            (year / 'ai4s.json').write_text(json.dumps([{'year': 2025, 'venue': 'v', 'id': '1', 'abstract': None}]), encoding='utf-8')
            sources = {s['code']: s for s in build(root)['years'][0]['sources']}
            self.assertEqual(sources['v']['papers_missing_abstract'], 1)
            self.assertFalse(any('采集状态尚未完成：abstract_incomplete' in x for x in sources['v']['issues']))
            self.assertTrue(any('AI4S候选缺少摘要' in x for x in sources['v']['issues']))
            self.assertTrue(any('采集状态尚未完成：failed' in x for x in sources['w']['issues']))
