"""Import a supplied course news document and its original images as static data."""
import argparse
from datetime import date
import hashlib
import json
from pathlib import Path
import posixpath
import re
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parents[1]
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
    'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
    'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}


def import_document(source,article_id,published,root=ROOT):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*',article_id):
        raise ValueError('Invalid news identifier')
    date.fromisoformat(published)
    root=Path(root);source=Path(source)
    with ZipFile(source) as archive:
        paragraphs=ET.fromstring(archive.read('word/document.xml')).findall('w:body/w:p',NS)
        relations={item.attrib['Id']:item.attrib for item in ET.fromstring(archive.read('word/_rels/document.xml.rels'))}
        text=lambda element:''.join(item.text or '' for item in element.findall('.//w:t',NS)).strip()
        if len(paragraphs)<4:raise ValueError('News document needs title, byline, course and body')
        blocks=[];number=None
        asset_dir=root/'data/news/assets'/article_id
        asset_dir.mkdir(parents=True,exist_ok=True)
        for paragraph in paragraphs[3:]:
            value=text(paragraph)
            images=[]
            for image in paragraph.findall('.//a:blip',NS):
                relation=relations.get(image.get('{'+NS['r']+'}embed'),{})
                if not relation or relation.get('TargetMode')=='External':continue
                target=posixpath.normpath('word/'+relation['Target'])
                if not target.startswith('word/media/') or Path(target).suffix.lower() not in {'.png','.jpg','.jpeg','.webp'}:
                    raise ValueError('Unexpected news image relationship')
                name=Path(target).name
                (asset_dir/name).write_bytes(archive.read(target))
                images.append(dict(src=f'data/news/assets/{article_id}/{name}',caption=''))
            if images:
                blocks.append(dict(type='gallery',images=images) if len(images)>1 else dict(type='image',**images[0]))
            if not value:continue
            if re.fullmatch(r'\d{2}',value):number=value;continue
            if number:
                blocks.append(dict(type='heading',number=number,text=value,id='section-'+number));number=None
            elif blocks and blocks[-1]['type']=='image' and not blocks[-1]['caption'] and re.match(r'^图\s*\d+',value):
                blocks[-1]['caption']=value
            else:blocks.append(dict(type='paragraph',text=value))
        if number:raise ValueError('Section marker has no heading')
        article=dict(id=article_id,title=text(paragraphs[0]),source=text(paragraphs[1]),subtitle=text(paragraphs[2]),date=published,
                     sourceSha256=hashlib.sha256(source.read_bytes()).hexdigest(),blocks=blocks)
        target=root/'data/news/articles'/f'{article_id}.json';target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps(article,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
        return article


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path);parser.add_argument('--id',required=True);parser.add_argument('--date',required=True)
    args=parser.parse_args();article=import_document(args.source,args.id,args.date)
    print(f'Imported {article["id"]}: {len(article["blocks"])} content blocks')
