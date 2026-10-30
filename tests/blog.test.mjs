import test from 'node:test';
import assert from 'node:assert/strict';
import {readFileSync,existsSync} from 'node:fs';
import {safeLink,readingLink,categoryName,COLLECTIONS,filterCollection,readCollection,seriesLabel} from '../static/js/blog-core.mjs';
const catalog=JSON.parse(readFileSync(new URL('../data/blog-index.json',import.meta.url),'utf8'));

test('seventeen editorials retain reading order and all body text and images resolve',()=>{
  assert.deepEqual(catalog.articles.map(entry=>entry.articleId),[
    'scientific-model-start','scientific-model-capabilities','scientific-model-scores',
    'scientific-agent-data','agentic-science','scientific-foundation-models',
    'scientific-knowledge-modeling','s1-omni','biomatrix','logos',
    'scientific-foundation-pretraining','scientific-data-ai4s',
    'virtual-biotech-clinical-data','virtual-biotech-treatment-hypotheses','scientific-agent-harness','hle','autonomous-labs-1'
  ]);
  assert.deepEqual(Object.keys(catalog),['articles']);
  for(const entry of catalog.articles){
    const article=JSON.parse(readFileSync(new URL('../'+entry.dataUrl,import.meta.url),'utf8'));
    assert.ok(article.blocks.some(block=>block.type==='paragraph'&&block.text.length>30),entry.title);
    for(const image of article.blocks.filter(block=>block.type==='image')){
      assert.ok(existsSync(new URL('../'+image.src,import.meta.url)),image.src);
    }
  }
});

test('article links safely encode IDs and return to their card',()=>{
  assert.equal(readingLink('s1-omni'),'blog-article.html?id=s1-omni');
  assert.equal(readingLink('x&next=other'),'blog-article.html?id=x%26next%3Dother');
  assert.equal(safeLink('https://arxiv.org/abs/2508.21148'),'https://arxiv.org/abs/2508.21148');
  for(const url of ['javascript:alert(1)','//example.com','data:text/html,x','a\\b',' https://x.com'])assert.equal(safeLink(url),null);
});

test('every editorial has an English title and card summary without changing Chinese content',()=>{
  for(const entry of catalog.articles){
    assert.ok(entry.titleEn?.length>10,entry.articleId);
    assert.ok(entry.summaryEn?.length>30,entry.articleId);
    assert.ok(/[\u3400-\u9fff]/.test(entry.title),entry.articleId);
  }
  assert.equal(categoryName('foundation','en'),'Scientific foundation models');
  assert.equal(categoryName('foundation','zh'),'科学基础模型');
});

test('new editorials join their topics while empty collections remain ready for future content',()=>{
  assert.deepEqual(COLLECTIONS.map(group=>group.id),['reviews','agents','foundation','knowledge','data','evaluation','labs','math-physics','life','matter','earth','information','social']);
  assert.deepEqual(filterCollection(catalog.articles,'reviews').map(entry=>entry.seriesPart),[1,2,3,4]);
  assert.deepEqual(filterCollection(catalog.articles,'agents').map(entry=>entry.articleId),['agentic-science','virtual-biotech-clinical-data','virtual-biotech-treatment-hypotheses','scientific-agent-harness']);
  assert.deepEqual(filterCollection(catalog.articles,'foundation').map(entry=>entry.articleId),['scientific-foundation-models','s1-omni','biomatrix','logos','scientific-foundation-pretraining']);
  assert.deepEqual(filterCollection(catalog.articles,'knowledge').map(entry=>entry.articleId),['scientific-knowledge-modeling']);
  assert.equal(filterCollection(catalog.articles,'all').length,17);
  assert.equal(catalog.articles.length,17);
  assert.equal(seriesLabel(catalog.articles[2],'zh'),'精读（三）');
  assert.equal(seriesLabel(catalog.articles[2],'en'),'Part III');
  assert.deepEqual(filterCollection(catalog.articles,'data').map(entry=>entry.articleId),['scientific-data-ai4s']);
  assert.deepEqual(filterCollection(catalog.articles,'evaluation').map(entry=>entry.articleId),['hle']);
  assert.deepEqual(filterCollection(catalog.articles,'labs').map(entry=>entry.articleId),['autonomous-labs-1']);
  for(const id of ['math-physics','life','matter','earth','information','social']){
    assert.deepEqual(filterCollection(catalog.articles,id),[]);
    assert.equal(readCollection('?category='+id),id);
    assert.ok(COLLECTIONS.find(group=>group.id===id).en);
  }
});

test('category navigation survives article links and rejects unknown categories',()=>{
  const href=readingLink('logos','foundation');
  assert.equal(href,'blog-article.html?id=logos&category=foundation');
  assert.equal(readCollection('?category=foundation&lang=en'),'foundation');
  assert.equal(readCollection('?category=unknown'),'all');
  assert.equal(readCollection('?category=__proto__'),'all');
  assert.equal(readingLink('logos','javascript:alert(1)'),'blog-article.html?id=logos');
});
