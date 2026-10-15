import importlib.util
from pathlib import Path
import tempfile
import unittest
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]

class BlogImportTests(unittest.TestCase):
    def test_series_intro_is_preserved_and_word_heading_styles_form_sections(self):
        spec=importlib.util.spec_from_file_location('blog_import',ROOT/'tools/import_blog_docx.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);source=root/'source.docx'
            with ZipFile(source,'w') as archive:
                archive.writestr('word/document.xml','''<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body>
<w:p><w:pPr><w:pStyle w:val="title"/></w:pPr><w:r><w:t>Article title</w:t></w:r></w:p>
<w:p><w:r><w:t>The first substantive paragraph must stay in the body.</w:t></w:r></w:p>
<w:p><w:pPr><w:pStyle w:val="section"/></w:pPr><w:r><w:t>A section heading</w:t></w:r></w:p>
<w:p><w:r><w:t>Scientific evidence.</w:t></w:r></w:p>
</w:body></w:document>''')
                archive.writestr('word/styles.xml','''<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:style w:styleId="title"><w:name w:val="heading 1"/></w:style><w:style w:styleId="section"><w:name w:val="heading 2"/></w:style></w:styles>''')
                archive.writestr('word/_rels/document.xml.rels','<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"/>')
            _,result=module.import_document(source,'sample','article',root=root)
            self.assertEqual(result['subtitle'],'')
            self.assertEqual(result['blocks'][0],{'type':'paragraph','text':'The first substantive paragraph must stay in the body.'})
            self.assertEqual(result['blocks'][1],{'type':'heading','level':2,'text':'A section heading'})
