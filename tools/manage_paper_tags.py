"""Search and register controlled paper tags, without network access."""
import argparse
from pathlib import Path
import yaml
from build_paper_index import ROOT,PaperDumper,load_tag_vocabulary,validate_tag_vocabulary,tag_key

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,default=ROOT)
    commands=parser.add_subparsers(dest='command',required=True)
    listing=commands.add_parser('list',help='List tags or search names, descriptions and aliases')
    listing.add_argument('--query',default='')
    adding=commands.add_parser('add',help='Validate and register a new canonical tag')
    adding.add_argument('--id',required=True)
    adding.add_argument('--en',required=True)
    adding.add_argument('--zh',required=True)
    adding.add_argument('--alias',action='append',default=[])
    adding.add_argument('--description',default='')
    adding.add_argument('--source',default='',help='Verified HTTPS concept page or vocabulary source')
    args=parser.parse_args()
    try:
        vocabulary=load_tag_vocabulary(args.root)
        if vocabulary is None:raise ValueError('Missing data/paper-tags.yml')
        data,_=vocabulary
        if args.command=='list':
            query=tag_key(args.query)
            matches=[t for t in data['tags'] if not query or query in tag_key(' '.join([
                t['id'],t['nameEn'],t['nameZh'],*t.get('aliases',[]),t.get('descriptionZh','')]))]
            print(f'{len(matches)} matches / {len(data["tags"])} registered tags')
            for tag in matches:print(f'{tag["id"]} | {tag["nameZh"]} | {tag["nameEn"]} | aliases: {", ".join(tag.get("aliases",[]))}')
            return
        tag={'id':args.id.strip(),'nameEn':args.en.strip(),'nameZh':args.zh.strip(),
             'aliases':[a.strip() for a in args.alias],'descriptionZh':args.description.strip()}
        if args.source:tag['sourceUrl']=args.source.strip()
        data['tags'].append(tag)
        validate_tag_vocabulary(data)
        output=args.root/'data/paper-tags.yml';temp=output.with_suffix('.yml.tmp')
        temp.write_text(yaml.dump(data,Dumper=PaperDumper,allow_unicode=True,sort_keys=False,width=100000),encoding='utf-8')
        temp.replace(output)
        print(f'Registered {tag["id"]}: {tag["nameZh"]} / {tag["nameEn"]}; commit data/paper-tags.yml with the paper.')
    except (ValueError,OSError) as exc:parser.exit(1,f'Tag registration failed: {exc}\n')

if __name__=='__main__':main()
