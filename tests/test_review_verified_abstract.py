import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path
from tools.build_review_monitor import build


class VerifiedAbstractTest(unittest.TestCase):
    def test_recovered_abstract_requires_current_owner_evidence_and_consistency(self):
        review = {'venue': 'v', 'year': 2026, 'id': 'paper', 'ai4s_review': {
            'owner': 'A', 'snapshot_at': 'current', 'decision': 'pending',
            'verified_metadata': {'abstract': 'Publisher original abstract.',
                                  'evidence_urls': ['https://publisher.example/paper']}}}
        cases = [('verified pending', review, None, None, 1)]
        for field, value in [('owner', 'B'), ('snapshot_at', 'old')]:
            record = deepcopy(review); record['ai4s_review'][field] = value
            cases.append((field, record, None, None, 0))
        for field, value in [('abstract', ' '), ('abstract', None),
                             ('evidence_urls', []), ('evidence_urls', ['https://[']),
                             ('evidence_urls', ['not a URL'])]:
            record = deepcopy(review); record['ai4s_review']['verified_metadata'][field] = value
            cases.append((str((field, value)), record, None, None, 0))
        duplicate = deepcopy(review)
        cases.append(('duplicate counts once', review, duplicate, None, 1))
        conflicting = deepcopy(review); conflicting['ai4s_review']['decision'] = 'include'
        cases.append(('conflicting decision', review, conflicting, None, 0))
        conflicting = deepcopy(review)
        conflicting['ai4s_review']['verified_metadata']['abstract'] = 'Different abstract.'
        cases.append(('conflicting text', review, conflicting, None, 0))
        cases.append(('candidate already complete', review, None, 'Original abstract.', 0))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root/'metadata/2026').mkdir(parents=True)
            (root/'reviews/2026').mkdir(parents=True)
            def write(path, value):
                (root/path).write_text(json.dumps(value), encoding='utf-8')
            write('metadata/2026/snapshot.json', {'year': 2026, 'captured_at': 'current',
                  'sources': [{'source': 'v', 'papers': 1}]})
            write('reviews/source-assignments-2026.json', {'year': 2026,
                  'sources': [{'code': 'v', 'owner': 'A'}]})
            for name, record, extra, original, expected in cases:
                with self.subTest(name=name):
                    write('metadata/2026/ai4s.json', [{'venue': 'v', 'year': 2026,
                          'id': 'paper', 'abstract': original}])
                    write('reviews/2026/a.json', [record] + ([extra] if extra else []))
                    source = build(root)['years'][0]['sources'][0]
                    self.assertEqual(source['abstract_recovered'], expected)
                    self.assertEqual(source['missing_abstract'], int(original is None))
                    self.assertEqual(source['abstract_supplement_required'], int(original is None)-expected)
                    self.assertIsNone(source['official_total'])
