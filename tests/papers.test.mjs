import test from 'node:test';
import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

test('missing imported resource metadata is unknown rather than confirmed absent', async () => {
  const {filterPapers,paginatePapers}=await import('../static/js/papers-core.mjs');
  const papers=[{id:'unknown',title:'Imported',imported:true,codeAvailability:'unknown'}, {id:'no',title:'Known absent',codeAvailability:'none'}];
  assert.deepEqual(filterPapers(papers,{github:'no'}).map(p=>p.id),['no']);
  assert.deepEqual(filterPapers(papers,{github:'unknown'}).map(p=>p.id),['unknown']);
  assert.deepEqual(filterPapers(papers,{arxiv:'unknown'}).map(p=>p.id),['unknown']);
  const page=paginatePapers(Array.from({length:101},(_,id)=>({id})),3,48);
  assert.equal(page.pages,3);assert.equal(page.items.length,5);assert.equal(page.items[0].id,96);
  assert.equal(paginatePapers([],20,48).page,1);
});

test('legacy category links resolve and related papers share actual tags', async () => {
  const {resolveDiscipline,relatedPapers}=await import('../static/js/papers-core.mjs');
  assert.equal(resolveDiscipline('weather'),'earth-space-sciences');
  assert.equal(resolveDiscipline('chemistry'),'matter-sciences');
  const current={id:'a',tags:['climate','pretraining']};
  assert.deepEqual(relatedPapers(current,[current,{id:'b',tags:['pretraining']},{id:'c',tags:['climate','pretraining']},{id:'d',tags:['agents']}]).map(p=>p.id),['c','b']);
});

test('resource facets distinguish linked arXiv from verified matches and exact GitHub hosts', async () => {
  const {filterPapers}=await import('../static/js/papers-core.mjs');
  const entries=[
    {id:'a',title:'A',paperUrl:'https://arxiv.org/abs/2601.00001',arxivStatus:'verified',codeUrl:'https://github.com/org/a',githubSource:'page'},
    {id:'b',title:'B',pdfUrl:'https://arxiv.org/pdf/2601.00002',arxivStatus:'',codeUrl:'https://github.com/org/b'},
    {id:'c',title:'C',arxivStatus:'probable',arxivUrl:'https://arxiv.org/abs/2601.00003'},
    {id:'d',title:'D',paperUrl:'https://example.org/?next=arxiv.org/abs/1',codeUrl:'https://github.com.evil.example/org/d'},
  ];
  assert.deepEqual(filterPapers(entries,{arxiv:'yes'}).map(p=>p.id),['a','b','c']);
  assert.deepEqual(filterPapers(entries,{arxiv:'strict'}).map(p=>p.id),['a']);
  assert.deepEqual(filterPapers(entries,{arxiv:'review'}).map(p=>p.id),['c']);
  assert.deepEqual(filterPapers(entries,{arxiv:'no'}).map(p=>p.id),['d']);
  assert.deepEqual(filterPapers(entries,{github:'yes'}).map(p=>p.id),['a','b']);
  assert.deepEqual(filterPapers(entries,{github:'page'}).map(p=>p.id),['a']);
  assert.deepEqual(filterPapers(entries,{github:'no'}).map(p=>p.id),['c','d']);
});

test('session and room facets use OR within a group and AND across groups', async () => {
  const {filterPapers,facetCounts}=await import('../static/js/papers-core.mjs');
  const entries=[{id:'a',title:'A',session:'Poster Session 1',room:'Room A'}, {id:'b',title:'B',session:'Poster Session 2',room:'Room B'}, {id:'c',title:'C'}];
  assert.deepEqual(filterPapers(entries,{sessions:['Poster Session 1','Poster Session 2'],rooms:['Room A']}).map(p=>p.id),['a']);
  assert.deepEqual(filterPapers(entries,{sessions:['__unlisted__']}).map(p=>p.id),['c']);
  assert.deepEqual(facetCounts(entries,{sessions:['Poster Session 1'],rooms:['Room B']},'sessions',['Poster Session 1','Poster Session 2','__unlisted__']),[['Poster Session 1',0],['Poster Session 2',1],['__unlisted__',0]]);
  assert.deepEqual(facetCounts(entries,{arxiv:'strict',sessions:['Poster Session 1']},'arxiv',['all','yes','strict','review','no']),[['all',1],['yes',0],['strict',0],['review',0],['no',1]]);
});

test('resource and venue facet selections survive detail navigation', async () => {
  const {readingUrl,detailReturnUrl}=await import('../static/js/papers-core.mjs');
  const link=new URL(readingUrl('one','?arxiv=strict&github=page&sessions=Poster+Session+1%7CPoster+Session+2&rooms=Room+A'),'https://example.org/');
  const back=new URL(detailReturnUrl(link.search),'https://example.org/');
  assert.equal(back.searchParams.get('arxiv'),'strict');assert.equal(back.searchParams.get('github'),'page');
  assert.equal(back.searchParams.get('sessions'),'Poster Session 1|Poster Session 2');assert.equal(back.searchParams.get('rooms'),'Room A');
});

