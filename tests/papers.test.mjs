import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('published catalog has bilingual Markdown sections and traceable full-paper ClimaX notes', async () => {
  const data=JSON.parse(await readFile(new URL('../data/papers-index.json',import.meta.url),'utf8'));
  assert.equal(data.schemaVersion,1);
  const details=await Promise.all(data.papers.map(p=>readFile(new URL('../'+p.dataUrl,import.meta.url),'utf8').then(JSON.parse)));
  for(const p of details) {
    assert.equal(typeof p.content.zh.html,'string');
    assert.equal(typeof p.content.en.html,'string');
    for(const content of Object.values(p.content)) {
      assert.equal(new Set(content.toc.map(n=>n.id)).size,content.toc.length);
      for(const heading of content.toc) assert.ok(content.html.includes(`id="${heading.id}"`));
    }
  }
  const climax=details.find(p=>p.id==='5CZyPMgjUu');
  assert.equal(climax.content.zh.toc.length,8);
  assert.equal(climax.content.en.toc.length,8);
  assert.ok(climax.notesMeta.sources.some(s=>s.url==='https://proceedings.mlr.press/v202/nguyen23a/nguyen23a.pdf'));
  assert.match(climax.content.zh.html,/1\.70/);
  assert.match(climax.content.zh.html,/1\.79/);
  assert.match(climax.content.zh.html,/<img[^>]+src="data\/papers\/climax\/images\/workflow.svg"/);
});

test('tag translations change labels while preserving stable tag identifiers', async () => {
  const { tagLabel, filterPapers } = await import('../static/js/papers-core.mjs');
  const translations = {Climate:'气候',Pretraining:'预训练'};
  assert.equal(tagLabel('Climate','zh',translations),'气候');
  assert.equal(tagLabel('Climate','en',translations),'Climate');
  assert.equal(tagLabel('Unknown','zh',translations),'Unknown');
  assert.equal(filterPapers([{id:'a',title:'A',tags:['Climate']}],{tag:'Climate'}).length,1);
});

test('controlled tag IDs display bilingual labels and old alias links resolve to the same ID', async () => {
  const {tagLabel,resolveTag,filterPapers}=await import('../static/js/papers-core.mjs');
  const vocabulary=[{id:'climate',nameEn:'Climate',nameZh:'气候',aliases:['气候科学']}];
  assert.equal(tagLabel('climate','zh',{climate:'气候'},{climate:'Climate'}),'气候');
  assert.equal(tagLabel('climate','en',{climate:'气候'},{climate:'Climate'}),'Climate');
  for(const input of ['Climate','climate','气候科学',' Ｃｌｉｍａｔｅ ']) {
    assert.equal(resolveTag(input,vocabulary),'climate');
    assert.equal(filterPapers([{id:'a',title:'A',tags:['climate']}],{tag:resolveTag(input,vocabulary)}).length,1);
  }
});

test('catalog uses abstracts only and never substitutes an AI overview', async () => {
  const { cardAbstract } = await import('../static/js/papers-core.mjs');
  const paper = {abstract:'Original abstract',summaryZh:'中文概述'};
  assert.deepEqual(cardAbstract(paper,'zh'),{text:'Original abstract',isAbstract:true});
  assert.deepEqual(cardAbstract(paper,'en'),{text:'Original abstract',isAbstract:true});
  assert.deepEqual(cardAbstract({summaryZh:'只有概述',summaryEn:'Only a summary'},'zh'),{text:'',isAbstract:false});
  assert.deepEqual(cardAbstract({...paper,abstractZh:'完整中文摘要'},'zh'),{text:'完整中文摘要',isAbstract:true});
});

test('exact tags count papers once, search affiliations and preserve tag context', async () => {
  const { paperTags, tagCounts, filterPapers, readingUrl, listReturnUrl } = await import('../static/js/papers-core.mjs');
  const papers = [
    {id:'a',title:'Climate',tags:['Pretraining','Climate','Climate'],topics:['Pretraining'],affiliations:['Microsoft Research'],keywords:['Weather']},
    {id:'b',title:'Agent',topics:['Pretraining'],keywords:['Climate']},
  ];
  assert.deepEqual(paperTags(papers[0]), ['Pretraining','Climate']);
  assert.equal(tagCounts(papers).find(([tag])=>tag==='Pretraining')[1],2);
  assert.deepEqual(filterPapers(papers,{tag:'Climate'}).map(p=>p.id),['a']);
  assert.deepEqual(filterPapers(papers,{tag:'Climate',query:'microsoft'}).map(p=>p.id),['a']);
  const url = new URL(readingUrl('a','?tag=Climate'),'https://example.org/');
  assert.equal(new URL(listReturnUrl(url.searchParams.get('from')),'https://example.org/').searchParams.get('tag'),'Climate');
});

test('reading links encode paper IDs and restore only local list filters', async () => {
  const { readingUrl, listReturnUrl } = await import('../static/js/papers-core.mjs');
  const context = '?discipline=weather&q=气候&theme=dark&paper=old';
  const link = new URL(readingUrl('a&b', context), 'https://example.org/');
  assert.equal(link.pathname, '/paper.html');
  assert.equal(link.searchParams.get('id'), 'a&b');
  const back = listReturnUrl(link.searchParams.get('from'));
  assert.equal(new URL(back, 'https://example.org/').searchParams.get('discipline'), 'weather');
  assert.equal(new URL(back, 'https://example.org/').searchParams.has('paper'), false);
  assert.equal(listReturnUrl('https://evil.example/'), 'papers.html');
  assert.equal(listReturnUrl('//evil.example/'), 'papers.html');
});

test('search combines bilingual text, topic and saved filters', async () => {
  const { filterPapers } = await import('../static/js/papers-core.mjs');
  const papers = [
    { id: 'a', title: 'Reflexion', titleZh: '反思智能体', summaryZh: '语言反馈', authors: ['Noah Shinn'], topics: ['Agents'], published: '2023-03-20' },
    { id: 'b', title: 'Biology', topics: ['Biology'], published: '2024-01-01' },
  ];
  assert.deepEqual(filterPapers(papers, { query: '反思', topic: 'Agents' }).map(p => p.id), ['a']);
  assert.equal(filterPapers(papers, { query: 'Noah', topic: 'Biology' }).length, 0);
  assert.deepEqual(filterPapers(papers, { savedOnly: true, saved: ['b'] }).map(p => p.id), ['b']);
  assert.deepEqual(filterPapers(papers, {}).map(p => p.id), ['b', 'a']);
});

test('disciplines support cross-disciplinary papers and combine with venue, subfield and decision', async () => {
  const { filterPapers } = await import('../static/js/papers-core.mjs');
  const papers = [
    {id:'a', title:'Weather', disciplines:['weather','physics'], subfield:'Forecasting', venue:'ICLR 2024', year:'2024', decision:'Poster', keywords:['climate'], abstract:'Atmospheric foundation model'},
    {id:'b', title:'Protein', disciplines:['biology'], subfield:'Proteins', venue:'ICLR 2025', year:'2025', decision:'Oral'},
  ];
  assert.deepEqual(filterPapers(papers, {discipline:'physics', subfield:'Forecasting', venue:'ICLR 2024', year:'2024', decision:'Poster', query:'climate atmospheric'}).map(p => p.id), ['a']);
  assert.equal(filterPapers(papers, {discipline:'biology', venue:'ICLR 2024'}).length, 0);
  assert.equal(filterPapers(papers, {discipline:'weather', decision:'Oral'}).length, 0);
  assert.equal(filterPapers(papers, {year:'2023'}).length, 0);
});
