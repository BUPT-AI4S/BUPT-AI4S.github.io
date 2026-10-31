"""Compile YAML-front-matter Markdown papers and generate a static catalog."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import difflib
import unicodedata
import hashlib
import yaml
from markdown_it import MarkdownIt
from urllib.parse import urlparse, unquote

ROOT=Path(__file__).resolve().parents[1]
INDEX_FIELDS=('id','title','titleZh','authors','affiliations','published','dateType','venue','year',
              'disciplines','subfield','keywords','tags','topics','abstract','abstractZh',
              'summaryZh','summaryEn','paperUrl','pdfUrl','forumUrl','codeUrl','sample','abstractSource','abstractLicense','tagIds',
              'arxivUrl','arxivStatus','githubSource','session','sessionTime','room','poster')
INDEX_FIELDS+=('imported','classificationStatus','pdfAvailability','codeAvailability','projectUrl','dateRaw','datePrecision','sourceDate')

class FirstImage(HTMLParser):
    def __init__(self):
        super().__init__()
        self.image = None
    def handle_starttag(self, tag, attrs):
        if tag == 'img' and self.image is None:
            values = dict(attrs)
            if values.get('src'):
                self.image = {'src': unescape(values['src']), 'alt': values.get('alt', '')}

def tag_key(value):
    return ' '.join(unicodedata.normalize('NFKC',value).strip().casefold().split())

def validate_tag_vocabulary(data):
    if not isinstance(data,dict) or data.get('schemaVersion')!=1 or not isinstance(data.get('tags'),list):
        raise ValueError('Tag vocabulary: expected schemaVersion: 1 and a tags array')
    lookup={};ids=set()
    for tag in data['tags']:
        if not isinstance(tag,dict):raise ValueError('Tag vocabulary: each tag must be an object')
        for field in ('id','nameEn','nameZh'):
            if not isinstance(tag.get(field),str) or not tag[field].strip():raise ValueError(f'Tag vocabulary: missing {field}')
        if not re.fullmatch(r'[a-z][a-z0-9-]*',tag['id']):raise ValueError(f'Invalid tag id: {tag["id"]}')
        if tag['id'] in ids:raise ValueError(f'Duplicate tag id: {tag["id"]}')
        ids.add(tag['id'])
        aliases=tag.get('aliases',[])
        if not isinstance(aliases,list) or any(not isinstance(a,str) or not a.strip() for a in aliases):
            raise ValueError(f'{tag["id"]}: aliases must be nonempty strings')
        if tag.get('sourceUrl') and (not isinstance(tag['sourceUrl'],str) or urlparse(tag['sourceUrl']).scheme!='https'):
            raise ValueError(f'{tag["id"]}: sourceUrl must use HTTPS')
        for name in [tag['id'],tag['nameEn'],tag['nameZh'],*aliases]:
            key=tag_key(name)
            if key in lookup and lookup[key]['id']!=tag['id']:
                raise ValueError(f'Tag name or alias collision: {name} ({lookup[key]["id"]} / {tag["id"]})')
            lookup[key]=tag
    return lookup

def load_tag_vocabulary(root):
    path=Path(root)/'data/paper-tags.yml'
    if not path.exists():raise ValueError(f'Missing tag vocabulary: {path}')
    if path.is_symlink() or not path.resolve().is_relative_to(Path(root).resolve()):raise ValueError('Invalid tag vocabulary path')
    try:data=yaml.load(path.read_text(encoding='utf-8-sig'),Loader=PaperLoader)
    except yaml.YAMLError as exc:raise ValueError(f'{path}: {exc}') from exc
    return data,validate_tag_vocabulary(data)

def keyword_key(value):
    return re.sub(r'\s+',' ',re.sub(r'[-\u2010-\u2015]+',' ',tag_key(value))).strip()

def keyword_values(paper):
    return [part.strip() for value in paper.get('keywords',[]) for part in re.split(r'[;；]',value) if part.strip()]

def load_keyword_vocabulary(root,vocabulary):
    path=Path(root)/'data/keyword-tag-vocabulary.json'
    if not path.exists():return False
    if path.is_symlink():raise ValueError('Invalid keyword vocabulary path')
    extra=read_json(path)
    validate_tag_vocabulary(extra)
    data,lookup=vocabulary;existing={t['id']:t for t in data['tags']}
    for tag in extra['tags']:
        if not re.search(r'[\u3400-\u9fff]',tag['nameZh']):raise ValueError('Keyword tag needs a Chinese name: '+tag['id'])
        if tag['id'] in existing:
            original=existing[tag['id']]
            if any(original[key]!=tag[key] for key in ('nameEn','nameZh')):raise ValueError('Core tag names must be preserved: '+tag['id'])
            original['aliases']=list(dict.fromkeys(original.get('aliases',[])+tag.get('aliases',[])))
        else:data['tags'].append(tag)
    lookup.clear();lookup.update(validate_tag_vocabulary(data))
    return True

def register_keyword_tags(vocabulary,papers,require_translations=False):
    data,lookup=vocabulary
    matches={keyword_key(name):tag for name,tag in lookup.items()}
    groups={}
    for paper in papers:
        for value in keyword_values(paper):groups.setdefault(keyword_key(value),set()).add(value)
    for key,variants in sorted(groups.items()):
        if key not in matches:
            label=sorted(variants,key=lambda s:(len(s),s.casefold(),s))[0]
            if require_translations:raise ValueError('Untranslated metadata keyword: '+label)
            tag={'id':'keyword-'+hashlib.sha256(key.encode('utf-8')).hexdigest()[:16],
                 'nameEn':label,'nameZh':label,'aliases':sorted(variants),
                 'source':'metadata-keywords'}
            data['tags'].append(tag);matches[key]=tag
        else:
            tag=matches[key]
            tag['aliases']=list(dict.fromkeys(tag.get('aliases',[])+sorted(variants)))
    lookup.clear();lookup.update(validate_tag_vocabulary(data))
    return {key:tag['id'] for key,tag in matches.items()}

def normalize_paper_tags(paper,vocabulary,label,keyword_tags=None):
    if vocabulary is None:raise ValueError('Missing tag vocabulary')
    _,lookup=vocabulary;paper=dict(paper);ids=[]
    if keyword_tags is not None:
        paper['tags']=list(dict.fromkeys(paper.get('tags',[])+[
            keyword_tags[keyword_key(value)] for value in keyword_values(paper)]))
    for field in ('tags','topics'):
        if field not in paper:continue
        names=[]
        for raw in paper[field]:
            key=tag_key(raw)
            if key not in lookup:
                close=difflib.get_close_matches(key,lookup,n=3,cutoff=.6)
                suggestions=list(dict.fromkeys(lookup[k]['nameEn'] for k in close))
                raise ValueError(f'{label}: Unknown tag {raw!r}; check data/paper-tags.yml'+
                                 ('; possible matches: '+', '.join(suggestions) if suggestions else '; register the new tag before uploading'))
            tag=lookup[key]
            if tag['id'] not in names:names.append(tag['id'])
            if tag['id'] not in ids:ids.append(tag['id'])
        paper[field]=names
    paper['tagIds']=ids
    return paper

class PaperLoader(yaml.SafeLoader):
    def construct_mapping(self,node,deep=False):
        pairs=[]
        for key,value in node.value:
            key=self.construct_object(key,deep=deep)
            if not isinstance(key,str): raise ValueError('YAML keys must be strings')
            pairs.append((key,self.construct_object(value,deep=deep)))
        return unique_object(pairs)

def read_markdown(path):
    text=path.read_text(encoding='utf-8-sig').replace('\r\n','\n')
    match=re.fullmatch(r'---\n(.*?)\n---(?:\n|$)(.*)',text,re.S)
    if not match: raise ValueError(f'{path}: missing YAML front matter')
    try:
        # Aliases can expand unexpectedly and make hand-edited metadata ambiguous.
        if any(isinstance(t,(yaml.tokens.AliasToken,yaml.tokens.AnchorToken)) for t in yaml.scan(match[1])):
            raise ValueError('YAML aliases and anchors are not supported')
        paper=yaml.load(match[1],Loader=PaperLoader)
        if not isinstance(paper,dict): raise ValueError('YAML metadata must be an object')
        for key in ('year','published'):
            if key in paper and not isinstance(paper[key],(dict,list,bool)):
                paper[key]=str(paper[key])
        # Dates in provenance should remain strings too.
        if isinstance(paper.get('notesMeta'),dict) and 'generated' in paper['notesMeta']:
            paper['notesMeta']['generated']=str(paper['notesMeta']['generated'])
        if any(k in paper for k in ('notes','content','figures')):
            raise ValueError('Write notes and figures in the Markdown body, not YAML')
        return paper,match[2].strip()
    except (yaml.YAMLError,ValueError) as exc: raise ValueError(f'{path}: {exc}') from exc

class PaperDumper(yaml.SafeDumper):
    pass

def readable_string(dumper,value):
    return dumper.represent_scalar('tag:yaml.org,2002:str',value,style='|' if '\n' in value or len(value)>120 else None)

PaperDumper.add_representer(str,readable_string)

def markdown_source(paper,body):
    """Serialize metadata only; keep the editable Markdown body intact."""
    return '---\n'+yaml.dump(paper,Dumper=PaperDumper,allow_unicode=True,sort_keys=False,width=100000)+'---\n\n'+body.strip()+'\n'

def paper_files(folder):
    """Each new paper directory has exactly one source: paper.md."""
    files=[*folder.glob('*.md'),*folder.glob('*.json')]
    for directory in sorted(folder.iterdir()) if folder.exists() else []:
        if directory.is_symlink():raise ValueError(f'Symlink not allowed for paper directory: {directory.name}')
        if not directory.is_dir():continue
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',directory.name) or directory.name.endswith('.local'):
            raise ValueError(f'Invalid paper directory: {directory.name}')
        source=directory/'paper.md'
        if not source.is_file():raise ValueError(f'{directory.name}: missing paper.md')
        if any(f.name!='paper.md' for f in directory.glob('*.md')):
            raise ValueError(f'{directory.name}: keep only paper.md at the directory root')
        files.append(source)
    return sorted(files)

def paper_key(file,folder):
    return file.parent.name if file.parent!=folder else file.stem

def compile_markdown(body,file,root):
    marker=r'(?m)^<!-- language: en -->\s*$'
    parts=re.split(marker,body)
    if len(parts)>2: raise ValueError(f'{file}: duplicate English language marker')
    content={}
    for lang,text in zip(('zh','en'),parts):
        md=MarkdownIt('js-default',{'html':False})
        tokens=md.parse(text);toc=[];anchors={};used=set()
        def visit(items):
            for token in items:
                if token.type=='image':
                    src=token.attrGet('src');parsed=urlparse(src)
                    if parsed.scheme or parsed.netloc:
                        if parsed.scheme!='https': raise ValueError(f'{file}: image must use HTTPS')
                    else:
                        if parsed.query or parsed.fragment: raise ValueError(f'{file}: invalid image path')
                        image=(file.parent/unquote(parsed.path)).resolve()
                        allowed=(file.parent/'images') if file.name=='paper.md' else root/'static/images/papers'
                        if not image.is_relative_to(allowed.resolve()) or not image.is_relative_to(root.resolve()) or not image.is_file():
                            raise ValueError(f'{file}: missing or invalid local image: {src}')
                        token.attrSet('src',image.relative_to(root.resolve()).as_posix())
                    token.attrSet('loading','lazy')
                if token.type=='link_open':
                    href=token.attrGet('href') or ''
                    if href.startswith('#') and unquote(href[1:]) in anchors:
                        token.attrSet('href','#'+anchors[unquote(href[1:])])
                    if not href.startswith('#') and urlparse(href).scheme!='https':
                        raise ValueError(f'{file}: link must use HTTPS or an anchor: {href}')
                    if not href.startswith('#'):
                        token.attrSet('target','_blank');token.attrSet('rel','noopener noreferrer')
                if token.children:visit(token.children)
        for i,token in enumerate(tokens):
            if token.type=='heading_open':
                title=tokens[i+1].content
                slug=re.sub(r'\s+','-',re.sub(r'[^\w\s-]','',title.lower()).strip()) or 'section'
                unique=slug;number=0
                while unique in used:
                    number+=1;unique=f'{slug}-{number}'
                used.add(unique)
                anchor=f'md-{lang}-{unique}';anchors[unique]=anchor
                token.attrSet('id',anchor)
                toc.append({'id':anchor,'title':title,'level':int(token.tag[1:])})
        visit(tokens)
        content[lang]={'html':md.renderer.render(tokens,md.options,{}),'toc':toc}
    return content

def unique_object(pairs):
    obj={}
    for key,value in pairs:
        if key in obj: raise ValueError(f'Duplicate JSON key: {key}')
        obj[key]=value
    return obj

def read_json(path):
    try: return json.loads(path.read_text(encoding='utf-8-sig'),object_pairs_hook=unique_object)
    except (ValueError,OSError) as exc: raise ValueError(f'{path}: {exc}') from exc

def validate(value,spec,schema,path='$'):
    """Validate the constraints used by the bundled v1 schema (not a general schema engine)."""
    if '$ref' in spec:
        target=schema
        for part in spec['$ref'][2:].split('/'): target=target[part]
        return validate(value,target,schema,path)
    if 'const' in spec and value!=spec['const']: raise ValueError(f'{path}: invalid constant')
    if 'enum' in spec and value not in spec['enum']: raise ValueError(f'{path}: invalid value')
    kind=spec.get('type')
    types={'object':dict,'array':list,'string':str,'boolean':bool}
    if kind and (kind not in types or not isinstance(value,types[kind])): raise ValueError(f'{path}: expected {kind}')
    if kind=='object':
        for key in spec.get('required',[]):
            if key not in value: raise ValueError(f'{path}: missing {key}')
        for key,item in value.items():
            child=spec.get('properties',{}).get(key,spec.get('additionalProperties'))
            if isinstance(child,dict): validate(item,child,schema,path+'.'+key)
    elif kind=='array':
        for i,item in enumerate(value): validate(item,spec.get('items',{}),schema,f'{path}[{i}]')
    elif kind=='string':
        if len(value.strip())<spec.get('minLength',0): raise ValueError(f'{path}: empty value')
        if 'pattern' in spec and not re.search(spec['pattern'],value): raise ValueError(f'{path}: invalid format')

def validate_paper(paper,schema,root,label):
    if 'content' in paper:raise ValueError(f'{label}: content is reserved for generated Markdown HTML')
    validate(paper,schema['$defs']['paper'],schema,label)
    ids=[n['id'] for n in paper.get('notes',[])]
    if len(ids)!=len(set(ids)): raise ValueError(f'{label}: Duplicate section id')
    for field in ('paperUrl','pdfUrl','forumUrl','codeUrl','abstractSource','abstractLicense','arxivUrl','projectUrl'):
        if paper.get(field) and urlparse(paper[field]).scheme!='https': raise ValueError(f'{label}: {field} must use HTTPS')
    for figure in paper.get('figures',[]):
        src=figure['src']; parsed=urlparse(src)
        if parsed.scheme or parsed.netloc:
            if parsed.scheme!='https': raise ValueError(f'{label}: image must use HTTPS or a repository path')
        else:
            image=(root/unquote(parsed.path)).resolve()
            if not image.is_relative_to((root/'static/images/papers').resolve()) or not image.is_file():
                raise ValueError(f'{label}: missing or invalid local image: {src}')

def build_index(folder,schema_path,config,root,details=None):
    schema=read_json(schema_path)
    validate(config.get('tagTranslations',{}),schema['properties']['tagTranslations'],schema,'tagTranslations')
    vocabulary=load_tag_vocabulary(root)
    translated_keywords=load_keyword_vocabulary(root,vocabulary)
    imported_sources=[]
    for source in sorted((root/'data/imported').glob('ai4s-*.json')):
        if source.is_symlink():raise ValueError('Symlink not allowed for imported metadata')
        imported=read_json(source)
        if imported.get('schemaVersion')!=1 or not isinstance(imported.get('papers'),list):raise ValueError('Invalid imported catalog')
        for paper in imported['papers']:validate_paper(paper,schema,root,str(paper.get('id','')))
        imported_sources.append((source,imported['papers']))
    keyword_tags=register_keyword_tags(vocabulary,[p for _,rows in imported_sources for p in rows],translated_keywords)
    papers=[]; ids=set(); filenames=set()
    for file in paper_files(folder):
        if file.name.endswith(('.local.json','.local.md')): raise ValueError(f'Paper filename uses reserved local suffix: {file.name}')
        if file.is_symlink(): raise ValueError(f'Symlink not allowed for paper: {file.name}')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.(md|json)',file.name): raise ValueError(f'Invalid paper filename: {file.name}')
        key=paper_key(file,folder)
        if key.lower() in filenames: raise ValueError(f'Duplicate filename: {key}')
        filenames.add(key.lower())
        body=None
        if file.suffix=='.md':paper,body=read_markdown(file)
        else:paper=read_json(file)
        validate_paper(paper,schema,root,file.name)
        paper=normalize_paper_tags(paper,vocabulary,file.relative_to(folder).as_posix())
        if body is not None:paper['content']=compile_markdown(body,file,root)
        if paper['id'] in ids: raise ValueError(f'Duplicate paper id: {paper["id"]}')
        ids.add(paper['id'])
        item={key:paper[key] for key in INDEX_FIELDS if key in paper}
        for content in paper.get('content',{}).values():
            parser=FirstImage();parser.feed(content.get('html',''))
            if parser.image:
                item['thumbnail']=parser.image
                break
        if 'thumbnail' not in item and paper.get('figures'):
            figure=paper['figures'][0]
            item['thumbnail']={'src':figure['src'],'alt':figure.get('altZh',figure.get('captionZh',''))}
        item.update(dataUrl='data/papers-built/'+key+'.json',
                    hasNotes=bool(body) if body is not None else bool(paper.get('notes')))
        item['sourceUrl']='data/papers/'+file.relative_to(folder).as_posix()
        if details is not None:details[key+'.json']=paper
        papers.append(item)
    # Bulk metadata stays separate from authored Markdown. Curated content wins
    # when a normalized title and conference year identify the same record.
    title_key=lambda p:(''.join(c for c in unicodedata.normalize('NFKC',p['title']).casefold() if c.isalnum()),str(p.get('year','')))
    authored={title_key(p) for p in papers}
    for source,rows in imported_sources:
        for original in rows:
            paper=dict(original)
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*',str(paper.get('id',''))):raise ValueError('Unsafe imported paper id')
            if any(key in paper for key in ('content','notes','notesMeta')):raise ValueError('Imported metadata cannot supply generated HTML or notes')
            validate_paper(paper,schema,root,paper['id'])
            paper=normalize_paper_tags(paper,vocabulary,source.name,keyword_tags)
            if title_key(paper) in authored:continue
            if paper['id'] in ids:raise ValueError('Duplicate imported paper id: '+paper['id'])
            if paper['id'].casefold() in filenames:raise ValueError('Duplicate imported detail filename: '+paper['id'])
            ids.add(paper['id'])
            filenames.add(paper['id'].casefold())
            paper['imported']=True
            paper['hasNotes']=False
            paper['content']={lang:{'html':'','toc':[]} for lang in ('zh','en')}
            item={key:paper[key] for key in INDEX_FIELDS if key in paper}
            filename=paper['id']+'.json'
            item.update(dataUrl='data/papers-built/'+filename,hasNotes=False,sourceUrl=source.relative_to(root).as_posix())
            if details is not None:details[filename]=paper
            papers.append(item)
    if not papers: raise ValueError('No paper Markdown files found')
    return {'schemaVersion':1,'updated':datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
            'tagTranslations':{t['id']:t['nameZh'] for t in vocabulary[0]['tags']} if vocabulary else config.get('tagTranslations',{}),
            'tagLabelsEn':{t['id']:t['nameEn'] for t in vocabulary[0]['tags']} if vocabulary else {},
            'tagVocabulary':vocabulary[0]['tags'] if vocabulary else [],'papers':papers}

def write_index(root=ROOT,schema_path=None):
    root=Path(root)
    config=read_json(root/'data/papers-config.json') if (root/'data/papers-config.json').exists() else {}
    details={}
    data=build_index(root/'data/papers',schema_path or root/'data/papers.schema.json',config,root,details)
    built=root/'data/papers-built'
    if built.is_symlink():raise ValueError('Unsafe generated detail directory')
    built.mkdir(exist_ok=True)
    for name,paper in details.items():
        output=built/name
        if output.is_symlink():raise ValueError('Unsafe generated detail file')
        temp=output.with_suffix('.json.tmp')
        temp.write_text(json.dumps(paper,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(output)
    for file in built.glob('*.json'):
        if file.name not in details:file.unlink()
    output=root/'data/papers-index.json';temp=output.with_suffix('.json.tmp')
    temp.write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n',encoding='utf-8');temp.replace(output)
    return data

def stage_site(root=ROOT):
    root=Path(root).resolve();destination=root/'_site'
    # Only replace our own generated directory, never an arbitrary target or symlink.
    if destination.is_symlink() or destination.resolve()!=root/'_site': raise ValueError('Unsafe staging path')
    marker=destination/'.generated-site'
    if destination.exists():
        if not marker.is_file() or marker.read_text()!='AI4S generated site': raise ValueError('_site exists without generation marker')
        shutil.rmtree(destination)
    destination.mkdir();marker.write_text('AI4S generated site')
    def ignored(folder,names):
        for name in names:
            path=Path(folder)/name
            if path.is_symlink() or name.startswith('.') or name=='__pycache__' or name.endswith(('.local.json','.pyc','.log','.tmp')):
                yield name
    for file in root.glob('*.html'): shutil.copy2(file,destination/file.name)
    if (root/'CNAME').is_file(): shutil.copy2(root/'CNAME',destination/'CNAME')
    for name in ('static','data','course_material','lectures','syllabus','assignments','AI4S第二讲_AI-Ready科学数据_综述图文版'):
        source=root/name
        if source.is_symlink(): raise ValueError(f'Symlink not allowed in site: {source}')
        if source.is_dir(): shutil.copytree(source,destination/name,ignore=lambda path,names:list(ignored(path,names)))
    archive=root/'AI4S第二讲_AI-Ready科学数据_综述图文版.rar'
    if archive.is_file(): shutil.copy2(archive,destination/archive.name)
    (destination/'.nojekyll').touch()
    return destination

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',type=Path,default=ROOT);parser.add_argument('--site',action='store_true',help='Stage public website files in _site for GitHub Pages')
    args=parser.parse_args()
    try:
        data=write_index(args.root);print(f'Validated {len(data["papers"])} papers; generated data/papers-index.json')
        if args.site: print(f'Staged site: {stage_site(args.root)}')
    except ValueError as exc: parser.exit(1,f'Paper index build failed: {exc}\n')
