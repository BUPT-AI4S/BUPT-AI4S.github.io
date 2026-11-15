import json,tempfile,unittest
from copy import deepcopy
from pathlib import Path
from tools.build_review_monitor import build
from test_review_monitor import HistoricalAbstractStateTest
class NonresearchOverlayTest(unittest.TestCase):
 def fixture(self):
  s,c,r,f=HistoricalAbstractStateTest().fixture();f['official_total']=3;f['collection_state_resolution']['reason']='full_catalogue_with_nonresearch_additions_candidates_complete';f['catalogue_reconciliation'].update(same_scope_missing=1,verified_nonresearch_additions=1,canonical_unresolved_missing=0)
  raw=[{'id':v,'venue':'v','year':2025} for v in ['one','two']]
  a={'id':'three','venue':'v','year':2025,'title':'Highlight','document_type':'Research Highlight','url':'https://publisher.example/article','published':'2025-03-01','catalogue_supplement':{'owner':'A','snapshot_at':'current','checked_at':'2026-11-15','reason':'official_catalogue_item_missing_from_fixed_raw','disposition':'exclude_nonoriginal','evidence_urls':['https://publisher.example/article']}}
  report={'source_code':'v','year':2025,'owner':'A','snapshot_at':'current','official_total':3,'missing':['three'],'extra':[],'duplicates':0,'rows':[{'id':'one'},{'id':'two'},{'id':'three','title':'Highlight','type':'Research Highlight','url':a['url'],'date':a['published']}]}
  return [s,c,r,f,raw,[a],report]
 def render(self,x,include_evidence=True):
  s,c,r,f,raw,adds,report=x
  with tempfile.TemporaryDirectory() as d:
   p=Path(d);docs={'metadata/2025/snapshot.json':s,'metadata/2025/ai4s.json':c,'reviews/source-assignments-2025.json':{'year':2025,'sources':[{'code':'v','owner':'A'},{'code':'untouched','owner':'A'}]},'reviews/2025/a.json':r,'reviews/2025/feedback/a.json':f,'metadata/v/2025/papers.json':raw,'metadata/v/2025/catalogue-additions.json':adds,'metadata/v/2025/catalogue-reconciliation.json':report}
   for path,obj in docs.items():
    if not include_evidence and path.startswith('metadata/v/'): continue
    file=p/path;file.parent.mkdir(parents=True,exist_ok=True);file.write_text(json.dumps(obj),encoding='utf8')
   return build(p)['years'][0]['sources']
 def test_verified_nonresearch_overlay_closes_only_audited_source(self):
  a,b=self.render(self.fixture());self.assertEqual(a['issues'],[]);self.assertEqual(a['papers'],2);self.assertEqual(a['official_total'],3);self.assertEqual(a['state'],'abstract_incomplete');self.assertTrue(b['issues'])
 def test_invalid_overlays_never_close(self):
  cases=[
   ('wrong reason',lambda s,c,r,f,raw,a,m:f['collection_state_resolution'].update(reason='full_catalogue_abstract_gap_candidates_complete')),
   ('pending',lambda s,c,r,f,raw,a,m:r[0]['ai4s_review'].update(decision='pending')),
   ('abstract gap',lambda s,c,r,f,raw,a,m:c[0].update(abstract=None)),
   ('unhandled gap',lambda s,c,r,f,raw,a,m:m['missing'].append('four')),
   ('missing evidence',lambda s,c,r,f,raw,a,m:a[0]['catalogue_supplement'].update(evidence_urls=[])),
   ('new owner',lambda s,c,r,f,raw,a,m:a[0]['catalogue_supplement'].update(owner='B')),
   ('old snapshot',lambda s,c,r,f,raw,a,m:a[0]['catalogue_supplement'].update(snapshot_at='old')),
   ('research',lambda s,c,r,f,raw,a,m:(a[0].update(document_type='Article'),m['rows'][2].update(type='Article'))),
   ('pending disposition',lambda s,c,r,f,raw,a,m:a[0]['catalogue_supplement'].update(disposition='pending')),
   ('wrong venue',lambda s,c,r,f,raw,a,m:a[0].update(venue='z')),
   ('wrong year',lambda s,c,r,f,raw,a,m:a[0].update(year=2024)),
   ('duplicate addition',lambda s,c,r,f,raw,a,m:a.append(deepcopy(a[0]))),
   ('missing addition',lambda s,c,r,f,raw,a,m:a.clear()),
   ('raw duplicate',lambda s,c,r,f,raw,a,m:raw[1].update(id='one')),
   ('raw other source',lambda s,c,r,f,raw,a,m:raw[1].update(venue='z')),
   ('raw count',lambda s,c,r,f,raw,a,m:raw.pop()),
   ('official count',lambda s,c,r,f,raw,a,m:m.update(official_total=4)),
   ('different identity',lambda s,c,r,f,raw,a,m:m['rows'][2].update(id='different')),
   ('duplicate official',lambda s,c,r,f,raw,a,m:m['rows'].append(deepcopy(m['rows'][0]))),
   ('wrong title',lambda s,c,r,f,raw,a,m:a[0].update(title='Other')),
   ('wrong date',lambda s,c,r,f,raw,a,m:a[0].update(published='2024-03-01')),
   ('wrong formal type',lambda s,c,r,f,raw,a,m:m['rows'][2].update(type='Article')),
   ('wrong URL',lambda s,c,r,f,raw,a,m:a[0].update(url='https://elsewhere.example/')),
   ('wrong report owner',lambda s,c,r,f,raw,a,m:m.update(owner='B')),
   ('wrong report snapshot',lambda s,c,r,f,raw,a,m:m.update(snapshot_at='old')),
   ('unhandled extra',lambda s,c,r,f,raw,a,m:m.update(extra=['four'])),
   ('malformed missing',lambda s,c,r,f,raw,a,m:m.update(missing=[{}])),
   ('unknown missing',lambda s,c,r,f,raw,a,m:f['catalogue_reconciliation'].update(canonical_unresolved_missing=1)),
  ]
  for name,change in cases:
   with self.subTest(name=name):
    x=self.fixture();change(*x);a=self.render(x)[0];self.assertNotIn('collection_state_resolution',a);self.assertTrue(a['issues'])
