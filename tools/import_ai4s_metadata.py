"""Apply supplied, classified AI4S metadata without rerunning candidate filtering."""
import argparse
from collections import Counter,defaultdict
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlsplit

from clean_ai4s_metadata import _normalized_record,_merge,safe_https

CATEGORIES=dict(zip([
    '科学数据','科学知识模型','科学基础模型','科学智能体','科学评测','自主实验室',
    'AI for 数理科学','AI for 生命科学','AI for 物质科学','AI for 地球宇宙科学','AI for 信息科学','AI for 社会科学',
],[
    'scientific-data','scientific-knowledge-models','scientific-foundation-models','scientific-agents','scientific-evaluation','autonomous-labs',
    'mathematical-sciences','life-sciences','matter-sciences','earth-space-sciences','information-sciences','social-sciences',
]))

def title_key(p):
    return ''.join(c for c in unicodedata.normalize('NFKC',p['title']).casefold() if c.isalnum())

def adapt_record(raw,source,as_of=None):
    if not isinstance(raw.get('ai4s_tags'),list):raise ValueError('Missing supplied ai4s_tags: '+str(raw.get('title')))
    p=_merge([_normalized_record(raw,as_of=as_of or date.today())])
    p['id']=p['id'].replace('import-2026-',f"import-{p['year']}-",1)
    p['disciplines']=list(dict.fromkeys(CATEGORIES[t] for t in raw['ai4s_tags'] if t in CATEGORIES))
    p['classificationStatus']='source-provided' if p['disciplines'] else 'needs-review'
    p['recordFlags']=[f for f in p['recordFlags'] if f!='taxonomy-rule-derived']
    provenance=p['metadataProvenance']
    provenance.update(source=source,classificationMethod='source-ai4s-tags',sourceAi4sTags=raw['ai4s_tags'],
                      sourceAi4sTagging=raw.get('ai4s_tagging',{}),importedAt=str(as_of or date.today()))
    provenance.pop('classificationEvidence',None)
    if raw.get('doi'):provenance['dois']=[raw['doi']]
    p['_excluded']=raw.get('ai4s_tagging',{}).get('status')=='out_of_scope' or '非AI4S（当前口径）' in raw['ai4s_tags']
    return p

def formal(p):
    return bool(p.get('venue')) and p['venue'].casefold() not in ('arxiv','arxiv.org','preprint','unknown')

def publication_rank(p):
    host=urlsplit(p.get('paperUrl','')).hostname or ''
    if not formal(p) or host in ('arxiv.org','www.arxiv.org'):return 0
    return 1 if host in ('openreview.net','www.openreview.net') else 2

def merge_record(old,new,authored=False):
    preferred=new if publication_rank(new)>=publication_rank(old) else old
    secondary=old if preferred is new else new
    merged=deepcopy(old)
    for k,v in preferred.items():
        if v not in ('',None,[]) or k=='disciplines':merged[k]=deepcopy(v)
    for k,v in secondary.items():
        if not merged.get(k) and k not in ('disciplines','_excluded'):merged[k]=deepcopy(v)
    merged['id']=old['id']
    # Classification updates are independent of which publication version wins.
    for k in ('disciplines','classificationStatus','recordFlags'):merged[k]=deepcopy(new.get(k,[]))
    old_meta=old.get('metadataProvenance',{});new_meta=new.get('metadataProvenance',{})
    meta={**old_meta,**new_meta}
    for k in ('originalIds','sourceUrls','rawPublishedValues','dois'):
        meta[k]=list(dict.fromkeys(old_meta.get(k,[])+new_meta.get(k,[])))
    merged['metadataProvenance']=meta
    for candidate in (old,new):
        url=candidate.get('arxivUrl') or candidate.get('paperUrl','')
        if re.match(r'https://(?:www\.)?arxiv\.org/',url):merged['arxivUrl']=url
    if authored:
        # Source imports must not replace authored prose, translations or notes.
        publication=('venue','year','paperUrl','pdfUrl','codeUrl','published')
        keep=deepcopy(old)
        if publication_rank(new)>publication_rank(old):
            for k in publication:
                if k in merged:keep[k]=merged[k]
        keep['disciplines']=merged.get('disciplines',[])
        if merged.get('arxivUrl'):keep['arxivUrl']=merged['arxivUrl']
        return keep
    return merged

def identity_keys(p):
    keys=set()
    url=safe_https(p.get('paperUrl'))
    if url:
        url=url.split('#')[0].rstrip('/')
        if re.match(r'https://arxiv.org/(?:abs|pdf)/',url):url=re.sub(r'v\d+$','',url.replace('/pdf/','/abs/').removesuffix('.pdf'))
        keys.add('url:'+url)
    meta=p.get('metadataProvenance',{})
    for value in meta.get('originalIds',[])+meta.get('dois',[]):
        value=re.sub(r'^https?://(?:dx\.)?doi.org/','',value,flags=re.I)
        if re.match(r'^10\.\d{4,9}/',value):keys.add('doi:'+value.casefold())
    return keys

