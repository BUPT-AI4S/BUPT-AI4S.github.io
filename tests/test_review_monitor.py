import json, tempfile, unittest
from copy import deepcopy
from pathlib import Path
from tools.build_review_monitor import build

class OfficialNoAbstractTest(unittest.TestCase):
    def test_verified_exclusion_is_not_actionable_but_raw_missingness_is_retained(self):
        requirement = {'status':'not_required','reason':'official_source_has_no_independent_abstract',
                       'checked_at':'2026-11-13','checked_by':'A','evidence_urls':['https://publisher.example/article']}
        candidate = {'venue':'v','year':2025,'id':'1','abstract':None,'abstract_requirement':requirement}
        review = {'venue':'v','year':2025,'id':'1','ai4s_review':{
            'decision':'exclude','owner':'A','snapshot_at':'current','abstract_requirement':requirement}}
        cases = [('verified', candidate, review, None, 0)]
        for field in ('evidence_urls','reason','checked_at','checked_by'):
            c = deepcopy(candidate); del c['abstract_requirement'][field]
            cases.append((field, c, review, None, 1))
        for links in ([], ['https://['], ['not a URL']):
            c = deepcopy(candidate); c['abstract_requirement']['evidence_urls'] = links
            cases.append(('invalid evidence '+str(links), c, review, None, 1))
        for field, value in [('decision','include'),('snapshot_at','old'),('owner','B')]:
            r = deepcopy(review); r['ai4s_review'][field] = value
            cases.append((field, candidate, r, None, 1))
        r = deepcopy(review); del r['ai4s_review']['abstract_requirement']
        cases.append(('unverified review', candidate, r, None, 1))
        r = deepcopy(review); r['ai4s_review']['decision'] = 'pending'
        cases.append(('conflicting review', candidate, review, r, 1))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d); (p/'metadata/2025').mkdir(parents=True); (p/'reviews/2025/feedback').mkdir(parents=True)
            (p/'metadata/2025/snapshot.json').write_text(json.dumps({'year':2025,'captured_at':'current',
                'sources':[{'source':'v','state':'completed','papers':1}]}), encoding='utf8')
            (p/'reviews/source-assignments-2025.json').write_text(json.dumps({'year':2025,
                'sources':[{'code':'v','owner':'A'}]}), encoding='utf8')
            (p/'reviews/2025/feedback/a.json').write_text(json.dumps({'year':2025,'source_code':'v',
                'snapshot_at':'current','official_total':1,'official_scope':'all types'}), encoding='utf8')
            for name, c, r, extra, expected in cases:
                with self.subTest(name=name):
                    (p/'metadata/2025/ai4s.json').write_text(json.dumps([c]), encoding='utf8')
                    (p/'reviews/2025/a.json').write_text(json.dumps([r]+([extra] if extra else [])), encoding='utf8')
                    s = build(p)['years'][0]['sources'][0]
                    self.assertEqual(s['missing_abstract'], 1)
                    self.assertEqual(s['abstract_supplement_required'], expected)
                    self.assertEqual(s['abstract_not_required'], 1-expected)
                    self.assertEqual(any('AI4S候选缺少摘要' in x for x in s['issues']), bool(expected))
                    if name == 'verified': self.assertEqual(s['issues'], [])

