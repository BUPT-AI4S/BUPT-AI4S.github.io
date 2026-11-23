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


class WithdrawnOnlyNormalizationTest(unittest.TestCase):
    def fixture(self):
        x=NormalizedCatalogueTest().fixture();s,c,r,f,raw,adds,report=x
        adds.clear();f['official_total']=1
        f['catalogue_reconciliation'].update(same_scope_missing=0,canonical_total=1)
        report.update(official_total=1,matched_canonical_records=[{'id':'one'}],raw_missing_before_overlay=[])
        report['canonical_resolution'].update(canonical_total=1)
        report['canonical_resolution'].pop('evidence_url')
        report['raw_only_before_overlay'][0]['withdrawal_evidence']={
            'status':'withdrawn_unassigned_online','id':'two','pii':'P2','checked_at':'2026-11-15',
            'checked_by':'A','publisher_withdrawal_notice':'Withdrawn due to publisher error',
            'evidence_urls':['https://pubmed.ncbi.nlm.nih.gov/123/']}
        return x

    def test_no_addition_is_needed_when_all_difference_is_verified_withdrawal(self):
        source=NonresearchOverlayTest().render(self.fixture())[0]
        self.assertEqual(source['issues'],[])
        self.assertEqual(source['papers'],2);self.assertEqual(source['official_total'],1)

    def test_no_unverified_extra_can_be_dismissed(self):
        for key in ['status','id','pii','checked_at','checked_by','publisher_withdrawal_notice','evidence_urls']:
            with self.subTest(key=key):
                x=self.fixture();x[6]['raw_only_before_overlay'][0]['withdrawal_evidence'].pop(key)
                self.assertTrue(NonresearchOverlayTest().render(x)[0]['issues'])


class EmptyCatalogueCandidateTest(unittest.TestCase):
    def fixture(self):
        x=HistoricalAbstractStateTest().fixture()
        x[1].clear();x[2].clear()
        x[3].update(candidate_count=0,own_review_count=0,work_status='complete',
            own_review_counts=dict.fromkeys(('include','exclude','pending','unreviewed'),0))
        x[3]['collection_state_resolution']['reason']='full_catalogue_no_candidates'
        return x

    def test_explicit_audited_zero_candidates_close_without_placeholder_reviews(self):
        source,other=HistoricalAbstractStateTest().render(self.fixture())
        self.assertEqual(source['issues'],[])
        self.assertEqual(source['candidates'],0)
        self.assertEqual(source['state'],'abstract_incomplete')
        self.assertTrue(other['issues'])

    def test_empty_missing_or_nonzero_work_is_not_implicitly_complete(self):
        cases=[lambda x:x[3].pop('candidate_count'),
            lambda x:x[3].update(own_review_count=1),
            lambda x:x[3].update(work_status='partial'),
            lambda x:x[3]['own_review_counts'].update(pending=1),
            lambda x:x[3]['catalogue_reconciliation'].update(same_scope_missing=1),
            lambda x:x[3].update(official_total=3),
            lambda x:x[3]['collection_state_resolution'].update(reason='full_catalogue_abstract_gap_candidates_complete'),
            lambda x:x[1].append({'year':2025,'venue':'v','id':'one','abstract':'Original abstract'})]
        for change in cases:
            x=self.fixture();change(x)
            self.assertTrue(HistoricalAbstractStateTest().render(x)[0]['issues'])


class ReferenceCatalogueClosureTest(unittest.TestCase):
    def fixture(self):
        x=HistoricalAbstractStateTest().fixture();s,c,r,f=x
        f['official_total']=None;f['official_scope']=''
        f['reference_check']={'status':'complete','source':'Crossref + PubMed','total':2,
            'scope':'formal print2025 all types','query_url':'https://api.crossref.org/journals/1234/works',
            'checked_at':'2026-11-15','unresolved':0}
        f['collection_state_resolution']['reason']='full_reference_catalogue_candidates_complete'
        f['catalogue_audit']={'source_code':'v','year':2025,'owner':'A','snapshot_at':'current',
            'input_main_commit':'a'*40,'raw_sha256':'b'*64,
            'details_file':'metadata/v/2025/catalogue-reconciliation.json',
            'raw_identities':[{'id':i,'venue':'v','year':2025}for i in ['one','two']],
            'additions':[],'report':{'source_code':'v','year':2025,'owner':'A','snapshot_at':'current',
                'reference_check':deepcopy(f['reference_check']),'matched_reference_ids':['one','two']}}
        return x

    def test_exact_reference_catalogue_closes_without_inventing_official_total(self):
        a,b=HistoricalAbstractStateTest().render(self.fixture())
        self.assertEqual(a['issues'],[]);self.assertIsNone(a['official_total'])
        self.assertEqual(a['reference_check']['total'],2)
        self.assertEqual(a['state'],'abstract_incomplete');self.assertTrue(b['issues'])

    def test_partial_stale_or_conflicting_reference_audits_do_not_close(self):
        cases=[lambda x:x[3]['catalogue_audit']['report']['matched_reference_ids'].pop(),
            lambda x:x[3]['catalogue_audit']['report'].update(matched_reference_ids=['one','one']),
            lambda x:x[3]['catalogue_audit']['report'].update(matched_reference_ids=['one','wrong']),
            lambda x:x[3]['catalogue_audit'].update(owner='B'),
            lambda x:x[3]['catalogue_audit'].update(snapshot_at='old'),
            lambda x:x[3]['catalogue_audit']['raw_identities'][0].update(year=2024),
            lambda x:x[3]['reference_check'].update(unresolved=1),
            lambda x:x[3]['reference_check'].update(total=1),
            lambda x:x[3]['catalogue_reconciliation'].update(same_scope_extra=1),
            lambda x:x[3].update(official_total=2,official_scope='unsupported official'),
            lambda x:x[2][0]['ai4s_review'].update(decision='pending'),
            lambda x:x[1][0].update(abstract=None)]
        for change in cases:
            x=self.fixture();change(x)
            self.assertTrue(HistoricalAbstractStateTest().render(x)[0]['issues'])
