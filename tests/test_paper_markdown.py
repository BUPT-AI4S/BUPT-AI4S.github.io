import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class MarkdownPaperTests(unittest.TestCase):
    def site_root(self,tmp):
        root=Path(tmp);(root/'data').mkdir()
        (root/'data/paper-tags.yml').write_text('schemaVersion: 1\ntags: []\n',encoding='utf-8')
        return root
    def module(self):
        spec = importlib.util.spec_from_file_location('index_md', ROOT/'tools/build_paper_index.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def source(self, body='## 方法\n\n**中文**\n\n<!-- language: en -->\n\n## Method\n\nEnglish'):
        return '---\nid: demo\ntitle: Demo\nauthors: [A]\nyear: "2023"\npublished: 2023-01-02\n---\n\n'+body

    def test_markdown_build_produces_light_index_and_bilingual_detail(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            (folder/'demo.md').write_text(self.source(),encoding='utf-8')
            data=self.module().write_index(root,ROOT/'data/papers.schema.json')
            entry=data['papers'][0]
            self.assertEqual(entry['dataUrl'],'data/papers-built/demo.json')
            self.assertEqual(entry['published'],'2023-01-02')
            self.assertTrue(entry['hasNotes'])
            self.assertNotIn('content',entry)
            detail=json.loads((root/entry['dataUrl']).read_text(encoding='utf-8'))
            self.assertIn('<strong>中文</strong>',detail['content']['zh']['html'])
            self.assertEqual(detail['content']['en']['toc'][0]['title'],'Method')

    def test_duplicate_yaml_keys_and_unsafe_tags_fail_without_replacing_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            output=root/'data/papers-index.json';output.write_text('previous',encoding='utf-8')
            for extra in ('title: Another\n', 'title: !!python/object:os.system {}\n'):
                (folder/'demo.md').write_text(self.source().replace('title: Demo\n',extra+'title: Demo\n'),encoding='utf-8')
                with self.assertRaises(ValueError):self.module().write_index(root,ROOT/'data/papers.schema.json')
                self.assertEqual(output.read_text(),'previous')

    def test_local_markdown_image_resolves_and_missing_image_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            images=root/'static/images/papers/demo';images.mkdir(parents=True)
            (images/'plot.png').write_bytes(b'placeholder')
            file=folder/'demo.md'
            file.write_text(self.source('## 方法\n\n![结构](../../static/images/papers/demo/plot.png)'),encoding='utf-8')
            data=self.module().write_index(root,ROOT/'data/papers.schema.json')
            detail=json.loads((root/data['papers'][0]['dataUrl']).read_text(encoding='utf-8'))
            self.assertIn('src="static/images/papers/demo/plot.png"',detail['content']['zh']['html'])
            (images/'plot.png').unlink()
            with self.assertRaisesRegex(ValueError,'image'):self.module().write_index(root,ROOT/'data/papers.schema.json')

    def test_html_is_inert_and_links_are_checked(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            file=folder/'demo.md'
            file.write_text(self.source('## 方法\n\n<script>alert(1)</script>\n\n[代码](https://github.com/example/demo)'),encoding='utf-8')
            data=self.module().write_index(root,ROOT/'data/papers.schema.json')
            html=json.loads((root/data['papers'][0]['dataUrl']).read_text(encoding='utf-8'))['content']['zh']['html']
            self.assertNotIn('<script>',html)
            self.assertIn('rel="noopener noreferrer"',html)
            file.write_text(self.source('[错误](../../.env)'),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'link'):self.module().write_index(root,ROOT/'data/papers.schema.json')

    def test_legacy_json_cannot_inject_generated_html(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            (folder/'demo.json').write_text(json.dumps({'id':'demo','title':'Demo','authors':[],
                'content':{'zh':{'html':'<img src=x onerror=alert(1)>'}}}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'content'):self.module().write_index(root,ROOT/'data/papers.schema.json')

    def test_markdown_heading_links_resolve_after_inserting_another_heading(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers';folder.mkdir(parents=True)
            (folder/'demo.md').write_text(self.source('## Intro\n\n[Jump](#method)\n\n## Method\n\nText'),encoding='utf-8')
            data=self.module().write_index(root,ROOT/'data/papers.schema.json')
            html=json.loads((root/data['papers'][0]['dataUrl']).read_text())['content']['zh']['html']
            self.assertIn('href="#md-zh-method"',html)
            self.assertIn('id="md-zh-method"',html)

    def test_paper_directory_contains_source_and_its_images_in_published_site(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers/demo';images=folder/'images';images.mkdir(parents=True)
            (images/'plot.png').write_bytes(b'placeholder')
            (folder/'paper.md').write_text(self.source('## 方法\n\n![结构](images/plot.png)'),encoding='utf-8')
            other=root/'data/papers/other';other.mkdir()
            (other/'paper.md').write_text(self.source('## Another').replace('id: demo','id: other'),encoding='utf-8')
            m=self.module();data=m.write_index(root,ROOT/'data/papers.schema.json')
            entry=data['papers'][0]
            self.assertEqual(entry['sourceUrl'],'data/papers/demo/paper.md')
            self.assertEqual(entry['dataUrl'],'data/papers-built/demo.json')
            detail=json.loads((root/entry['dataUrl']).read_text(encoding='utf-8'))
            self.assertIn('src="data/papers/demo/images/plot.png"',detail['content']['zh']['html'])
            site=m.stage_site(root)
            self.assertTrue((site/'data/papers/demo/paper.md').is_file())
            self.assertTrue((site/'data/papers/demo/images/plot.png').is_file())
            (images/'plot.png').unlink()
            with self.assertRaisesRegex(ValueError,'image'):m.write_index(root,ROOT/'data/papers.schema.json')

    def test_paper_directory_image_cannot_reference_another_paper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=self.site_root(tmp);folder=root/'data/papers/demo';folder.mkdir(parents=True)
            other=root/'data/papers/other/images';other.mkdir(parents=True)
            (other/'plot.png').write_bytes(b'placeholder')
            (other.parent/'paper.md').write_text(self.source().replace('id: demo','id: other'),encoding='utf-8')
            (folder/'paper.md').write_text(self.source('![图](../other/images/plot.png)'),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'image'):self.module().write_index(root,ROOT/'data/papers.schema.json')


if __name__=='__main__':unittest.main()
