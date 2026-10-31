import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]

class PaperTagTests(unittest.TestCase):
    def module(self):
        spec=importlib.util.spec_from_file_location('tags_build',ROOT/'tools/build_paper_index.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        return module

    def setup_site(self,root,values):
        folder=root/'data/papers/demo';folder.mkdir(parents=True)
        (root/'data/paper-tags.yml').write_text('schemaVersion: 1\ntags:\n  - id: climate\n    nameEn: Climate\n    nameZh: 气候\n    aliases: [气候科学]\n',encoding='utf-8')
        body='---\nid: demo\ntitle: Demo\nauthors: []\ntags: '+json.dumps(values,ensure_ascii=False)+'\n---\n\n## 方法\n\nText'
        (folder/'paper.md').write_text(body,encoding='utf-8')

    def test_ids_names_and_aliases_share_one_canonical_tag(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_site(root,['climate','Climate','气候','气候科学',' CLIMATE '])
            index=self.module().write_index(root,ROOT/'data/papers.schema.json')
            self.assertEqual(index['papers'][0]['tags'],['climate'])
            self.assertEqual(index['papers'][0]['tagIds'],['climate'])
            self.assertEqual(index['tagTranslations'],{'climate':'气候'})
            self.assertEqual(index['tagLabelsEn'],{'climate':'Climate'})
            detail=json.loads((root/index['papers'][0]['dataUrl']).read_text(encoding='utf-8'))
            self.assertEqual(detail['tags'],['climate'])

    def test_unknown_tags_block_build_without_changing_the_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_site(root,['Climat'])
            output=root/'data/papers-index.json';output.write_text('previous')
            with self.assertRaisesRegex(ValueError,'Unknown tag.*Climate'):
                self.module().write_index(root,ROOT/'data/papers.schema.json')
            self.assertEqual(output.read_text(),'previous')

    def test_add_command_checks_collisions_before_writing_the_vocabulary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_site(root,['climate'])
            command=[sys.executable,str(ROOT/'tools/manage_paper_tags.py'),'--root',str(root)]
            result=subprocess.run(command+['add','--id','llm','--en','Large language models','--zh','大语言模型','--alias','LLMs'],capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            registry=root/'data/paper-tags.yml';previous=registry.read_bytes()
            result=subprocess.run(command+['add','--id','duplicate','--en','Another','--zh','气候'],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertEqual(registry.read_bytes(),previous)
            text=(root/'data/papers/demo/paper.md').read_text(encoding='utf-8').replace('tags: ["climate"]','tags: [LLMs]')
            (root/'data/papers/demo/paper.md').write_text(text,encoding='utf-8')
            index=self.module().write_index(root,ROOT/'data/papers.schema.json')
            self.assertEqual(index['papers'][0]['tags'],['llm'])

    def test_missing_vocabulary_does_not_disable_tag_validation(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_site(root,['unknown'])
            (root/'data/paper-tags.yml').unlink()
            with self.assertRaisesRegex(ValueError,'Missing.*paper-tags.yml'):
                self.module().write_index(root,ROOT/'data/papers.schema.json')

    def test_legacy_json_details_use_the_same_normalized_ids_as_the_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_site(root,[])
            (root/'data/papers/demo/paper.md').unlink();(root/'data/papers/demo').rmdir()
            (root/'data/papers/demo.json').write_text(json.dumps({'id':'demo','title':'Demo','authors':[],'tags':['气候科学']}),encoding='utf-8')
            index=self.module().write_index(root,ROOT/'data/papers.schema.json')
            entry=index['papers'][0]
            detail=json.loads((root/entry['dataUrl']).read_text(encoding='utf-8'))
            self.assertEqual(detail['tags'],['climate'])
            self.assertEqual(entry['sourceUrl'],'data/papers/demo.json')

    def test_imported_keywords_join_existing_tags_and_generated_details(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_site(root,['climate'])
            folder=root/'data/imported';folder.mkdir()
            rows=[{'id':'a','title':'First','authors':[],'keywords':[' CLIMATE ','Protein Design; Self-supervised Learning','protein design']},
                  {'id':'b','title':'Second','authors':[],'keywords':['self supervised learning','Protein Design']},
                  {'id':'c','title':'No keywords','authors':[]}]
            (folder/'ai4s-2026.json').write_text(json.dumps({'schemaVersion':1,'papers':rows}),encoding='utf-8')
            index=self.module().write_index(root,ROOT/'data/papers.schema.json')
            first,second,empty=index['papers'][1:]
            self.assertEqual(len(first['tags']),3)
            self.assertIn('climate',first['tags'])
            self.assertEqual(set(first['tags'])-{'climate'},set(second['tags']))
            self.assertEqual(empty.get('tags',[]),[])
            self.assertEqual(first['tagIds'],first['tags'])
            detail=json.loads((root/first['dataUrl']).read_text(encoding='utf-8'))
            self.assertEqual(detail['tags'],first['tags'])
            self.assertEqual(detail['keywords'],rows[0]['keywords'])
            names={t['nameEn'] for t in index['tagVocabulary']}
            self.assertEqual(len(names),3)
            self.assertIn('Protein Design',names)
            # Stable IDs must survive a source-record reorder.
            (folder/'ai4s-2026.json').write_text(json.dumps({'schemaVersion':1,'papers':rows[::-1]}),encoding='utf-8')
            reordered=self.module().write_index(root,ROOT/'data/papers.schema.json')
            self.assertEqual({p['id']:p.get('tags',[]) for p in index['papers']},{p['id']:p.get('tags',[]) for p in reordered['papers']})

    def test_translated_keyword_vocabulary_merges_synonyms_and_keeps_old_ids_as_aliases(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);self.setup_site(root,['climate'])
            folder=root/'data/imported';folder.mkdir()
            row={'id':'llm-paper','title':'LLMs','authors':[],'keywords':['LLM','Large language models']}
            (folder/'ai4s-2026.json').write_text(json.dumps({'schemaVersion':1,'papers':[row]}),encoding='utf-8')
            registry={'schemaVersion':1,'tags':[{'id':'keyword-canonical','nameEn':'Large language models','nameZh':'大语言模型','aliases':['LLM','keyword-previous-id']}]}
            (root/'data/keyword-tag-vocabulary.json').write_text(json.dumps(registry),encoding='utf-8')
            index=self.module().write_index(root,ROOT/'data/papers.schema.json')
            entry=index['papers'][1]
            self.assertEqual(entry['tags'],['keyword-canonical'])
            self.assertEqual(index['tagTranslations']['keyword-canonical'],'大语言模型')
            tag=next(t for t in index['tagVocabulary'] if t['id']=='keyword-canonical')
            self.assertIn('keyword-previous-id',tag['aliases'])
            # New source terms cannot silently reintroduce untranslated labels.
            row['keywords'].append('Untranslated new term')
            (folder/'ai4s-2026.json').write_text(json.dumps({'schemaVersion':1,'papers':[row]}),encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'Untranslated.*Untranslated new term'):
                self.module().write_index(root,ROOT/'data/papers.schema.json')

if __name__=='__main__':unittest.main()
