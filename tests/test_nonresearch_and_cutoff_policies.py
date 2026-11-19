"""Explicit evidence closes only its named action; live scientific gaps stay open."""
import json
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import test_review_monitor as abstract_fixtures
import test_nydiii_2026_catalogue_closure as catalogue_fixtures
from tools.build_review_monitor import (verified_audited_catalogue,
                                       verified_nonresearch_abstract_exclusion)


class NonresearchAbstractExclusionTest(unittest.TestCase):
    def fixture(self, kind='Editorial'):
        f = abstract_fixtures.HistoricalAbstractStateTest().fixture()
        proof = {'status':'not_required', 'reason':'verified_nonresearch_document_type_exclusion',
                 'verification_basis':'publisher_or_primary_index_document_type',
                 'paper_id':'one', 'source_code':'v', 'year':2025, 'document_type':kind,
                 'checked_by':'A', 'checked_at':'2026-11-17T07:14:20Z',
                 'primary_source_url':'https://publisher.example/article',
                 'evidence_urls':['https://publisher.example/article']}
        f[1][0].update(abstract=None, abstract_requirement=deepcopy(proof))
        f[2][0]['ai4s_review'].update(decision='exclude', abstract_requirement=deepcopy(proof),
            verified_metadata={'article_type':kind, 'evidence_urls':proof['evidence_urls']})
        return f

    def render(self, f):
        return abstract_fixtures.HistoricalAbstractStateTest().render(f)[0]

    def test_explicit_document_types_close_action_while_nulls_remain(self):
        for kind in ('Editorial','Conference abstract','Erratum','Corrigendum','Correction'):
            with self.subTest(kind=kind):
                f=self.fixture(kind);before=deepcopy(f);s=self.render(f)
                self.assertEqual(f,before)
                self.assertEqual(s['missing_abstract'],1)
                self.assertEqual(s['abstract_nonresearch_excluded'],1)
                self.assertEqual(s['abstract_not_required'],0)
                self.assertEqual(s['abstract_full_text_reviewed'],0)
                self.assertEqual(s['abstract_supplement_required'],0)
                self.assertEqual(s['issues'],[])
                self.assertIsNone(f[1][0]['abstract'])

    def test_uncertain_article_types_never_gain_this_exemption(self):
        for kind in ('Letter','Research Letter','Perspective','Review','Short communication',
                     'Research article','unknown','Editorial commentary'):
            with self.subTest(kind=kind):
                s=self.render(self.fixture(kind))
                self.assertEqual(s['abstract_nonresearch_excluded'],0)
                self.assertEqual(s['abstract_supplement_required'],1)

    def test_missing_stale_foreign_or_mismatched_evidence_keeps_gap(self):
        mutations=[
            ('include',lambda f:f[2][0]['ai4s_review'].update(decision='include')),
            ('pending',lambda f:f[2][0]['ai4s_review'].update(decision='pending')),
            ('wrong owner',lambda f:f[2][0]['ai4s_review'].update(owner='B')),
            ('stale review',lambda f:f[2][0]['ai4s_review'].update(snapshot_at='old')),
            ('missing candidate proof',lambda f:f[1][0].pop('abstract_requirement')),
            ('candidate proof differs',lambda f:f[1][0]['abstract_requirement'].update(checked_at='other')),
            ('no primary metadata',lambda f:f[2][0]['ai4s_review'].pop('verified_metadata')),
            ('metadata type mismatch',lambda f:f[2][0]['ai4s_review']['verified_metadata'].update(article_type='Review')),
            ('metadata evidence mismatch',lambda f:f[2][0]['ai4s_review']['verified_metadata'].update(evidence_urls=[])),
            ('conflict',lambda f:f[2].append(dict(deepcopy(f[2][0]),ai4s_review={
                'owner':'A','snapshot_at':'current','decision':'include'}))),
        ]
        for key in ('checked_by','checked_at','evidence_urls','reason','verification_basis',
                    'primary_source_url','paper_id','source_code','year','document_type'):
            mutations.append((key,lambda f,key=key:f[2][0]['ai4s_review']['abstract_requirement'].pop(key)))
        for name,mutate in mutations:
            with self.subTest(case=name):
                f=self.fixture();mutate(f);s=self.render(f)
                self.assertEqual(s['abstract_nonresearch_excluded'],0)
                self.assertEqual(s['abstract_supplement_required'],1)
                self.assertTrue(any('候选缺少摘要' in x for x in s['issues']))

    def test_valid_exclusion_does_not_hide_another_live_gap_or_pending(self):
        f=self.fixture();f[1].append({'id':'live','venue':'v','year':2025,'abstract':None})
        f[2].append({'id':'live','venue':'v','year':2025,'ai4s_review':{
            'owner':'A','snapshot_at':'current','decision':'pending'}})
        s=self.render(f)
        self.assertEqual(s['missing_abstract'],2)
        self.assertEqual(s['abstract_nonresearch_excluded'],1)
        self.assertEqual(s['abstract_supplement_required'],1)
        self.assertTrue(any('待定或未审' in x for x in s['issues']))
        self.assertTrue(any('候选缺少摘要' in x for x in s['issues']))

    def test_matching_candidate_proof_still_cannot_authorize_wrong_owner_identity_or_url(self):
        for field,value in [('checked_by','B'),('checked_at','not-a-time'),('paper_id','another'),
                            ('source_code','another'),('year',2026),
                            ('evidence_urls',['http://publisher.example/article']),
                            ('evidence_urls',['https://[']),('primary_source_url','https://another.example/article')]:
            with self.subTest(field=field,value=value):
                f=self.fixture()
                for proof in [f[1][0]['abstract_requirement'],f[2][0]['ai4s_review']['abstract_requirement']]:
                    proof[field]=value
                s=self.render(f)
                self.assertEqual(s['abstract_nonresearch_excluded'],0)
                self.assertEqual(s['abstract_supplement_required'],1)