class MonitorTest(unittest.TestCase):
    def test_2024_abstract_gaps_are_not_action_items_but_later_years_are(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d)
            for year in (2024, 2025, 2026):
                md=p/'metadata'/str(year); md.mkdir(parents=True)
                reviews=p/'reviews'/str(year); reviews.mkdir(parents=True)
                (md/'snapshot.json').write_text(json.dumps({'year':year,'captured_at':'current','sources':[{'source':'v','papers':2}]}),encoding='utf8')
                (p/'reviews'/f'source-assignments-{year}.json').write_text(json.dumps({'year':year,'sources':[{'code':'v','owner':'A'}]}),encoding='utf8')
                (md/'ai4s.json').write_text(json.dumps([{'year':year,'venue':'v','id':'existing','abstract':None}]),encoding='utf8')
                (reviews/'a.json').write_text(json.dumps([{'year':year,'venue':'v','id':'extra','abstract':None,'ai4s_review':{'owner':'A','snapshot_at':'current','decision':'include'}}]),encoding='utf8')
            rows={y['year']:y['sources'][0] for y in build(p)['years']}
            self.assertEqual(rows[2024]['unsynced_included'],1)
            self.assertIsNone(rows[2024]['final_missing_abstract'])
            self.assertFalse(any('摘要' in x or '尚未同步候选总集' in x for x in rows[2024]['issues']))
            for year in (2025,2026):
                self.assertEqual(rows[year]['unsynced_included'],1)
                self.assertEqual(rows[year]['unsynced_missing_abstract'],1)
                self.assertEqual(rows[year]['final_missing_abstract'],1)
                self.assertTrue(any('尚未同步候选总集' in x for x in rows[year]['issues']))
                self.assertTrue(any('AI4S候选缺少摘要' in x for x in rows[year]['issues']))
    def test_full_and_final_inclusion_abstract_counts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'now','sources':[{'source':'v','papers':10,'with_abstract':7},{'source':'unknown','papers':3}]}),encoding='utf8')
            (p/'reviews/source-assignments-2024.json').write_text(json.dumps({'year':2024,'sources':[{'code':'v','owner':'A'},{'code':'unknown','owner':'B'}]}),encoding='utf8')
            (p/'metadata/2024/ai4s.json').write_text(json.dumps([{'year':2024,'venue':'v','id':'in','abstract':'complete'}]),encoding='utf8')
            def rec(id, decision='include', abstract=None):
                return {'year':2024,'venue':'v','id':id,'abstract':abstract,'ai4s_review':{'owner':'A','snapshot_at':'now','decision':decision}}
            (p/'reviews/2024/a.json').write_text(json.dumps([rec('in'),rec('missing'),rec('missing'),rec('excluded','exclude'),rec('conflict'),rec('conflict','exclude')]),encoding='utf8')
            rows={s['code']:s for s in build(p)['years'][0]['sources']}
            self.assertEqual(rows['v']['papers_missing_abstract'],3)
            self.assertEqual(rows['v']['final_included'],2)
            self.assertIsNone(rows['v']['final_missing_abstract'])
            self.assertIsNone(rows['unknown']['papers_missing_abstract'])
            self.assertIsNone(rows['unknown']['final_included'])

    def test_reviewed_inclusions_outside_candidate_file_are_visible(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2025').mkdir(parents=True); (p/'reviews/2025').mkdir(parents=True)
            (p/'metadata/2025/snapshot.json').write_text(json.dumps({'year':2025,'captured_at':'current','sources':[{'source':'v','state':'completed','papers':6}]}),encoding='utf8')
            (p/'reviews/source-assignments-2025.json').write_text(json.dumps({'year':2025,'sources':[{'code':'v','owner':'A'}]}),encoding='utf8')
            (p/'metadata/2025/ai4s.json').write_text(json.dumps([{'year':2025,'venue':'v','id':'in','abstract':'full'}]),encoding='utf8')
            def rec(id,decision='include',owner='A',snapshot='current',abstract=None,verified=None):
                return {'year':2025,'venue':'v','id':id,'abstract':abstract,'ai4s_review':{'owner':owner,'snapshot_at':snapshot,'decision':decision,'verified_metadata':{'abstract':verified}}}
            records=[rec('in',abstract='full'),rec('missing'),rec('full',verified='publisher abstract'),rec('excluded',decision='exclude'),rec('other',owner='B'),rec('old',snapshot='old'),rec('missing'),rec('conflict'),rec('conflict',decision='exclude')]
            (p/'reviews/2025/a.json').write_text(json.dumps(records),encoding='utf8')
            s=build(p)['years'][0]['sources'][0]
            self.assertEqual(s.get('unsynced_included'),2)
            self.assertEqual(s.get('unsynced_missing_abstract'),1)
            self.assertEqual(s['missing_abstract'],0)
            self.assertTrue(any('尚未同步候选总集' in issue for issue in s['issues']))
            self.assertTrue(any('补充' in action and '摘要' in action for action in s['actions']))

    def test_reference_check_can_complete_without_claiming_official_total(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024/feedback').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'same','sources':[{'source':'v','state':'completed','papers':10,'ai4s':1}]}),encoding='utf8')
            (p/'reviews/venue-review.csv').write_text('source_code,title,owner,是否建议纳入\nv,Venue,A,建议纳入\n',encoding='utf8')
            (p/'reviews/2024/a.json').write_text(json.dumps([{'venue':'v','year':2024,'id':'1','ai4s_review':{'decision':'include','snapshot_at':'same'}}]),encoding='utf8')
            check={'status':'complete','source':'Crossref','total':10,'scope':'2024 research articles','query_url':'https://api.crossref.org/example','checked_at':'2026-11-15','unresolved':0}
            feedback={'year':2024,'source_code':'v','snapshot_at':'same','reference_check':check,'issues':[],'next_actions':[]}
            path=p/'reviews/2024/feedback/a.json'; path.write_text(json.dumps(feedback),encoding='utf8')
            year=build(p)['years'][0]; row=year['sources'][0]
            self.assertIsNone(row['official_total']); self.assertEqual(row['reference_check'],check)
            self.assertFalse(any('官网同口径总数尚未确认' in i for i in row['issues']))
            self.assertEqual(year['owners'][0]['status'],'complete')
            feedback['snapshot_at']='old'; path.write_text(json.dumps(feedback),encoding='utf8')
            self.assertTrue(any('官网同口径总数尚未确认' in i for i in build(p)['years'][0]['sources'][0]['issues']))

    def test_incomplete_reference_check_does_not_clear_action(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024/feedback').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'same','sources':[{'source':'v','state':'completed','papers':10,'ai4s':0}]}),encoding='utf8')
            check={'status':'complete','source':'Crossref','total':10,'scope':'2024 research articles','query_url':'https://api.crossref.org/example','checked_at':'2026-11-15','unresolved':1}
            (p/'reviews/2024/feedback/a.json').write_text(json.dumps({'year':2024,'source_code':'v','snapshot_at':'same','reference_check':check}),encoding='utf8')
            row=build(p)['years'][0]['sources'][0]
            self.assertTrue(any('官网同口径总数尚未确认' in i for i in row['issues']))

    def test_snapshot_review_and_feedback_keep_unknown_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'2026-01-01','sources':[{'source':'v','state':'completed','papers':10,'with_abstract':7,'ai4s':2}]}), encoding='utf8')
            (p/'metadata/2024/ai4s.json').write_text(json.dumps([{'venue':'v','year':2024,'id':str(i),'abstract':None} for i in range(3)]),encoding='utf8')
            (p/'reviews/venue-review.csv').write_text('source_code,title,owner,是否建议纳入\nv,Venue,A,建议纳入\n',encoding='utf8')
            (p/'reviews/2024/a.json').write_text(json.dumps([{'venue':'v','year':2024,'id':'1','ai4s_review':{'owner':'A','decision':'include'}},{'venue':'v','year':2024,'id':'2','ai4s_review':{'owner':'A','decision':'pending'}}]),encoding='utf8')
            x=build(p); v=x['years'][0]['sources'][0]
            self.assertEqual(v['missing_abstract'],3); self.assertEqual(v['decisions']['include'],1); self.assertEqual(v['decisions']['pending'],1)
            self.assertIsNone(v['official_total']); self.assertTrue(any('官网' in i for i in v['issues']))
            self.assertEqual(v['owner'],'A')

    def test_feedback_requires_same_snapshot_for_count_comparison(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024/feedback').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'new','sources':[{'source':'v','state':'completed','papers':10,'with_abstract':10,'ai4s':0}]}),encoding='utf8')
            (p/'reviews/2024/feedback/a.json').write_text(json.dumps({'year':2024,'source_code':'v','snapshot_at':'old','official_total':11,'official_scope':'research','issues':['problem'],'next_actions':['check']}),encoding='utf8')
            v=build(p)['years'][0]['sources'][0]
            self.assertIsNone(v['official_total']); self.assertTrue(any('快照' in i for i in v['issues']))

if __name__ == '__main__': unittest.main()

class ReviewConflictTest(unittest.TestCase):
    def test_mixed_snapshots_and_duplicate_conflicts_are_visible(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'current','sources':[{'source':'v','state':'completed','papers':2,'with_abstract':2,'ai4s':1}]}),encoding='utf8')
            for name,decision in [('a','include'),('b','exclude')]:
                (p/f'reviews/2024/{name}.json').write_text(json.dumps([{'venue':'v','year':2024,'id':'1','ai4s_review':{'decision':decision,'snapshot_at':'old'}}]),encoding='utf8')
            s=build(p)['years'][0]['sources'][0]
            self.assertTrue(any('快照' in x for x in s['issues']))
            self.assertTrue(any('冲突' in x for x in s['issues']))

