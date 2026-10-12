"""Compile YAML-front-matter Markdown papers and generate a static catalog."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import shutil
import yaml
from markdown_it import MarkdownIt
from urllib.parse import urlparse, unquote

ROOT=Path(__file__).resolve().parents[1]
INDEX_FIELDS=('id','title','titleZh','authors','affiliations','published','dateType','venue','year',
              'disciplines','subfield','keywords','tags','topics','abstract','abstractZh',
              'summaryZh','summaryEn','paperUrl','pdfUrl','forumUrl','codeUrl','sample')

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
                        if not image.is_relative_to((root/'static/images/papers').resolve()) or not image.is_file():
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
    for field in ('paperUrl','pdfUrl','forumUrl','codeUrl'):
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
    papers=[]; ids=set(); filenames=set()
    for file in sorted([*folder.glob('*.md'),*folder.glob('*.json')]):
        if file.name.endswith(('.local.json','.local.md')): raise ValueError(f'Paper filename uses reserved local suffix: {file.name}')
        if file.is_symlink(): raise ValueError(f'Symlink not allowed for paper: {file.name}')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.(md|json)',file.name): raise ValueError(f'Invalid paper filename: {file.name}')
        if file.stem.lower() in filenames: raise ValueError(f'Duplicate filename: {file.name}')
        filenames.add(file.stem.lower())
        body=None
        if file.suffix=='.md':paper,body=read_markdown(file)
        else:paper=read_json(file)
        validate_paper(paper,schema,root,file.name)
        if body is not None:paper['content']=compile_markdown(body,file,root)
        if paper['id'] in ids: raise ValueError(f'Duplicate paper id: {paper["id"]}')
        ids.add(paper['id'])
        item={key:paper[key] for key in INDEX_FIELDS if key in paper}
        item.update(dataUrl=('data/papers-built/'+file.stem+'.json') if body is not None else 'data/papers/'+file.name,
                    hasNotes=bool(body) if body is not None else bool(paper.get('notes')))
        if body is not None:
            item['sourceUrl']='data/papers/'+file.name
            if details is not None:details[file.stem+'.json']=paper
        papers.append(item)
    if not papers: raise ValueError('No paper Markdown files found')
    return {'schemaVersion':1,'updated':datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
            'tagTranslations':config.get('tagTranslations',{}),'papers':papers}

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
