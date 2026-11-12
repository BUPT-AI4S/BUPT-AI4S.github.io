import json, tempfile, unittest
from pathlib import Path
from tools.build_review_monitor import build

class MonitorTest(unittest.TestCase):
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


class VerifiedAbstractTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.write('metadata/2024/snapshot.json', {
            'year': 2024, 'captured_at': 'current',
            'sources': [{'source': 'v', 'state': 'completed', 'papers': 20, 'ai4s': 9}],
        })

    def write(self, path, value):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(value), encoding='utf8')

    def candidate(self, id='1', abstract=None):
        return {'venue': 'v', 'year': 2024, 'id': id, 'abstract': abstract}

    def review(self, id='1', abstract='Original scientific abstract.'):
        return {'venue': 'v', 'year': 2024, 'id': id, 'ai4s_review': {
            'decision': 'include', 'snapshot_at': 'current',
            'verified_metadata': {'abstract': abstract, 'evidence_urls': ['https://example.org/paper']},
            'abstract_verification': {'status': 'verified_original_abstract'},
        }}

    def source(self):
        return build(self.root)['years'][0]['sources'][0]

    def test_nine_verified_abstracts_remove_only_the_automatic_missing_task(self):
        candidates = [self.candidate(str(i)) for i in range(9)]
        reviews = [self.review(str(i), f'Original abstract {i}.') for i in range(9)]
        for i, record in enumerate(reviews):
            record['ai4s_review']['decision'] = ('include', 'exclude', 'pending')[i % 3]
        self.write('metadata/2024/ai4s.json', candidates)
        self.write('reviews/2024/a.json', reviews)
        self.write('reviews/2024/feedback/a.json', {
            'year': 2024, 'source_code': 'v', 'snapshot_at': 'current',
            'issues': ['Separate scientific question'], 'next_actions': ['Check that question'],
        })
        source = self.source()
        self.assertEqual((source['missing_abstract'], source['backfilled_abstract'], source['remaining_missing_abstract']), (9, 9, 0))
        self.assertFalse(any('缺少摘要' in text for text in source['issues']))
        self.assertFalse(any('为缺摘要' in text for text in source['actions']))
        self.assertIn('Separate scientific question', source['issues'])
        self.assertIn('Check that question', source['actions'])
        self.assertEqual(source['decisions'], {'include': 3, 'exclude': 3, 'pending': 3, 'unreviewed': 0})
        self.assertEqual(json.loads((self.root / 'metadata/2024/ai4s.json').read_text()), candidates)
        self.assertEqual(json.loads((self.root / 'reviews/2024/a.json').read_text()), reviews)

    def test_legacy_verified_metadata_counts_without_new_status_field(self):
        record = self.review()
        del record['ai4s_review']['abstract_verification']
        self.write('metadata/2024/ai4s.json', [self.candidate()])
        self.write('reviews/2024/a.json', [record])
        self.assertEqual(self.source()['backfilled_abstract'], 1)

    def test_empty_text_nonoriginal_status_and_nonpublic_evidence_do_not_count(self):
        variants = []
        for value in [None, '', '  ', {'summary': 'AI-generated summary'}]:
            record = self.review(abstract=value); variants.append(('abstract ' + repr(value), record))
        for status in ['not_provided_by_official_source', 'access_restricted_original_text', 'not_retrieved', 'summary', None]:
            record = self.review(); record['ai4s_review']['abstract_verification']['status'] = status
            variants.append(('status ' + repr(status), record))
        for urls in [[], None, [''], ['file:///tmp/paper.txt'], ['/paper'], ['https://'], ['http://localhost/paper'], ['http://127.0.0.1/paper'], ['http://192.168.1.1/paper']]:
            record = self.review(); record['ai4s_review']['verified_metadata']['evidence_urls'] = urls
            variants.append(('evidence ' + repr(urls), record))
        record = self.review(abstract=None)
        record['ai4s_review']['verified_metadata']['summary'] = 'Reviewed from a summary.'
        record['ai4s_review']['rationale'] = 'Abstract was completed.'
        variants.append(('summary and prose only', record))
        self.write('metadata/2024/ai4s.json', [self.candidate()])
        for name, record in variants:
            with self.subTest(name=name):
                self.write('reviews/2024/a.json', [record])
                source = self.source()
                self.assertEqual(source['backfilled_abstract'], 0)
                self.assertEqual(source['remaining_missing_abstract'], 1)

    def test_only_exact_candidate_identity_and_same_nonempty_snapshot_count(self):
        variants = []
        for field, value in [('venue', 'other'), ('year', 2023), ('id', 'supplement')]:
            record = self.review(); record[field] = value; variants.append(record)
        for stamp in ['old', None, '']:
            record = self.review(); record['ai4s_review']['snapshot_at'] = stamp; variants.append(record)
        self.write('metadata/2024/ai4s.json', [self.candidate()])
        self.write('reviews/2024/a.json', variants)
        self.assertEqual(self.source()['backfilled_abstract'], 0)
        for stamp in [None, '', '   ']:
            with self.subTest(snapshot=stamp):
                self.write('metadata/2024/snapshot.json', {'year': 2024, 'captured_at': stamp, 'sources': [{'source': 'v'}]})
                record = self.review(); record['ai4s_review']['snapshot_at'] = stamp
                self.write('reviews/2024/a.json', [record])
                self.assertEqual(self.source()['backfilled_abstract'], 0)

    def test_duplicate_review_copies_count_once_and_ignore_unverified_conflicts(self):
        self.write('metadata/2024/ai4s.json', [self.candidate()])
        self.write('reviews/2024/a.json', [self.review()])
        duplicate = self.review(abstract='  Original\nscientific   abstract. ')
        rejected = self.review(abstract='A different unverified text.')
        rejected['ai4s_review']['abstract_verification']['status'] = 'not_retrieved'
        self.write('reviews/2024/b.json', [duplicate, rejected])
        source = self.source()
        self.assertEqual(source['backfilled_abstract'], 1)
        self.assertEqual(source['remaining_missing_abstract'], 0)
        self.assertFalse(any('摘要' in text and '冲突' in text for text in source['issues']))

    def test_conflicting_verified_texts_remain_missing_with_one_warning(self):
        self.write('metadata/2024/ai4s.json', [self.candidate()])
        self.write('reviews/2024/a.json', [self.review()])
        self.write('reviews/2024/b.json', [self.review(abstract='A different original abstract.'), self.review()])
        source = self.source()
        self.assertEqual((source['backfilled_abstract'], source['remaining_missing_abstract']), (0, 1))
        self.assertEqual(sum('摘要' in text and '冲突' in text for text in source['issues']), 1)
        self.assertTrue(any('摘要' in text for text in source['actions']))

    def test_later_duplicate_with_valid_abstract_keeps_its_evidence_file_link(self):
        self.write('metadata/2024/ai4s.json', [self.candidate()])
        self.write('reviews/2024/a.json', [self.review(abstract=None)])
        self.write('reviews/2024/b.json', [self.review()])
        source = self.source()
        self.assertEqual((source['backfilled_abstract'], source['remaining_missing_abstract']), (1, 0))
        self.assertEqual(source['decisions']['include'], 1)
        self.assertIn('reviews/2024/a.json', source['files'])
        self.assertEqual(source['files'].count('reviews/2024/b.json'), 1)

    def test_candidate_duplicates_keep_record_count_and_existing_abstracts_get_no_credit(self):
        self.write('metadata/2024/ai4s.json', [self.candidate(), self.candidate(), self.candidate(abstract='Already present'), self.candidate('2'), self.candidate(None)])
        self.write('reviews/2024/a.json', [self.review(), self.review()])
        source = self.source()
        self.assertEqual(source['candidates'], 5)
        self.assertEqual((source['missing_abstract'], source['backfilled_abstract'], source['remaining_missing_abstract']), (4, 2, 2))
        self.assertTrue(any('2 篇' in text and '缺少摘要' in text for text in source['issues']))
        self.write('metadata/2024/ai4s.json', [self.candidate(abstract='Already present')])
        source = self.source()
        self.assertEqual((source['missing_abstract'], source['backfilled_abstract'], source['remaining_missing_abstract']), (0, 0, 0))

    def test_missing_candidate_file_keeps_all_abstract_counts_unknown(self):
        self.write('reviews/2024/a.json', [self.review()])
        source = self.source()
        for field in ['missing_abstract', 'backfilled_abstract', 'remaining_missing_abstract']:
            self.assertIsNone(source[field])
