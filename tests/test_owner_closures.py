import unittest
from copy import deepcopy
from test_review_monitor import HistoricalAbstractStateTest
from test_nonresearch_additions import NonresearchOverlayTest


class OwnerClosureTest(unittest.TestCase):
    def fixture(self):
        x = HistoricalAbstractStateTest().fixture()
        proof = {'status':'closed_by_owner','reason':'access_restricted_excluded_by_owner',
                 'checked_at':'2026-11-15','checked_by':'A','user_instruction':'exclude inaccessible item',
                 'access_status':'publisher restricted','evidence_urls':['https://publisher.example/article']}
        x[1][0].update(abstract=None, abstract_requirement=deepcopy(proof))
        x[2][0]['ai4s_review'].update(decision='exclude',abstract_requirement=deepcopy(proof))
        return x

    def test_closed_access_gap_stays_distinct_from_official_absence(self):
        source, other = HistoricalAbstractStateTest().render(self.fixture())
        self.assertEqual(source['issues'], [])
        self.assertEqual(source['missing_abstract'], 1)
        self.assertEqual(source['abstract_closed_by_owner'], 1)
        self.assertEqual(source['abstract_not_required'], 0)
        self.assertEqual(source['state'], 'abstract_incomplete')
        self.assertTrue(other['issues'])

    def test_unapproved_incomplete_and_conflicting_cases_remain_actionable(self):
        cases = []
        for key in ['status','reason','checked_by','checked_at','user_instruction','access_status','evidence_urls']:
            cases.append((key, lambda x,key=key: x[1][0]['abstract_requirement'].pop(key)))
        cases += [
            ('include',lambda x:x[2][0]['ai4s_review'].update(decision='include')),
            ('pending',lambda x:x[2][0]['ai4s_review'].update(decision='pending')),
            ('wrong owner',lambda x:x[2][0]['ai4s_review'].update(owner='B')),
            ('old snapshot',lambda x:x[2][0]['ai4s_review'].update(snapshot_at='old')),
            ('different instruction',lambda x:x[2][0]['ai4s_review']['abstract_requirement'].update(user_instruction='different')),
            ('conflict',lambda x:x[2].append(dict(deepcopy(x[2][0]),ai4s_review={'decision':'include','owner':'A','snapshot_at':'current'}))),
        ]
        for name, mutate in cases:
            with self.subTest(name=name):
                x=self.fixture(); mutate(x)
                source=HistoricalAbstractStateTest().render(x)[0]
                self.assertEqual(source['abstract_supplement_required'],1)
                self.assertEqual(source['abstract_closed_by_owner'],0)
                self.assertTrue(source['issues'])


class NormalizedCatalogueTest(unittest.TestCase):
    def fixture(self):
        x=NonresearchOverlayTest().fixture(); s,c,r,f,raw,adds,report=x
        f['official_total']=2
        f['collection_state_resolution']['reason']='full_catalogue_with_documented_normalization_candidates_complete'
        f['catalogue_reconciliation'].update(same_scope_extra=1,canonical_total=2,canonical_missing=0,canonical_extra=0)
        raw[1]['title']='WITHDRAWN: Letter'
        adds[0].update(article_type='Corrigendum',screening_disposition='exclude_non_original_corrigendum',pii='P3',evidence_urls=[adds[0]['url']])
        report.update(official_total=2,raw_page_differences=[],
            matched_canonical_records=[{'id':'one'},{'id':'three','pii':'P3','title':'Highlight','url':adds[0]['url']}],
            raw_missing_before_overlay=[{'pii':'P3'}],raw_only_before_overlay=[{'id':'two','pii':'P2'}],
            canonical_resolution={'status':'complete','canonical_missing':[],'canonical_extra':[],
                'canonical_total':2,'excluded_raw_ids':['two'],'excluded_raw_reason':'Withdrawn Article in Press without issue',
                'evidence_url':'https://www.sciencedirect.com/science/article/pii/P2'})
        return x

    def test_verified_normalization_preserves_raw_count_and_closes(self):
        a,b=NonresearchOverlayTest().render(self.fixture())
        self.assertEqual(a['issues'],[]);self.assertEqual(a['papers'],2);self.assertTrue(b['issues'])

    def test_invalid_normalizations_remain_actionable(self):
        cases=[
            ('withdrawn proof',lambda s,c,r,f,raw,a,m:raw[1].update(title='Research paper')),
            ('missing identity',lambda s,c,r,f,raw,a,m:m['matched_canonical_records'][1].update(id='wrong')),
            ('duplicate official',lambda s,c,r,f,raw,a,m:m['matched_canonical_records'].append(deepcopy(m['matched_canonical_records'][0]))),
            ('different extra',lambda s,c,r,f,raw,a,m:m['raw_only_before_overlay'][0].update(id='one')),
            ('wrong evidence',lambda s,c,r,f,raw,a,m:m['canonical_resolution'].update(evidence_url='https://elsewhere.example/')),
            ('unresolved',lambda s,c,r,f,raw,a,m:m['canonical_resolution'].update(canonical_missing=['four'])),
            ('research addition',lambda s,c,r,f,raw,a,m:a[0].update(article_type='Research article')),
            ('wrong owner',lambda s,c,r,f,raw,a,m:m.update(owner='B')),
            ('stale snapshot',lambda s,c,r,f,raw,a,m:m.update(snapshot_at='old')),
            ('missing evidence',lambda s,c,r,f,raw,a,m:a[0].update(evidence_urls=[])),
        ]
        for name,mutate in cases:
            with self.subTest(name=name):
                x=self.fixture();mutate(*x)
                source=NonresearchOverlayTest().render(x)[0]
                self.assertTrue(source['issues']);self.assertNotIn('collection_state_resolution',source)


class SparseCatalogueAuditTest(unittest.TestCase):
    def test_identity_audits_work_without_full_raw_checkout_and_reject_bad_provenance(self):
        for fixture in [NonresearchOverlayTest().fixture, NormalizedCatalogueTest().fixture]:
            x=fixture();s,c,r,f,raw,adds,report=x
            f['catalogue_audit']={'source_code':'v','year':2025,'owner':'A','snapshot_at':'current',
                'input_main_commit':'a'*40,'raw_sha256':'b'*64,
                'details_file':'metadata/v/2025/catalogue-reconciliation.json',
                'raw_identities':raw,'additions':adds,'report':report}
            self.assertEqual(NonresearchOverlayTest().render(x,False)[0]['issues'],[])
            for key,value in [('owner','B'),('snapshot_at','old'),('raw_sha256',''),('input_main_commit',''),('details_file','unrelated.json')]:
                with self.subTest(fixture=fixture,key=key):
                    y=deepcopy(x);y[3]['catalogue_audit'][key]=value
                    self.assertTrue(NonresearchOverlayTest().render(y,False)[0]['issues'])
