import sys
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from import_ai4s_metadata import adapt_record,merge_record,update_catalog


class MetadataUpdateTests(unittest.TestCase):
    def raw(self,**extra):
        return dict(title='Science Paper',authors=['Alice Smith'],venue='icml',year=2026,
                    url='https://example.org/paper',ai4s_tags=['科学数据'],**extra)

    def test_supplied_categories_replace_keyword_guesses_and_preserve_unknown_labels(self):
        p=adapt_record(self.raw(abstract='Protein and molecular foundation model',ai4s_tagging={'status':'classified'}),'new.json')
        self.assertEqual(p['disciplines'],['scientific-data'])
        self.assertEqual(p['classificationStatus'],'source-provided')
        raw=self.raw();raw['ai4s_tags']=['科研工具','AI for 工程科学']
        p=adapt_record(raw,'new.json')
        self.assertEqual(p['disciplines'],[])
        self.assertEqual(p['metadataProvenance']['sourceAi4sTags'],raw['ai4s_tags'])
        self.assertEqual(p['classificationStatus'],'needs-review')

    def test_published_version_replaces_preprint_across_years_without_changing_id(self):
        old={'id':'stable','title':'Science Paper!','authors':['Alice Smith'],'venue':'arXiv','year':'2025','paperUrl':'https://arxiv.org/abs/2501.01234','pdfUrl':'https://arxiv.org/pdf/2501.01234','notes':[{'id':'summary'}]}
        new=adapt_record(self.raw(pdf_url='https://example.org/paper.pdf'),'new.json')
        result=update_catalog([old],[new])
        self.assertEqual(len(result['papers']),1)
        p=result['papers'][0]
        self.assertEqual((p['id'],p['venue'],p['year']),('stable','ICML','2026'))
        self.assertEqual(p['notes'],old['notes'])
        self.assertEqual(p['arxivUrl'],old['paperUrl'])

    def test_preprint_never_downgrades_published_metadata(self):
        formal=adapt_record(self.raw(pdf_url='https://example.org/paper.pdf'),'old.json')
        raw=self.raw();raw.update(venue='arxiv',year=2025,url='https://arxiv.org/abs/2501.01234')
        p=merge_record(formal,adapt_record(raw,'new.json'))
        self.assertEqual((p['venue'],p['year'],p['paperUrl']),('ICML','2026','https://example.org/paper'))

    def test_updates_preserve_existing_pdf_when_source_does_not_supply_one(self):
        old=adapt_record(self.raw(pdf_url='https://example.org/paper.pdf'),'old.json')
        p=merge_record(old,adapt_record(self.raw(abstract='Updated abstract'),'new.json'))
        self.assertEqual(p['abstract'],'Updated abstract')
        self.assertEqual(p['pdfUrl'],old['pdfUrl'])

    def test_explicit_non_ai4s_removes_matching_old_record_but_keeps_absent_records(self):
        old=adapt_record(self.raw(),'old.json');other={**old,'id':'other','title':'Other Paper','paperUrl':'https://example.org/other'}
        raw=self.raw();raw['ai4s_tags']=['非AI4S（当前口径）'];raw['ai4s_tagging']={'status':'out_of_scope'}
        result=update_catalog([old,other],[adapt_record(raw,'new.json')])
        self.assertEqual([p['id'] for p in result['papers']],['other'])
        self.assertEqual(len(result['excluded']),1)

    def test_same_generic_title_with_different_authors_is_not_merged(self):
        old=adapt_record(self.raw(),'old.json')
        new={**adapt_record(self.raw(),'new.json'),'id':'different','authors':['Bob Jones'],'paperUrl':'https://example.org/different'}
        self.assertEqual(len(update_catalog([old],[new])['papers']),2)

    def test_authored_content_and_translation_are_preserved(self):
        old=adapt_record(self.raw(),'old.json');old.update(id='curated',abstract='Edited abstract',titleZh='人工翻译',notes=[{'id':'summary'}])
        new=adapt_record(self.raw(abstract='Source abstract'),'new.json')
        p=merge_record(old,new,authored=True)
        self.assertEqual((p['id'],p['abstract'],p['titleZh'],p['notes']),('curated','Edited abstract','人工翻译',[{'id':'summary'}]))

    def test_final_publisher_links_are_not_downgraded_to_openreview(self):
        old=adapt_record(self.raw(),'old.json');old.update(paperUrl='https://proceedings.mlr.press/v306/paper.html',pdfUrl='https://proceedings.mlr.press/v306/paper.pdf')
        raw=self.raw();raw.update(url='https://openreview.net/forum?id=abc',pdf_url='https://openreview.net/pdf?id=abc')
        for authored in (False,True):
            p=merge_record(old,adapt_record(raw,'new.json'),authored=authored)
            self.assertEqual((p['paperUrl'],p['pdfUrl']),(old['paperUrl'],old['pdfUrl']))


if __name__=='__main__':unittest.main()
