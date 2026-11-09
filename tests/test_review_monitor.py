import json, tempfile, unittest
from pathlib import Path
from tools.build_review_monitor import build

class MonitorTest(unittest.TestCase):
    def test_snapshot_review_and_feedback_keep_unknown_distinct(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d); (p/'metadata/2024').mkdir(parents=True); (p/'reviews/2024').mkdir(parents=True)
            (p/'metadata/2024/snapshot.json').write_text(json.dumps({'year':2024,'captured_at':'2026-01-01','sources':[{'source':'v','state':'completed','papers':10,'with_abstract':7,'ai4s':2}]}), encoding='utf8')
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