class ConservativeCutoffPolicyTest(unittest.TestCase):
    def fixture(self, root, owner='A', year=2026):
        row=catalogue_fixtures.NydiiiAuditedCatalogueTest().fixture(root,owner=owner,year=year,excluded=True)
        policy={'status':'authorized_conservative_exclusion','cutoff_at':'2026-11-17T07:14:20Z',
                'checked_by':owner,'checked_at':'2026-11-18T01:00:00+00:00',
                'user_instruction':'Cannot prove publication before cutoff: exclude from fixed range and preserve originals.'}
        report=row['catalogue_audit']['report'];report.update(cutoff_at=policy['cutoff_at'],cutoff_policy=deepcopy(policy))
        row['cutoff_policy']=deepcopy(policy)
        report['scope_exclusions'][0].update(status='publication_time_unproven_before_cutoff',
            verified_year=year,verified_volume='369',source_evidence={'volume':'369'},
            checked_at='2026-11-18T01:00:00+00:00',
            cutoff_at=policy['cutoff_at'],owner_instruction=policy['user_instruction'])
        (root/f'reviews/{year}/feedback/nydiii.json').write_text(json.dumps([row]))
        source=catalogue_fixtures.NydiiiAuditedCatalogueTest().source(root)
        return source,row

    def test_policy_is_owner_year_agnostic_and_does_not_rewrite_originals(self):
        for year,owner in [(2026,'A'),(2025,'B')]:
            with self.subTest(year=year,owner=owner),tempfile.TemporaryDirectory() as d:
                root=Path(d);source,row=self.fixture(root,owner,year);original=deepcopy(row)
                self.assertTrue(verified_audited_catalogue(root,year,source,row))
                self.assertEqual(row,original)
                self.assertEqual(source['issues'],[])
                self.assertEqual(source['state'],'abstract_incomplete')

    def test_untrusted_policy_or_broken_identity_partition_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);source,row=self.fixture(root)
            def report(r):return r['catalogue_audit']['report']
            def excluded(r):return report(r)['scope_exclusions'][0]
            mutations=[
                ('no row policy',lambda r:r.pop('cutoff_policy')),
                ('no report policy',lambda r:report(r).pop('cutoff_policy')),
                ('policy mismatch',lambda r:report(r)['cutoff_policy'].update(checked_at='other')),
                ('item cutoff',lambda r:excluded(r).update(cutoff_at='2026-11-18T07:14:20Z')),
                ('report cutoff',lambda r:report(r).update(cutoff_at='2026-11-18T07:14:20Z')),
                ('item instruction',lambda r:excluded(r).update(owner_instruction='ignore')),
                ('item wrong owner',lambda r:excluded(r).update(checked_by='B')),
                ('item year',lambda r:excluded(r).update(verified_year=2027)),
                ('bool year',lambda r:excluded(r).update(verified_year=True)),
                ('no actual volume',lambda r:excluded(r).update(verified_volume=None)),
                ('different volume',lambda r:excluded(r).update(verified_volume='370')),
                ('no primary volume metadata',lambda r:excluded(r).pop('source_evidence')),
                ('no item URLs',lambda r:excluded(r).update(evidence_urls=[])),
                ('http URL',lambda r:excluded(r).update(evidence_urls=['http://publisher.example/later'])),
                ('invalid URL',lambda r:excluded(r).update(evidence_urls=['https://['])),
                ('ignore status',lambda r:excluded(r).update(status='ignore')),
                ('deleted exclusion',lambda r:report(r)['scope_exclusions'].pop()),
                ('wrong snapshot',lambda r:report(r).update(snapshot_at='old')),
                ('wrong raw owner',lambda r:r['catalogue_audit'].update(owner='B')),
                ('duplicate canonical',lambda r:report(r)['canonical_records'].append(deepcopy(report(r)['canonical_records'][0]))),
            ]
            for field in ('checked_by','checked_at','user_instruction','status','cutoff_at'):
                mutations.append(('missing policy '+field,lambda r,field=field:r['cutoff_policy'].pop(field)))
            for field,value in [('status','ignore'),('checked_by','B'),('checked_at',''),
                                ('checked_at','not-a-time'),('user_instruction','')]:
                def alter_both(r,field=field,value=value):
                    r['cutoff_policy'][field]=value;report(r)['cutoff_policy'][field]=value
                mutations.append(('coherent but invalid '+field,alter_both))
            for name,mutate in mutations:
                with self.subTest(case=name):
                    bad=deepcopy(row);mutate(bad)
                    self.assertFalse(verified_audited_catalogue(root,2026,source,bad))