def compatible_authors(a,b):
    def names(p):
        return {''.join(sorted(re.findall(r'\w+',unicodedata.normalize('NFKC',x).casefold()))) for x in p.get('authors',[])}
    aa,bb=names(a),names(b)
    return not aa or not bb or bool(aa&bb)

def update_catalog(existing,incoming,authored=()):
    papers=deepcopy(existing);original_ids={p['id'] for p in papers};authored=set(authored)
    titles=defaultdict(set);identities=defaultdict(set);removed=set();updated=set();added=set();excluded=[];duplicates=0;seen=set()
    def index(i,p):
        titles[title_key(p)].add(i)
        for k in identity_keys(p):identities[k].add(i)
    for i,p in enumerate(papers):index(i,p)
    for p in incoming:
        key=title_key(p)
        if key in seen:duplicates+=1
        seen.add(key)
        strong=set().union(*(identities[k] for k in identity_keys(p))) if identity_keys(p) else set()
        matches=(strong|{i for i in titles[key] if compatible_authors(papers[i],p)})-removed
        if len(matches)>1:raise ValueError('Ambiguous existing records: '+p['title'])
        i=next(iter(matches),None)
        if p.get('_excluded'):
            if i is not None:
                if papers[i]['id'] in authored:raise ValueError('Excluded source conflicts with authored paper: '+p['title'])
                removed.add(i)
            excluded.append({'title':p['title'],'year':p['year'],'previousId':papers[i]['id'] if i is not None else None})
            continue
        if i is None:
            if p['id'] in {x['id'] for x in papers}:raise ValueError('Generated ID collision: '+p['id'])
            papers.append(deepcopy(p));i=len(papers)-1;added.add(p['id'])
        else:
            papers[i]=merge_record(papers[i],p,papers[i]['id'] in authored)
            if papers[i]['id'] in original_ids:updated.add(papers[i]['id'])
        index(i,papers[i])
    return {'papers':[{k:v for k,v in p.items() if not k.startswith('_')} for i,p in enumerate(papers) if i not in removed],
            'updatedIds':sorted(updated),'addedIds':sorted(added),'excluded':excluded,'duplicateInputRows':duplicates}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sources',nargs='+',type=Path)
    parser.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--apply',action='store_true')
    args=parser.parse_args();root=args.root
    from build_paper_index import read_markdown
    import yaml
    existing=[];authored={};source_report=[];incoming=[]
    for path in sorted((root/'data/imported').glob('ai4s-*.json')):existing+=json.loads(path.read_text(encoding='utf-8'))['papers']
    for path in sorted((root/'data/papers').rglob('*')):
        if path.suffix not in ('.md','.json'):continue
        if path.suffix=='.md':p,_=read_markdown(path)
        else:p=json.loads(path.read_text(encoding='utf-8'))
        existing.append(p);authored[p['id']]=(path,p)
    # The builder already hides imported copies of authored papers. Do not let
    # those invisible source rows compete with their stable authored identity.
    existing=[p for p in existing if p['id'] in authored or not any(
        title_key(p)==title_key(a) and compatible_authors(p,a) for _,a in authored.values())]
    for path in args.sources:
        raw=path.read_bytes();rows=json.loads(raw.decode('utf-8-sig'))
        if not isinstance(rows,list):raise ValueError('Expected a JSON array: '+str(path))
        source_report.append({'file':path.name,'sha256':hashlib.sha256(raw).hexdigest(),'rows':len(rows)})
        incoming.extend(adapt_record(r,path.name) for r in rows)
    result=update_catalog(existing,incoming,authored)
    result['sources']=source_report;result['beforeCount']=len(existing);result['afterCount']=len(result['papers'])
    result['disciplines']=dict(Counter(d for p in result['papers'] for d in p.get('disciplines',[])))
    result['unmappedSourceTags']=dict(Counter(t for p in incoming if not p['_excluded'] for t in p['metadataProvenance']['sourceAi4sTags'] if t not in CATEGORIES))
    result['unclassifiedCount']=sum(not p.get('disciplines') for p in result['papers'])
    by_year=defaultdict(list)
    for p in result['papers']:
        if p['id'] in authored:
            path,original=authored[p['id']]
            if p!=original and args.apply:
                if path.suffix=='.md':
                    text=path.read_text(encoding='utf-8');body=text.split('---',2)[2]
                    path.write_text('---\n'+yaml.safe_dump(p,allow_unicode=True,sort_keys=False,width=100000)+'---'+body,encoding='utf-8')
                else:path.write_text(json.dumps(p,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        else:by_year[p.get('year','unknown')].append(p)
    if args.apply:
        for year,rows in by_year.items():
            dest=root/f'data/imported/ai4s-{year}.json'
            dest.write_text(json.dumps({'schemaVersion':1,'source':', '.join(x['file'] for x in source_report),'papers':rows},ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        report={k:v for k,v in result.items() if k!='papers'}
        (root/f'docs/ai4s-upload-{date.today()}.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('papers','addedIds','updatedIds','excluded')},ensure_ascii=True,indent=2))
    print('added',len(result['addedIds']),'updated',len(result['updatedIds']),'excluded',len(result['excluded']))

if __name__=='__main__':main()
