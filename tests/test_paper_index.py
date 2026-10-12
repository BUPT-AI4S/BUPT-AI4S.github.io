import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]

class PaperIndexTests(unittest.TestCase):
    def vocabulary(self,root):
        (root/'data/paper-tags.yml').write_text('schemaVersion: 1\ntags:\n  - id: climate\n    nameEn: Climate\n    nameZh: 气候\n    aliases: []\n',encoding='utf-8')
    def module(self):
        spec=importlib.util.spec_from_file_location('paper_index',ROOT/'tools/build_paper_index.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def paper(self,id='a'):
        return {'id':id,'title':'Test paper','authors':['A'], 'tags':['Climate'],
                'notes':[{'id':'method','headingZh':'方法','headingEn':'Method','textZh':'中文','textEn':'English'}]}

    def test_index_is_lightweight_and_preserves_detail_path(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            folder=Path(tmp)/'data/papers';folder.mkdir(parents=True)
            self.vocabulary(Path(tmp))
            (folder/'example.json').write_text(json.dumps(self.paper()),encoding='utf-8')
            data=m.build_index(folder,ROOT/'data/papers.schema.json',{'tagTranslations':{'Climate':'气候'}},Path(tmp))
            item=data['papers'][0]
            self.assertEqual(item['dataUrl'],'data/papers-built/example.json')
            self.assertTrue(item['hasNotes'])
            self.assertNotIn('notes',item)
            self.assertNotIn('figures',item)
            self.assertEqual(data['tagTranslations']['climate'],'气候')

    def test_invalid_file_duplicate_id_and_missing_image_are_rejected(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            self.vocabulary(root)
            a=folder/'a.json';a.write_text(json.dumps(self.paper()),encoding='utf-8')
            b=folder/'b.json';b.write_text(json.dumps(self.paper()),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Duplicate'):m.build_index(folder,ROOT/'data/papers.schema.json',{},root)
            b.unlink()
            p=self.paper();p['authors']='not an array';a.write_text(json.dumps(p),encoding='utf-8')
            with self.assertRaises(ValueError):m.build_index(folder,ROOT/'data/papers.schema.json',{},root)
            p=self.paper();p['figures']=[{'src':'static/images/papers/missing.svg','altZh':'图','altEn':'Figure','captionZh':'图','captionEn':'Figure'}];a.write_text(json.dumps(p),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'image'):m.build_index(folder,ROOT/'data/papers.schema.json',{},root)

    def test_failed_build_keeps_previous_index(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            self.vocabulary(root)
            (folder/'a.json').write_text('{bad json',encoding='utf-8')
            output=root/'data/papers-index.json';output.write_text('previous',encoding='utf-8')
            with self.assertRaises(ValueError):m.write_index(root,schema_path=ROOT/'data/papers.schema.json')
            self.assertEqual(output.read_text(encoding='utf-8'),'previous')

    def test_site_staging_excludes_private_files_and_includes_course_assets(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)
            (root/'static').mkdir();(root/'data').mkdir();(root/'course_material').mkdir()
            (root/'index.html').write_text('site',encoding='utf-8')
            (root/'.env').write_text('secret',encoding='utf-8')
            (root/'data/x.local.json').write_text('private path',encoding='utf-8')
            (root/'course_material/lesson.pdf').write_text('public',encoding='utf-8')
            site=m.stage_site(root)
            self.assertTrue((site/'index.html').exists())
            self.assertTrue((site/'course_material/lesson.pdf').exists())
            self.assertFalse((site/'.env').exists())
            self.assertFalse((site/'data/x.local.json').exists())

    def test_reserved_local_filename_is_rejected_before_publishing(self):
        m=self.module()
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            self.vocabulary(root)
            (folder/'example.local.json').write_text(json.dumps(self.paper()),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'reserved'):m.build_index(folder,ROOT/'data/papers.schema.json',{},root)

if __name__=='__main__':unittest.main()