test('catalog search supports exact phrases and a selected search field', async () => {
  const {filterPapers}=await import('../static/js/papers-core.mjs');
  const entries=[{id:'a',title:'Graph neural networks',authors:['Alice'],abstract:'Molecular science'}, {id:'b',title:'Graph and neural methods',authors:['Bob'],abstract:'Alice studies molecular science'}];
  assert.deepEqual(filterPapers(entries,{query:'"graph neural"'}).map(p=>p.id),['a']);
  assert.deepEqual(filterPapers(entries,{query:'Alice',searchField:'authors'}).map(p=>p.id),['a']);
  assert.equal(filterPapers(entries,{query:'Alice',searchField:'title'}).length,0);
});

test('multiple disciplines support any, all, and primary-category matching', async () => {
  const {filterPapers}=await import('../static/js/papers-core.mjs');
  const entries=[{id:'a',title:'A',disciplines:['weather','physics']},{id:'b',title:'B',disciplines:['physics']},{id:'c',title:'C',disciplines:['biology']}];
  assert.deepEqual(filterPapers(entries,{disciplines:['weather','physics'],matchMode:'any'}).map(p=>p.id),['a','b']);
  assert.deepEqual(filterPapers(entries,{disciplines:['weather','physics'],matchMode:'all'}).map(p=>p.id),['a']);
  assert.deepEqual(filterPapers(entries,{disciplines:['physics'],primaryOnly:true}).map(p=>p.id),['b']);
});

test('catalog sorts by publication date and title without changing input order', async () => {
  const {sortPapers}=await import('../static/js/papers-core.mjs');
  const entries=[{id:'a',title:'Zebra',published:'2026-01-01'},{id:'b',title:'Alpha',published:'2023-01-01'},{id:'c',title:'Beta',published:''}];
  assert.deepEqual(sortPapers(entries,'title').map(p=>p.id),['b','c','a']);
  assert.deepEqual(sortPapers(entries,'oldest').map(p=>p.id),['b','a','c']);
  assert.deepEqual(sortPapers(entries,'default').map(p=>p.id),['a','b','c']);
  assert.deepEqual(entries.map(p=>p.id),['a','b','c']);
});

test('date browsing uses calendar periods and excludes papers without a publication date', async () => {
  const { filterPapers } = await import('../static/js/papers-core.mjs');
  const papers = [
    {id:'sun',title:'Sunday',published:'2026-10-11'},
    {id:'mon',title:'Monday',published:'2026-10-12'},
    {id:'wed',title:'Wednesday',published:'2026-10-14'},
    {id:'next',title:'Next week',published:'2026-10-19'},
    {id:'unknown',title:'Unknown',published:''},
  ];
  assert.deepEqual(filterPapers(papers,{period:'day',date:'2026-10-14'}).map(p=>p.id),['wed']);
  assert.deepEqual(filterPapers(papers,{period:'week',date:'2026-10-14'}).map(p=>p.id),['wed','mon']);
  assert.deepEqual(filterPapers(papers,{period:'month',date:'2026-10-14'}).map(p=>p.id),['next','wed','mon','sun']);
  assert.equal(filterPapers(papers,{period:'all',date:'2026-10-14'}).length,5);
});

test('returning from a paper retains date browsing and pagination', async () => {
  const { readingUrl, listReturnUrl } = await import('../static/js/papers-core.mjs');
  const link=new URL(readingUrl('paper','?period=week&date=2026-10-14&page=2'),'https://example.org/');
  const back=new URL(listReturnUrl(link.searchParams.get('from')),'https://example.org/');
  assert.equal(back.searchParams.get('period'),'week');
  assert.equal(back.searchParams.get('date'),'2026-10-14');
  assert.equal(back.searchParams.get('page'),'2');
});

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

test('detail navigation keeps current appearance when catalog context has old preferences', async () => {
  const {detailReturnUrl,readingUrl}=await import('../static/js/papers-core.mjs');
  const search='?id=one&from='+encodeURIComponent('?discipline=weather&lang=en&theme=dark');
  assert.equal(detailReturnUrl(search),'papers.html?discipline=weather');
  const context=new URL(detailReturnUrl(search),'https://example.org/').search;
  const next=new URL(readingUrl('two',context),'https://example.org/');
  assert.equal(next.searchParams.has('lang'),false);
  assert.equal(next.searchParams.has('theme'),false);
  assert.equal(next.searchParams.get('from'),'?discipline=weather');
  assert.equal(detailReturnUrl('?lang=en&theme=dark'),'papers.html?lang=en&theme=dark');
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
