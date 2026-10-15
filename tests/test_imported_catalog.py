import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]


class ImportedCatalogTests(unittest.TestCase):
    def builder(self):
        spec=importlib.util.spec_from_file_location('import_builder',ROOT/'tools/build_paper_index.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module

    def setup_root(self,tmp):
        root=Path(tmp);(root/'data/papers').mkdir(parents=True)
        (root/'data/imported').mkdir()
        (root/'data/paper-tags.yml').write_text('schemaVersion: 1\ntags: []\n',encoding='utf-8')
        return root

    def write_import(self,root,papers):
        (root/'data/imported/ai4s-2026.json').write_text(json.dumps({'schemaVersion':1,'source':'source','papers':papers}),encoding='utf-8')

    def test_bulk_records_have_working_details_and_unknown_resource_flags(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.setup_root(tmp)
            self.write_import(root,[{'id':'import-2026-test-one','title':'Science paper','authors':[], 'year':'2026','abstract':'Original abstract','imported':True,'hasNotes':False,'codeAvailability':'unknown','pdfAvailability':'unresolved','metadataProvenance':{'originalIds':['one']}}])
            data=self.builder().write_index(root,ROOT/'data/papers.schema.json')
            self.assertEqual(len(data['papers']),1)
            entry=data['papers'][0]
            self.assertFalse(entry['hasNotes']);self.assertTrue(entry['imported'])
            self.assertEqual(entry['codeAvailability'],'unknown')
            detail=json.loads((root/entry['dataUrl']).read_text(encoding='utf-8'))
            self.assertEqual(detail['metadataProvenance']['originalIds'],['one'])
            self.assertEqual(detail['content']['zh']['html'],'')
            self.assertNotIn('notesMeta',detail)

    def test_human_authored_paper_wins_same_title_and_year(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.setup_root(tmp)
            authored={'id':'curated','title':'Science Paper','authors':['Alice'],'year':'2026','abstract':'Reviewed abstract'}
            (root/'data/papers/curated.json').write_text(json.dumps(authored),encoding='utf-8')
            self.write_import(root,[{'id':'import-one','title':'Science Paper!','authors':['Alice'],'year':'2026','abstract':'Imported abstract','imported':True}])
            data=self.builder().write_index(root,ROOT/'data/papers.schema.json')
            self.assertEqual([p['id'] for p in data['papers']],['curated'])
            self.assertEqual(data['papers'][0]['abstract'],'Reviewed abstract')

    def test_unsafe_ids_and_generated_html_in_bulk_data_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.setup_root(tmp)
            for extra in [{'id':'../../escape'}, {'id':'okay','content':{'zh':{'html':'<script>bad</script>'}}}]:
                self.write_import(root,[{'title':'Paper','authors':[],**extra}])
                with self.assertRaises(ValueError):self.builder().write_index(root,ROOT/'data/papers.schema.json')

    def test_import_cannot_overwrite_authored_detail_filename(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.setup_root(tmp)
            (root/'data/papers/reserved.json').write_text(json.dumps({'id':'curated','title':'Authored','authors':[]}),encoding='utf-8')
            self.write_import(root,[{'id':'RESERVED','title':'Different paper','authors':[]}])
            with self.assertRaisesRegex(ValueError,'filename'):
                self.builder().write_index(root,ROOT/'data/papers.schema.json')


if __name__=='__main__':unittest.main()
