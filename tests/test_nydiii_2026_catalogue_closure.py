"""The explicitly authorized 2026 owner audit closes history, never live gaps."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

from tools.build_review_monitor import build, verified_audited_catalogue


class NydiiiAuditedCatalogueTest(unittest.TestCase):
    def fixture(self, root, year=2026, owner='南耀笛', official=True, excluded=False):
        raw = [{'id':'raw','title':'Original','venue':'v','year':year}]
        if excluded:
            raw.append({'id':'later','title':'Next year','venue':'v','year':year})
        extra = {'id':'added','title':'Added research','venue':'v','year':year,
                 'url':'https://publisher.example/added','published':f'{year}-10-01',
                 'checked_at':'2026-11-17','checked_by':owner,
                 'evidence_urls':['https://publisher.example/added']}
        canonical = [{'id':'raw','title':'Original','url':'https://publisher.example/raw'},
                     {'id':'added','title':'Added research','url':extra['url']}]
        check = {'status':'complete','source':'Crossref','total':2,'scope':'published year cohort',
                 'query_url':'https://api.crossref.org/works','checked_at':'2026-11-17','unresolved':0}
        report = {'source_code':'v','year':year,'owner':owner,'snapshot_at':'same',
                  'official_total':2 if official else None,
                  'reference_check':None if official else check,'normalized_count':2,
                  'canonical_records':canonical,'scope_exclusions':[], 'missing':['added'],
                  'extra':[],'duplicates':0,'unresolved':[],
                  'scope':'formal issue cohort' if official else check['scope']}
        if excluded:
            report['scope_exclusions']=[{'id':'later','title':'Next year',
                'status':'different_formal_year','verified_year':year+1,'verified_volume':'next',
                'checked_at':'2026-11-17','checked_by':owner,
                'evidence_urls':['https://publisher.example/later']}]
        row = {'year':year,'source_code':'v','owner':owner,'github_username':'nydiii','snapshot_at':'same',
               'official_total':report['official_total'],'official_scope':'formal issue cohort' if official else '',
               'issues':[],'reference_check':report['reference_check'],
               'catalogue_reconciliation':{'current_raw_count':len(raw),'normalized_count':2,
                 'same_scope_missing':1,'same_scope_extra':0,'same_scope_duplicate':0,
                 'canonical_unresolved_missing':0},
               'catalogue_audit':{'source_code':'v','year':year,'owner':owner,'snapshot_at':'same',
                 'input_main_commit':'a'*40,'raw_sha256':'b'*64,
                 'details_file':f'metadata/v/{year}/catalogue-reconciliation.json',
                 'raw_identities':raw,'additions':[extra],'report':report},
               'collection_state_resolution':{'status':'resolved_for_candidate_review',
                 'original_state':'abstract_incomplete','reason':'full_audited_catalogue_candidates_complete',
                 'checked_by':owner,'checked_at':'2026-11-17',
                 'evidence_urls':['https://publisher.example/contents']}}
        paths = {f'metadata/{year}/snapshot.json':{'year':year,'captured_at':'same',
                   'sources':[{'source':'v','state':'abstract_incomplete','papers':len(raw),'ai4s':1}]},
                 f'reviews/source-assignments-{year}.json':{'year':year,'sources':[{'code':'v','owner':owner}]},
                 f'metadata/{year}/ai4s.json':[{'id':'raw','venue':'v','year':year,'abstract':'Original scientific abstract.'}],
                 f'reviews/{year}/nydiii.json':[{'id':'raw','venue':'v','year':year,'ai4s_review':{
                   'decision':'include','owner':owner,'snapshot_at':'same'}}],
                 f'reviews/{year}/feedback/nydiii.json':[row]}
        for name,value in paths.items():
            p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(value))
        return row

    def source(self, root):
        return build(root)['years'][0]['sources'][0]

    def test_official_and_reference_additions_with_scope_differences(self):
        for official in (True, False):
            for excluded in (True, False):
                with self.subTest(official=official,excluded=excluded), tempfile.TemporaryDirectory() as d:
                    p=Path(d);self.fixture(p,official=official,excluded=excluded);s=self.source(p)
                    self.assertEqual(s['issues'],[])
                    self.assertEqual(s['state'],'abstract_incomplete')
                    self.assertEqual(s['papers'],2 if excluded else 1)
                    self.assertEqual(s['official_total'],2 if official else None)

    def test_other_owners_and_years_are_not_enabled(self):
        for year,owner in [(2026,'陈晨'),(2025,'南耀笛'),(2024,'南耀笛')]:
            with self.subTest(year=year,owner=owner),tempfile.TemporaryDirectory() as d:
                p=Path(d);self.fixture(p,year=year,owner=owner)
                self.assertTrue(any('采集状态尚未完成' in i for i in self.source(p)['issues']))

    def test_pending_missing_abstract_and_conflicting_review_still_warn(self):
        for case in ('pending','abstract','conflict'):
            with self.subTest(case=case),tempfile.TemporaryDirectory() as d:
                p=Path(d);self.fixture(p)
                rp=p/'reviews/2026/nydiii.json';cp=p/'metadata/2026/ai4s.json'
                reviews=json.loads(rp.read_text())
                if case=='pending':reviews[0]['ai4s_review']['decision']='pending'
                elif case=='conflict':
                    other=deepcopy(reviews[0]);other['ai4s_review']['decision']='exclude';reviews.append(other)
                else:
                    candidates=json.loads(cp.read_text());candidates[0]['abstract']=None;cp.write_text(json.dumps(candidates))
                rp.write_text(json.dumps(reviews));s=self.source(p)
                self.assertTrue(s['issues'])
                self.assertFalse(s.get('collection_state_resolution'))

    def test_incomplete_or_wrong_identity_proofs_fail_closed(self):
        mutations=[lambda a:a.update(owner='陈晨'),lambda a:a.update(snapshot_at='old'),
                   lambda a:a['report']['canonical_records'].pop(),
                   lambda a:a['report']['canonical_records'].append(a['report']['canonical_records'][0]),
                   lambda a:a['report'].update(unresolved=['unknown']),
                   lambda a:a['report'].update(normalized_count=3),
                   lambda a:a['report'].update(missing=[{}]),
                   lambda a:a['additions'][0].update(evidence_urls=[]),
                   lambda a:a['additions'][0].update(title='different paper'),
                   lambda a:a['report']['scope_exclusions'][0].update(verified_year=2026),
                   lambda a:a['report']['scope_exclusions'][0].update(evidence_urls=[]),
                   lambda a:a['report']['scope_exclusions'][0].update(status='ignore')]
        with tempfile.TemporaryDirectory() as d:
            p=Path(d);row=self.fixture(p,excluded=True);s=self.source(p)
            for i,mutate in enumerate(mutations):
                with self.subTest(case=i):
                    bad=deepcopy(row);mutate(bad['catalogue_audit'])
                    self.assertFalse(verified_audited_catalogue(p,2026,s,bad))
