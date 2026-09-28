import argparse
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import tingwu
import polish

class PolishTests(unittest.TestCase):
    def setUp(self):
        self.course = dict(id='lesson', title='课', slides=[{'image':'keep.png'}], transcript=[
            dict(id=str(i), text='原文。', speaker='甲', start=i*1000, end=(i+1)*1000) for i in range(3)])

    def test_invalid_response_cannot_drop_or_duplicate_sentences(self):
        for ids in ([0, 1], [0, 0, 2], [0, 2, 1]):
            with self.assertRaises(ValueError):
                polish.validate(self.course['transcript'], {'paragraphs':[{'indices':ids, 'text':'整理。'}]})

    def test_run_preserves_original_and_reuses_cache(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(tingwu, 'ROOT', Path(folder)), patch.object(tingwu, 'PRIVATE', Path(folder)/'.tingwu'):
            path = Path(folder)/'data/lesson.json'
            tingwu.write_json(path, self.course)
            args = argparse.Namespace(id='lesson', sample_seconds=None, overwrite=False)
            with patch.object(polish, 'complete', return_value={'paragraphs':[{'indices':[0,1,2], 'text':'整理。'}]}):
                polish.run(args)
            result = tingwu.read_json(path)
            self.assertEqual(result['transcript'], self.course['transcript'])
            self.assertEqual(result['slides'], [{'image':'keep.png'}])
            self.assertEqual(result['transcriptPolished'][0]['sourceSentenceIds'], ['0','1','2'])
            self.assertEqual(result['transcriptPolished'][0]['end'], 3000)
            args.overwrite = True
            with patch.object(polish, 'complete', side_effect=AssertionError('cache must be used')):
                polish.run(args)

    def test_sample_does_not_modify_course_and_failure_is_atomic(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(tingwu, 'ROOT', Path(folder)), patch.object(tingwu, 'PRIVATE', Path(folder)/'.tingwu'):
            path = Path(folder)/'data/lesson.json'
            tingwu.write_json(path, self.course)
            original = path.read_bytes()
            args = argparse.Namespace(id='lesson', sample_seconds=1, overwrite=False)
            with patch.object(polish, 'complete', return_value={'paragraphs':[{'indices':[0], 'text':'整理。'}]}):
                polish.run(args)
            self.assertEqual(path.read_bytes(), original)
            args.sample_seconds = None
            with patch.object(polish, 'complete', return_value={'paragraphs':[]}):
                with self.assertRaises(ValueError): polish.run(args)
            self.assertEqual(path.read_bytes(), original)

if __name__ == '__main__': unittest.main()
