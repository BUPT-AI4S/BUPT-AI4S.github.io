import importlib.util
from pathlib import Path
import unittest
import tempfile
import subprocess
import json
import sys

spec = importlib.util.spec_from_file_location('collector', Path(__file__).resolve().parents[1] / 'tools' / 'collect_openreview.py')

class CollectorTests(unittest.TestCase):
    def module(self):
        self.assertTrue(Path(spec.origin).exists(), 'OpenReview collector is not implemented')
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    def test_normalizes_api2_and_keeps_missing_translation_unknown(self):
        m = self.module()
        note = {'id':'abc', 'forum':'abc', 'number':12, 'readers':['everyone'], 'cdate':1704067200000,
                'content':{'title':{'value':'Climate prediction'}, 'abstract':{'value':'Weather forecasts'},
                           'authors':{'value':['A']}, 'keywords':{'value':['Climate']},
                           'venue':{'value':'ICLR 2024 poster'}, 'venueid':{'value':'ICLR.cc/2024/Conference'},
                           'pdf':{'value':'/pdf?id=abc'}}}
        p = m.normalize_note(note)
        self.assertEqual(p['abstract'], 'Weather forecasts')
        self.assertEqual(p['pdfUrl'], 'https://openreview.net/pdf?id=abc')
        self.assertEqual(p['forumUrl'], 'https://openreview.net/forum?id=abc')
        self.assertEqual(p['titleZh'], '')
        self.assertEqual(p['disciplines'], [])
        self.assertIn('weather', p['disciplineSuggestions'])
        self.assertEqual(p['decision'], 'Poster')
        self.assertEqual(p['year'], '2024')

    def test_curated_fields_survive_refresh_and_duplicate_id_is_merged(self):
        m = self.module()
        old = [{'id':'abc', 'title':'Old', 'titleZh':'中文标题', 'disciplines':['weather'], 'sample':True}]
        new = [{'id':'abc', 'title':'New', 'titleZh':'', 'disciplines':[], 'keywords':['new']}]
        result = m.merge_papers(old, new)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]['title'], 'New')
        self.assertEqual(result[0]['titleZh'], '中文标题')
        self.assertEqual(result[0]['disciplines'], ['weather'])
        self.assertTrue(result[0]['sample'])

    def test_bad_metadata_fails_instead_of_silently_dropping_content(self):
        m = self.module()
        with self.assertRaises(ValueError):
            m.normalize_note({'id':'bad', 'readers':['everyone'], 'content':{'title':{'value':''}}})

    def test_pagination_uses_offset_and_collects_every_page(self):
        m = self.module()
        offsets = []
        def request(base, endpoint, params):
            offsets.append(params['offset'])
            return {'notes': [{'id':str(i),'readers':['everyone']} for i in range(100)] if params['offset'] == 0 else [{'id':'last','readers':['everyone']}]}
        self.assertEqual(len(m.fetch_notes('https://api2.openreview.net', {'invitation':'test'}, 0, request)), 101)
        self.assertEqual(offsets, [0,100])

    def test_offline_cli_import_and_editorial_csv_without_network(self):
        with tempfile.TemporaryDirectory() as temp:
            temp = Path(temp)
            raw, output, csv = temp/'notes.json', temp/'papers.json', temp/'editorial.csv'
            raw.write_text(json.dumps({'notes':[{'id':'a','readers':['everyone'],'content':{'title':{'value':'Climate model'},'abstract':{'value':'Weather'}}}]}),encoding='utf-8')
            command = [sys.executable, spec.origin, '--input', str(raw), '--output', str(output)]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode, 0)
            csv.write_text('id,titleZh,disciplines,subfield\na,天气模型,weather|physics,Forecasting\n',encoding='utf-8')
            command = [sys.executable, spec.origin, '--editorial-only','--overrides',str(csv),'--output',str(output)]
            self.assertEqual(subprocess.run(command,capture_output=True).returncode,0)
            data=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(data['papers'][0]['disciplines'],['weather','physics'])
            self.assertEqual(data['papers'][0]['titleZh'],'天气模型')
            previous=output.read_bytes()
            csv.write_text('id,titleZh\nmissing,坏数据\n',encoding='utf-8')
            self.assertNotEqual(subprocess.run(command,capture_output=True).returncode,0)
            self.assertEqual(output.read_bytes(),previous)

    def test_private_submissions_and_decisions_are_never_exported(self):
        m = self.module()
        with self.assertRaises(ValueError):
            m.normalize_note({'id':'secret','readers':['Private/Group'],'content':{'title':'Private title'}})
        public = {'id':'public','readers':['everyone'],'content':{'title':'Public title'},
                  'details':{'directReplies':[{'readers':['Private/Group'],'invitation':'Venue/Paper/-/Decision','content':{'decision':'Private decision'}}]}}
        self.assertEqual(m.normalize_note(public)['decision'], '')
        public['content']['authors'] = {'value':['Private author'], 'readers':['Private/Group']}
        self.assertEqual(m.normalize_note(public)['authors'], [])

    def test_directory_import_keeps_filename_and_curated_notes(self):
        with tempfile.TemporaryDirectory() as temp:
            temp=Path(temp);folder=temp/'papers';folder.mkdir()
            existing=folder/'chosen-name.md'
            existing.write_text('---\nid: a\ntitle: Old\nauthors: []\n---\n\n## 方法\n\n保留\n\n<!-- language: en -->\n\n## Method\n\nKeep\n',encoding='utf-8')
            raw=temp/'notes.json';raw.write_text(json.dumps({'notes':[{'id':'a','readers':['everyone'],'content':{'title':'New'}}]}),encoding='utf-8')
            result=subprocess.run([sys.executable,spec.origin,'--input',str(raw),'--output',str(folder)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            text=existing.read_text(encoding='utf-8')
            self.assertIn('title: New',text)
            self.assertIn('## Method\n\nKeep',text)
            self.assertIn('## 方法\n\n保留',text)
            self.assertEqual(len(list(folder.glob('*.md'))),1)
            self.assertEqual(len(list(folder.glob('*.json'))),0)
            self.assertTrue((temp/'papers-index.json').exists())

    def test_refresh_legacy_json_does_not_create_duplicate_markdown(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'papers';folder.mkdir()
            file=folder/'old.json';file.write_text(json.dumps({'id':'a','title':'Old','authors':[]}),encoding='utf-8')
            raw=root/'input.json';raw.write_text(json.dumps({'notes':[{'id':'a','readers':['everyone'],'content':{'title':'New'}}]}),encoding='utf-8')
            result=subprocess.run([sys.executable,spec.origin,'--input',str(raw),'--output',str(folder)],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(file.read_text())['title'],'New')
            self.assertEqual(list(folder.glob('*.md')),[])

    def test_import_rejects_cross_extension_filename_collision_before_writing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'papers';folder.mkdir()
            file=folder/'new-id.json';previous=json.dumps({'id':'old-id','title':'Old','authors':[]})
            file.write_text(previous,encoding='utf-8')
            raw=root/'input.json';raw.write_text(json.dumps({'notes':[{'id':'new-id','readers':['everyone'],'content':{'title':'New'}}]}),encoding='utf-8')
            result=subprocess.run([sys.executable,spec.origin,'--input',str(raw),'--output',str(folder)],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(list(folder.glob('*.md')),[])
            self.assertEqual(file.read_text(),previous)

if __name__ == '__main__': unittest.main()