class ReportedCoverageTest(unittest.TestCase):
    def test_existing_coverage_total_is_attributed_and_snapshot_matched(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024/a').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'same','sources':[{'source':'v','papers':3,'with_abstract':3,'ai4s':0}]}),encoding='utf8')
            (p/'reviews/2024/a/coverage.json').write_text(json.dumps({'snapshot':{'snapshot_at':'same'},'sources':[{'source_code':'v','official_total':4,'coverage_rationale':'official 2024 directory','evidence_urls':['https://example.org/']}]}),encoding='utf8')
            s=build(p)['years'][0]['sources'][0]
            self.assertEqual(s['official_total'],4)
            self.assertIn('official 2024 directory',s['official_scope'])

class YearAssignmentTest(unittest.TestCase):
    def test_prior_year_assignments_do_not_imply_new_year_ownership(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2026').mkdir(parents=True); (p/'reviews').mkdir()
            (p/'metadata/2026/snapshot.json').write_text(json.dumps({'year':2026,'sources':[{'source':'v','papers':1,'with_abstract':1,'ai4s':0}]}),encoding='utf8')
            (p/'reviews/venue-review.csv').write_text('source_code,title,owner,是否建议纳入\nv,Venue,A,建议纳入\n',encoding='utf8')
            s=build(p)['years'][0]['sources'][0]
            self.assertEqual(s['owner'],''); self.assertEqual(s['venue_decision'],'')

class ActionFilesTest(unittest.TestCase):
    def test_owner_actions_contain_only_assigned_sources_and_source_commit(self):
        from tools.generate_review_actions import write_actions
        with tempfile.TemporaryDirectory() as d:
            data={'repository':'https://example.test/abc/','commit':'abc','years':[{'year':2024,'captured_at':'stamp','sources':[{'code':'v','title':'Venue','owner':'A','issues':['gap'],'actions':['check'],'files':['reviews/a.json']},{'code':'z','title':'Other','owner':'B','issues':['other'],'actions':['other action'],'files':[]}]}]}
            out=Path(d); write_actions(data,out)
            text=(out/'2024/actions/A.md').read_text(encoding='utf8')
            self.assertIn('Venue',text); self.assertIn('gap',text); self.assertIn('abc',text); self.assertNotIn('Other',text)

class CurrentScopeAndCandidateTest(unittest.TestCase):
    def test_current_scope_overrides_old_assignment_and_counts_candidate_abstracts(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews').mkdir()
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'x','sources':[{'source':'v','state':'completed','papers':100,'with_abstract':10,'ai4s':3},{'source':'removed','state':'completed','papers':7,'with_abstract':0,'ai4s':0}]}),encoding='utf8')
            (p/'reviews/venue-review.csv').write_text('source_code,title,owner,是否建议纳入\nv,Venue,Old,不建议纳入\n',encoding='utf8')
            (p/'reviews/source-assignments-2024.json').write_text(json.dumps({'year':2024,'sources':[{'code':'v','title':'Venue','owner':'New'}]}),encoding='utf8')
            (p/'metadata/2024/ai4s.json').write_text(json.dumps([{'venue':'v','year':2024,'id':'1','abstract':'abc'},{'venue':'v','year':2024,'id':'2','abstract':None},{'venue':'v','year':2024,'id':'3','abstract':'  '}]),encoding='utf8')
            rows=build(p)['years'][0]['sources']; self.assertEqual(len(rows),1)
            self.assertEqual(rows[0]['owner'],'New'); self.assertEqual(rows[0]['missing_abstract'],2); self.assertEqual(rows[0]['candidates'],3)
    def test_missing_candidate_file_yields_unknown_abstract_count(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'sources':[{'source':'v','papers':100,'with_abstract':10,'ai4s':3}]}),encoding='utf8')
            self.assertIsNone(build(p)['years'][0]['sources'][0]['missing_abstract'])

