import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]


class NewsImportTests(unittest.TestCase):
    def test_published_news_contains_all_original_images_and_section_captions(self):
        import json
        catalog=json.loads((ROOT/'data/news-index.json').read_text(encoding='utf-8'))
        self.assertEqual(len(catalog['articles']),1)
        entry=catalog['articles'][0]
        article=json.loads((ROOT/'data/news/articles'/f'{entry["id"]}.json').read_text(encoding='utf-8'))
        self.assertEqual([block['number'] for block in article['blocks'] if block['type']=='heading'],['01','02','03','04'])
        images=[block for block in article['blocks'] if block['type']=='image']
        galleries=[block for block in article['blocks'] if block['type']=='gallery']
        self.assertEqual(len(images),8)
        self.assertEqual(len(galleries),1)
        self.assertEqual(len(galleries[0]['images']),3)
        for item in images+galleries[0]['images']:
            self.assertTrue((ROOT/item['src']).is_file())
        source=ROOT.parent/'与大咖对话.docx'
        if source.exists():
            import xml.etree.ElementTree as ET
            with ZipFile(source) as archive:
                for image in images+galleries[0]['images']:
                    self.assertEqual((ROOT/image['src']).read_bytes(),archive.read('word/media/'+Path(image['src']).name))
                paragraphs=[''.join(node.text or '' for node in p.findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')).strip() for p in ET.fromstring(archive.read('word/document.xml')).findall('.//{http://schemas.openxmlformats.org/wordprocessingml/2006/main}body/{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p')]
            values=[article['title'],article['source'],article['subtitle']]+[block.get('text',block.get('caption','')) for block in article['blocks']]
            for paragraph in paragraphs:
                if paragraph and paragraph not in ['01','02','03','04']:
                    self.assertIn(paragraph,values)

    def test_paragraphs_section_markers_gallery_and_original_image_bytes_are_preserved(self):
        spec=importlib.util.spec_from_file_location('news_import',ROOT/'tools/import_news_docx.py')
        importer=importlib.util.module_from_spec(spec);spec.loader.exec_module(importer)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'input.docx'
            with ZipFile(source,'w') as z:
                z.writestr('word/document.xml','''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><w:body>
<w:p><w:r><w:t>Title</w:t></w:r></w:p><w:p><w:r><w:t>Byline</w:t></w:r></w:p><w:p><w:r><w:t>Course</w:t></w:r></w:p>
<w:p><w:r><w:t>Introduction.</w:t></w:r></w:p><w:p><w:r><w:t>01</w:t></w:r></w:p><w:p><w:r><w:t>A section</w:t></w:r></w:p>
<w:p><w:r><w:drawing><a:blip r:embed="a"/></w:drawing></w:r></w:p><w:p><w:r><w:t>图1｜Source caption</w:t></w:r></w:p>
<w:p><w:r><w:t>Evidence stays.</w:t></w:r></w:p><w:p><w:r><w:drawing><a:blip r:embed="b"/><a:blip r:embed="c"/></w:drawing></w:r></w:p>
</w:body></w:document>''')
                z.writestr('word/_rels/document.xml.rels','''<Relationships><Relationship Id="a" Target="media/a.png"/><Relationship Id="b" Target="media/b.png"/><Relationship Id="c" Target="media/c.png"/></Relationships>''')
                for name in 'abc':z.writestr(f'word/media/{name}.png',name.encode())
            article=importer.import_document(source,'dialogue','2026-10-23',root)
            self.assertEqual(article['title'],'Title')
            self.assertEqual([b['type'] for b in article['blocks']],['paragraph','heading','image','paragraph','gallery'])
            self.assertEqual(article['blocks'][1],dict(type='heading',number='01',text='A section',id='section-01'))
            self.assertEqual(article['blocks'][2]['caption'],'图1｜Source caption')
            self.assertEqual(article['blocks'][3]['text'],'Evidence stays.')
            self.assertEqual(len(article['blocks'][4]['images']),2)
            self.assertEqual((root/article['blocks'][2]['src']).read_bytes(),b'a')


if __name__=='__main__':unittest.main()
