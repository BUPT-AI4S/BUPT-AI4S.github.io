"""Import a local editorial DOCX as structured, static blog content (no HTML execution)."""
import argparse
import json
import posixpath
from pathlib import Path
import re
from zipfile import ZipFile
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main',
      'a':'http://schemas.openxmlformats.org/drawingml/2006/main',
      'r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}

def text(element):
    return ''.join(node.text or '' for node in element.findall('.//w:t', NS)).strip()

def import_document(source, article_id, kind, title=None, root=ROOT):
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', article_id):
        raise ValueError('Use a lowercase article ID containing letters, digits and hyphens.')
    with ZipFile(source) as archive:
        body = ET.fromstring(archive.read('word/document.xml')).find('w:body', NS)
        relationships = {r.attrib['Id']:r.attrib for r in ET.fromstring(archive.read('word/_rels/document.xml.rels'))}
        blocks = []
        paragraphs = body.findall('w:p', NS)
        article_title = title or text(paragraphs[0])
        styles = {s.get('{'+NS['w']+'}styleId'):s.find('w:name',NS).get('{'+NS['w']+'}val','').lower()
                  for s in ET.fromstring(archive.read('word/styles.xml')).findall('w:style',NS) if s.find('w:name',NS) is not None}
        # A research-paper explainer has an explicit subtitle followed by its overview.
        # Series posts start directly with substantive prose; keep that prose in the body.
        has_subtitle = kind=='book' or (len(paragraphs)>2 and text(paragraphs[2])=='先看全貌')
        subtitle = text(paragraphs[1]) if has_subtitle else ''
        asset_dir = root/'data/blog/assets'/article_id
        asset_dir.mkdir(parents=True, exist_ok=True)
        for index, element in enumerate(body):
            if element.tag == '{'+NS['w']+'}tbl':
                blocks.append({'type':'table','rows':[[text(cell) for cell in row.findall('w:tc',NS)] for row in element.findall('w:tr',NS)]})
                continue
            if element.tag != '{'+NS['w']+'}p':
                continue
            content = text(element)
            # The first two paragraphs are displayed by the article header.
            if element is paragraphs[0] or (has_subtitle and element is paragraphs[1]):
                continue
            if content == 'BUPT Reasoning' or (index < 4 and content == article_title):
                continue
            for image in element.findall('.//a:blip',NS):
                relation = relationships.get(image.get('{'+NS['r']+'}embed'))
                if not relation or relation.get('TargetMode') == 'External':
                    continue
                target = posixpath.normpath('word/'+relation['Target'])
                if not target.startswith('word/media/'):
                    raise ValueError('Unexpected image relationship')
                name = Path(target).name
                if Path(name).suffix.lower() not in {'.png','.jpg','.jpeg','.gif','.webp'}:
                    continue
                (asset_dir/name).write_bytes(archive.read(target))
                blocks.append({'type':'image','src':f'data/blog/assets/{article_id}/{name}','caption':''})
            if not content:
                continue
            if blocks and blocks[-1]['type']=='image' and (re.match(r'^(图\s*\d+|原论文图\s*\d+|全文导览)',content) or content.startswith('官方书影')):
                blocks[-1]['caption']=content
                continue
            style = element.find('w:pPr/w:pStyle',NS)
            style_id = style.get('{'+NS['w']+'}val') if style is not None else ''
            style_name=styles.get(style_id,'')
            if style_name in {'heading 1','heading 2'} or re.match(r'^0[1-9][^ /]',content):
                blocks.append({'type':'heading','level':2,'text':content})
            elif style_name=='heading 3' or re.match(r'^\d+\.\d+',content):
                blocks.append({'type':'heading','level':3,'text':content})
            elif content in {'先看全貌','本篇论文','研究要点','书目与阅读注释','论文与阅读注释','论文概览'}:
                blocks.append({'type':'heading','level':2,'text':content})
            else:
                blocks.append({'type':'paragraph','text':content})
        result={'id':article_id,'title':article_title,'subtitle':subtitle,'byline':'BUPT Reasoning · AI4S 专栏','blocks':blocks}
        output=root/'data/blog/articles'/f'{article_id}.json'
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        return output, result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path)
    parser.add_argument('--id',required=True)
    parser.add_argument('--kind',choices=['article','book'],default='article')
    parser.add_argument('--title')
    args=parser.parse_args()
    output,result=import_document(args.source,args.id,args.kind,args.title)
    print(f'{output.name}: {len(result["blocks"])} blocks imported')
