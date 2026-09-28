import sys
import unittest
import argparse
import tempfile
from unittest.mock import patch
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'tools'))
import tingwu
from tingwu import normalize, valid_id

class NormalizeTests(unittest.TestCase):
    def test_polish_keeps_original_and_uncovered_sentences(self):
        raw = {'Transcription': {'Transcription': {'Paragraphs': [{'SpeakerId': 1, 'Words': [
            {'SentenceId': i, 'Start': i*1000, 'End': (i+1)*1000, 'Text': '原文'} for i in range(3)]}]}},
            'TextPolish': {'TextPolish': [{'SentenceIds': [0, 1], 'FormalParagraphText': '整理后的段落。'}]}}
        result = normalize(raw)
        self.assertEqual([r['text'] for r in result['transcript']], ['原文']*3)
        self.assertEqual([r['text'] for r in result['transcriptPolished']], ['整理后的段落。', '原文'])
        self.assertEqual(result['transcriptPolished'][0]['sourceSentenceIds'], ['0', '1'])
        self.assertEqual(result['transcriptPolished'][0]['start'], 0)
        self.assertEqual(result['transcriptPolished'][0]['end'], 2000)
        raw['TextPolish']['TextPolish'][0]['SentenceIds'] = [0, 99]
        self.assertEqual(normalize(raw)['transcriptPolished'], [])

    def test_polish_rejects_noncontiguous_and_mixed_speakers(self):
        rows = [dict(id=str(i), text='原文', start=i*1000, end=(i+1)*1000,
                     speaker='甲' if i < 2 else '乙') for i in range(3)]
        for refs in ([0, 2], [1, 2], [0, 0], [99]):
            self.assertEqual(tingwu.polished_transcript(rows, [dict(SentenceIds=refs, FormalParagraphText='整理')]), [])
        self.assertEqual(tingwu.polished_transcript(rows, [dict(SentenceIds=[0], FormalParagraphText='  ')]), [])

    def test_submit_enables_polish_with_opt_out(self):
        for disabled in (False, True):
            with tempfile.TemporaryDirectory() as directory, patch.object(tingwu, 'PRIVATE', Path(directory)), patch.object(tingwu, 'api', return_value={'TaskId':'task'}) as api:
                args = argparse.Namespace(id='lesson', title='课', date='', file_url='https://example.com/a.mp4',
                    video_url='https://example.com/a.mp4', language='cn', retry=False, no_text_polish=disabled)
                tingwu.submit(args)
                self.assertEqual(api.call_args.args[2]['Parameters']['TextPolishEnabled'], not disabled)
                self.assertEqual(tingwu.read_json(Path(directory)/'lesson.json')['textPolishEnabled'], not disabled)

    def test_sentence_grouping_and_question_source(self):
        raw={'Transcription':{'Transcription':{'Paragraphs':[{'SpeakerId':'2','Words':[
            {'SentenceId':1,'Start':0,'End':500,'Text':'科学'},
            {'SentenceId':1,'Start':500,'End':1000,'Text':'智能'},
            {'SentenceId':2,'Start':1500,'End':2000,'Text':'课程'}]}]}},
            'Summarization':{'Summarization':{'QuestionsAnsweringSummary':[{'Question':'什么？','Answer':'科学智能','SentenceIdsOfQuestion':[1]}]}}}
        result=normalize(raw)
        self.assertEqual(result['transcript'][0]['text'],'科学智能')
        self.assertEqual(result['transcript'][0]['start'],0)
        self.assertEqual(result['questions'][0]['start'],0)
        self.assertEqual(len(result['transcript']),2)

    def test_missing_results_and_timestamps(self):
        result=normalize({'PptExtraction':{'PptExtraction':{'KeyFrameList':[{'FileUrl':'slide.jpg'}]}}})
        self.assertEqual(result['transcript'],[])
        self.assertIsNone(result['slides'][0]['start'])

    def test_reject_path_traversal(self):
        with self.assertRaises(ValueError): valid_id('../secret')

    def test_all_analysis_fields(self):
        raw={'AutoChapters':{'AutoChapters':[{'Start':1200,'End':9000,'Headline':'章节','Summary':'说明'}]},
             'MeetingAssistance':{'MeetingAssistance':{'Keywords':['科学']}},
             'Summarization':{'Summarization':{'ParagraphSummary':'全文','ConversationalSummary':[{'SpeakerId':'1','SpeakerName':'讲者','Summary':'发言'}],
                 'MindMapSummary':[{'Title':'根','Topic':[{'Title':'叶','Topic':[]}]}]}}}
        result=normalize(raw)
        self.assertEqual(result['chapters'][0]['start'],1200)
        self.assertEqual(result['summary'],'全文')
        self.assertEqual(result['keywords'],['科学'])
        self.assertEqual(result['speakers'],[{'speaker':'讲者','summary':'发言'}])
        self.assertEqual(result['mindMap'][0]['children'][0]['title'],'叶')

    def test_collect_persists_images_and_catalog_without_signed_urls(self):
        import json
        documents={
            'https://result/transcript':({'Transcription':{'Paragraphs':[]}},'application/json'),
            'https://result/slides':({'PptExtraction':{'KeyFrameList':[{'FileUrl':'https://result/image?Signature=private','Start':0,'End':1000}]}},'application/json')}
        def downloaded(url):
            if url.startswith('https://result/image'): return b'picture','image/png'
            body,kind=documents[url]
            return json.dumps(body).encode(),kind
        with tempfile.TemporaryDirectory() as directory, patch.object(tingwu,'ROOT',Path(directory)), patch.object(tingwu,'PRIVATE',Path(directory)/'.tingwu'), patch.object(tingwu,'download',downloaded):
            tingwu.collect(argparse.Namespace(id='lesson'),{'id':'lesson','title':'课','date':'2026-09-22','videoUrl':'https://video/lesson.mp4'},
                {'TaskStatus':'COMPLETED','Result':{'Transcription':'https://result/transcript','PptExtraction':'https://result/slides'}})
            path=Path(directory)/'data/lesson.json'
            content=path.read_text(encoding='utf-8')
            self.assertNotIn('Signature',content)
            result=json.loads(content)
            self.assertEqual((Path(directory)/result['slides'][0]['image']).read_bytes(),b'picture')
            self.assertEqual(tingwu.read_json(Path(directory)/'data/courses.json')[0]['id'],'lesson')

if __name__=='__main__': unittest.main()