class CandidateOnlyYearTest(unittest.TestCase):
    def test_discovers_year_without_snapshot_and_preserves_unknown_totals(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2025').mkdir(parents=True)
            (p/'metadata/2025/ai4s.json').write_text(json.dumps([{'venue':'cvpr','year':2025,'id':'x','abstract':'study'},{'venue':'cvpr','year':2025,'id':'y','abstract':None}]),encoding='utf8')
            year=build(p)['years'][0]; self.assertEqual(year['year'],2025)
            self.assertIsNone(year['captured_at']); self.assertIsNone(year['snapshot_file'])
            self.assertEqual(len(year['sources']),1); row=year['sources'][0]
            self.assertEqual(row['candidates'],2); self.assertEqual(row['missing_abstract'],1)
            self.assertIsNone(row['papers']); self.assertEqual(row['owner'],'')
            self.assertTrue(any('快照' in x for x in row['issues']))

class CandidateYearFeedbackTest(unittest.TestCase):
    def test_unavailable_snapshot_does_not_validate_feedback_totals(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2025').mkdir(parents=True); (p/'reviews/2025/feedback').mkdir(parents=True)
            (p/'metadata/2025/ai4s.json').write_text(json.dumps([{'venue':'v','year':2025,'id':'x','abstract':'a'}]),encoding='utf8')
            (p/'reviews/2025/feedback/a.json').write_text(json.dumps({'year':2025,'source_code':'v','snapshot_at':None,'official_total':1,'official_scope':'official','issues':['实际问题'],'next_actions':['实际行动']}),encoding='utf8')
            row=build(p)['years'][0]['sources'][0]
            self.assertIsNone(row['official_total']); self.assertIn('实际问题',row['issues']); self.assertIn('实际行动',row['actions'])
            self.assertTrue(any('快照' in x for x in row['issues']))

class CandidateOnlyAssignedYearTest(unittest.TestCase):
    def test_assignments_keep_zero_candidate_sources_without_inventing_totals(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2025').mkdir(parents=True); (p/'reviews').mkdir()
            (p/'metadata/2025/ai4s.json').write_text(json.dumps([{'venue':'v','year':2025,'id':'x','abstract':'a'}]),encoding='utf8')
            (p/'reviews/source-assignments-2025.json').write_text(json.dumps({'year':2025,'sources':[{'code':'v','owner':'A','title':'Venue'},{'code':'w','owner':'B','title':'Other'}]}),encoding='utf8')
            rows={r['code']:r for r in build(p)['years'][0]['sources']}
            self.assertEqual(set(rows),{'v','w'}); self.assertEqual(rows['w']['candidates'],0)
            self.assertEqual(rows['w']['owner'],'B'); self.assertIsNone(rows['w']['papers'])

class ConferenceCrawlFeedbackTest(unittest.TestCase):
    def test_conference_blocking_reasons_and_next_actions_are_visible(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024/reviewer').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'sources':[{'source':'sigmod','state':'completed','papers':10,'ai4s':0}]}),encoding='utf8')
            (p/'reviews/2024/reviewer/conference-crawl-check.csv').write_text('source_code,directory_status,blocking_reason,next_action,official_urls\nsigmod,尚未对齐,论文集访问受限,核对 ACM 目录,https://example.org\n',encoding='utf8')
            row=build(p)['years'][0]['sources'][0]
            self.assertIn('论文集访问受限',row['issues']); self.assertIn('核对 ACM 目录',row['actions'])
            self.assertIn('reviews/2024/reviewer/conference-crawl-check.csv',row['files'])
            self.assertIn('https://example.org',row['evidence_urls'])


class HistoricalAbstractStateTest(unittest.TestCase):
    def fixture(self):
        return [
            {'year':2025,'captured_at':'current','sources':[
                {'source':'v','state':'abstract_incomplete','papers':2,'with_abstract':1},
                {'source':'untouched','state':'abstract_incomplete','papers':2}]},
            [{'year':2025,'venue':'v','id':'one','abstract':'Original abstract'}],
            [{'year':2025,'venue':'v','id':'one','ai4s_review':{
                'owner':'A','snapshot_at':'current','decision':'include'}}],
            {'year':2025,'source_code':'v','owner':'A','github_username':'a',
             'snapshot_at':'current','official_total':2,'official_scope':'all formal issues',
             'catalogue_reconciliation':{'current_raw_count':2,'same_scope_missing':0,
                'same_scope_extra':0,'same_scope_duplicate':0},
             'collection_state_resolution':{'status':'resolved_for_candidate_review',
                'original_state':'abstract_incomplete',
                'reason':'full_catalogue_abstract_gap_candidates_complete',
                'checked_at':'2026-11-15','checked_by':'A',
                'evidence_urls':['https://publisher.example/toc']}}]

    def render(self, fixture, filename='a'):
        snapshot, candidates, reviews, feedback = fixture
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2025').mkdir(parents=True)
            (p/'reviews/2025/feedback').mkdir(parents=True)
            docs={'metadata/2025/snapshot.json':snapshot, 'metadata/2025/ai4s.json':candidates,
                'reviews/source-assignments-2025.json':{'year':2025,'sources':[
                    {'code':'v','owner':'A'},{'code':'untouched','owner':'A'}]},
                'reviews/2025/a.json':reviews, f'reviews/2025/feedback/{filename}.json':feedback}
            for path,obj in docs.items(): (p/path).write_text(json.dumps(obj),encoding='utf8')
            return build(p)['years'][0]['sources']

    def test_audited_source_closes_and_snapshot_state_is_retained(self):
        source, untouched=self.render(self.fixture())
        self.assertEqual(source['issues'],[])
        self.assertEqual(source['state'],'abstract_incomplete')
        self.assertIn('collection_state_resolution',source)
        self.assertIn('采集状态尚未完成：abstract_incomplete',untouched['issues'])
        self.assertNotIn('collection_state_resolution',untouched)

    def test_invalid_audits_retain_state_issue(self):
        cases=[
            ('no resolution',lambda s,c,r,f:f.pop('collection_state_resolution')),
            ('failed state',lambda s,c,r,f:s['sources'][0].update(state='failed')),
            ('missing abstract',lambda s,c,r,f:c[0].update(abstract=None)),
            ('missing review',lambda s,c,r,f:r[0].update(id='different')),
            ('pending',lambda s,c,r,f:r[0]['ai4s_review'].update(decision='pending')),
            ('wrong reviewer',lambda s,c,r,f:r[0]['ai4s_review'].update(owner='B')),
            ('old review',lambda s,c,r,f:r[0]['ai4s_review'].update(snapshot_at='old')),
            ('old feedback',lambda s,c,r,f:f.update(snapshot_at='old')),
            ('wrong owner',lambda s,c,r,f:f.update(owner='B')),
            ('different total',lambda s,c,r,f:f.update(official_total=3)),
            ('catalogue gap',lambda s,c,r,f:f['catalogue_reconciliation'].update(same_scope_missing=1)),
            ('no reconciliation',lambda s,c,r,f:f.pop('catalogue_reconciliation')),
            ('blocker',lambda s,c,r,f:f.update(issues=['unresolved evidence'])),
            ('no evidence',lambda s,c,r,f:f['collection_state_resolution'].update(evidence_urls=[])),
            ('bad URL',lambda s,c,r,f:f['collection_state_resolution'].update(evidence_urls=['https://['])),
            ('duplicate candidate',lambda s,c,r,f:c.append(deepcopy(c[0]))),
            ('conflicting review',lambda s,c,r,f:r.append(dict(deepcopy(r[0]),ai4s_review={
                'owner':'A','snapshot_at':'current','decision':'exclude'}))),
        ]
        for name,change in cases:
            with self.subTest(name=name):
                fixture=self.fixture(); change(*fixture); source=self.render(fixture)[0]
                self.assertNotIn('collection_state_resolution',source)
                self.assertTrue(any(x.startswith('采集状态尚未完成：') for x in source['issues']))
        self.assertNotIn('collection_state_resolution',self.render(self.fixture(),'other')[0])

class CurrentReviewScopeTest(unittest.TestCase):
    def fixture(self):
        import hashlib
        audit = 'metadata/2024/owner-scope.json'
        scope = {'status':'current_candidates_and_verified_additions',
                 'review_file':'reviews/2024/a.json','checked_by':'A','checked_at':'2026-11-16',
                 'candidate_file':'metadata/2024/ai4s.json','candidate_count':1,
                 'candidate_ids_sha256':hashlib.sha256(b'["one"]').hexdigest(),
                 'scope_instruction':'Review current candidates; keep unverified catalogue entries separate.',
                 'audit_file':audit}
        ref = {'status':'reference_only','reason':'unverified_catalogue_record_outside_current_candidates',
               'checked_by':'A','checked_at':'2026-11-16','audit_file':audit}
        return {
            'metadata/2024/snapshot.json':{'year':2024,'captured_at':'current','sources':[
                {'source':'v','state':'completed','papers':3},{'source':'w','state':'completed','papers':1}]},
            'metadata/2024/ai4s.json':[{'venue':'v','year':2024,'id':'one','abstract':'Original abstract'}],
            'reviews/source-assignments-2024.json':{'year':2024,'sources':[
                {'code':'v','owner':'A'},{'code':'w','owner':'B'}]},
            'reviews/2024/a.json':[
                {'venue':'v','year':2024,'id':'one','ai4s_review':{'owner':'A','snapshot_at':'current','decision':'include'}},
                {'venue':'v','year':2024,'id':'reference','ai4s_review':{'owner':'A','snapshot_at':'current',
                    'decision':'pending','review_scope':ref}}],
            'reviews/2024/b.json':[
                {'venue':'v','year':2024,'id':'one','ai4s_review':{'owner':'B','snapshot_at':'current','decision':'exclude'}},
                {'venue':'v','year':2024,'id':'legacy','ai4s_review':{'owner':'B','snapshot_at':'current','decision':'pending'}},
                {'venue':'w','year':2024,'id':'other-owner','ai4s_review':{'owner':'B','snapshot_at':'current','decision':'pending'}}],
            'reviews/2024/feedback/a.json':{'year':2024,'source_code':'v','owner':'A','snapshot_at':'current',
                'official_total':3,'official_scope':'all formal types','review_scope':scope},
            'reviews/2024/feedback/b.json':{'year':2024,'source_code':'v','owner':'B','snapshot_at':'current',
                'issues':['Historical owner backlog'],'next_actions':['Recheck historical owner records.']}}

    def render(self, docs):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            for path,value in docs.items():
                dest=root/path;dest.parent.mkdir(parents=True,exist_ok=True)
                dest.write_text(json.dumps(value),encoding='utf8')
            return {s['code']:s for s in build(root)['years'][0]['sources']}

    def test_explicit_scope_preserves_references_and_history_without_changing_other_owners(self):
        rows=self.render(self.fixture());v=rows['v'];w=rows['w']
        self.assertEqual(v['decisions'],{'include':1,'exclude':0,'pending':0,'unreviewed':0})
        self.assertEqual(v['catalogue_reference_records'],1)
        self.assertEqual(v['issues'],[])
        self.assertEqual(set(v['historical_review_files']),{'reviews/2024/b.json','reviews/2024/feedback/b.json'})
        self.assertEqual(w['decisions']['pending'],1)
        self.assertTrue(w['issues'])

    def test_incomplete_stale_foreign_and_invalid_scopes_cannot_close_tasks(self):
        cases=[
            ('no scope',lambda d:d['reviews/2024/feedback/a.json'].pop('review_scope')),
            ('wrong candidate digest',lambda d:d['reviews/2024/feedback/a.json']['review_scope'].update(candidate_ids_sha256='bad')),
            ('wrong count',lambda d:d['reviews/2024/feedback/a.json']['review_scope'].update(candidate_count=0)),
            ('wrong owner',lambda d:d['reviews/2024/feedback/a.json']['review_scope'].update(checked_by='B')),
            ('stale feedback',lambda d:d['reviews/2024/feedback/a.json'].update(snapshot_at='old')),
            ('foreign review file',lambda d:d['reviews/2024/feedback/a.json']['review_scope'].update(review_file='reviews/2024/b.json')),
            ('outside file',lambda d:d['reviews/2024/feedback/a.json']['review_scope'].update(review_file='../outside.json')),
            ('missing candidate',lambda d:d['reviews/2024/a.json'].pop(0)),
            ('duplicate candidate',lambda d:d['metadata/2024/ai4s.json'].append(deepcopy(d['metadata/2024/ai4s.json'][0]))),
        ]
        for name,mutate in cases:
            with self.subTest(name=name):
                docs=self.fixture();mutate(docs);v=self.render(docs)['v']
                self.assertNotIn('active_review_file',v)
                self.assertTrue(v['issues'])

    def test_actual_candidate_pending_cannot_be_hidden_as_reference(self):
        import hashlib
        docs=self.fixture();docs['metadata/2024/ai4s.json'].append({'venue':'v','year':2024,'id':'reference','abstract':'Original'})
        docs['reviews/2024/feedback/a.json']['review_scope'].update(candidate_count=2,
            candidate_ids_sha256=hashlib.sha256(b'["one","reference"]').hexdigest())
        v=self.render(docs)['v']
        self.assertEqual(v['decisions']['pending'],1)
        self.assertEqual(v['catalogue_reference_records'],0)
        self.assertTrue(v['issues'])

    def test_unmarked_or_unauthorized_supplement_remains_pending(self):
        for change in ('unmarked','wrong owner'):
            docs=self.fixture();review=docs['reviews/2024/a.json'][1]['ai4s_review']
            if change=='unmarked':review.pop('review_scope')
            else:review['review_scope']['checked_by']='B'
            v=self.render(docs)['v']
            self.assertEqual(v['decisions']['pending'],1)
            self.assertEqual(v['catalogue_reference_records'],0)
            self.assertTrue(v['issues'])