EVIDENCE=Path(__file__).resolve().parents[2]/'parallel-monitor-proofs'

@unittest.skipUnless((EVIDENCE/'j-437bcb1511-catalogue-proof-package.json').exists(),
                     'Optional real owner audit evidence is supplied outside the website repository')
class RealOwnerEvidenceTest(unittest.TestCase):
    def test_all_267_real_time_unproven_exclusions_require_policy(self):
        p=json.loads((EVIDENCE/'j-437bcb1511-catalogue-proof-package.json').read_text())
        source,row=p['source'],p['row'];before=deepcopy(row)
        exclusions=row['catalogue_audit']['report']['scope_exclusions']
        self.assertEqual(sum(z['status']=='publication_time_unproven_before_cutoff' for z in exclusions),267)
        self.assertTrue(verified_audited_catalogue(EVIDENCE,2026,source,row))
        self.assertEqual(row,before)
        for field in ('cutoff_policy',):
            bad=deepcopy(row);bad.pop(field)
            self.assertFalse(verified_audited_catalogue(EVIDENCE,2026,source,bad))
        for field,value in [('cutoff_at','2026-11-18T07:14:20Z'),('owner_instruction','ignore'),
                            ('checked_by','Other owner'),('status','ignore')]:
            bad=deepcopy(row);z=next(z for z in bad['catalogue_audit']['report']['scope_exclusions']
                                  if z['status']=='publication_time_unproven_before_cutoff');z[field]=value
            self.assertFalse(verified_audited_catalogue(EVIDENCE,2026,source,bad))
        bad=deepcopy(row);bad['catalogue_audit']['report']['scope_exclusions'].pop()
        self.assertFalse(verified_audited_catalogue(EVIDENCE,2026,source,bad))

    def test_six_actual_document_type_exclusions_match_candidate_proofs(self):
        candidates=json.loads((EVIDENCE/'nonresearch-abstract-candidate-proof-delta.json').read_text())
        reviews=json.loads((EVIDENCE/'nonresearch-abstract-review-proof-delta.json').read_text())
        records={(x['venue'],x['id']):x for x in reviews};self.assertEqual(len(candidates),6)
        for candidate in candidates:
            review=records[candidate['venue'],candidate['id']]['ai4s_review']
            self.assertIsNone(candidate['abstract'])
            self.assertEqual(candidate['abstract_requirement'],review['abstract_requirement'])
            self.assertTrue(verified_nonresearch_abstract_exclusion(candidate,review,review['owner']))

