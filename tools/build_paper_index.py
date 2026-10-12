"""Validate per-paper JSON files and generate a small static catalog. No dependencies."""
import argparse
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import re
import shutil
from urllib.parse import urlparse, unquote

ROOT=Path(__file__).resolve().parents[1]
INDEX_FIELDS=('id','title','titleZh','authors','affiliations','published','dateType','venue','year',
              'disciplines','subfield','keywords','tags','topics','abstract','abstractZh',
              'summaryZh','summaryEn','paperUrl','pdfUrl','forumUrl','codeUrl','sample')

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

def build_index(folder,schema_path,config,root):
    schema=read_json(schema_path)
    validate(config.get('tagTranslations',{}),schema['properties']['tagTranslations'],schema,'tagTranslations')
    papers=[]; ids=set(); filenames=set()
    for file in sorted(folder.glob('*.json')):
        if file.name.endswith('.local.json'): raise ValueError(f'Paper filename uses reserved .local.json suffix: {file.name}')
        if file.is_symlink(): raise ValueError(f'Symlink not allowed for paper: {file.name}')
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*\.json',file.name): raise ValueError(f'Invalid paper filename: {file.name}')
        if file.name.lower() in filenames: raise ValueError(f'Duplicate filename: {file.name}')
        filenames.add(file.name.lower())
        paper=read_json(file);validate_paper(paper,schema,root,file.name)
        if paper['id'] in ids: raise ValueError(f'Duplicate paper id: {paper["id"]}')
        ids.add(paper['id'])
        item={key:paper[key] for key in INDEX_FIELDS if key in paper}
        item.update(dataUrl='data/papers/'+file.name,hasNotes=bool(paper.get('notes')))
        papers.append(item)
    if not papers: raise ValueError('No paper JSON files found')
    return {'schemaVersion':1,'updated':datetime.now(timezone(timedelta(hours=8))).date().isoformat(),
            'tagTranslations':config.get('tagTranslations',{}),'papers':papers}

def write_index(root=ROOT,schema_path=None):
    root=Path(root)
    config=read_json(root/'data/papers-config.json') if (root/'data/papers-config.json').exists() else {}
    data=build_index(root/'data/papers',schema_path or root/'data/papers.schema.json',config,root)
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
