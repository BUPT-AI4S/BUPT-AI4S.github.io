import test from 'node:test';
import assert from 'node:assert/strict';
import * as core from '../static/js/blog-core.mjs';

const articles=[
  {articleId:'protein',collection:'foundation',title:'蛋白质基础模型',titleEn:'Protein Foundation Models',summary:'利用预训练学习分子表示',keywords:['结构预测']},
  {articleId:'molecule',collection:'foundation',title:'分子模型',summaryEn:'Molecular representation learning',keywords:['化学']},
  {articleId:'clinical',collection:'agents',title:'临床研究',summary:'智能体整合临床证据',keywords:['治疗假设']}
];
test('blog search matches titles, summaries and keywords across Chinese and English',()=>{
  assert.equal(typeof core.filterBlogArticles,'function');
  for(const [query,want] of [['蛋白 预训练',['protein']],['ＰＲＯＴＥＩＮ',['protein']],['MOLECULAR',['molecule']],['治疗假设',['clinical']],['不存在',[]]]){
    assert.deepEqual(core.filterBlogArticles(articles,'all',query).map(a=>a.articleId),want);
  }
});
test('search combines with the selected category and preserves article order and source data',()=>{
  assert.equal(typeof core.filterBlogArticles,'function');
  const original=structuredClone(articles);
  assert.deepEqual(core.filterBlogArticles(articles,'foundation','临床'),[]);
  assert.deepEqual(core.filterBlogArticles(articles,'foundation','  ').map(a=>a.articleId),['protein','molecule']);
  assert.deepEqual(core.filterBlogArticles(articles,'all','模型').map(a=>a.articleId),['protein','molecule']);
  assert.deepEqual(articles,original);
});
test('article links retain search context and encode it without changing existing links',()=>{
  assert.equal(core.readingLink('protein','foundation','蛋白 预训练'),'blog-article.html?id=protein&category=foundation&q=%E8%9B%8B%E7%99%BD%20%E9%A2%84%E8%AE%AD%E7%BB%83');
  assert.equal(core.readingLink('protein','all','  '),'blog-article.html?id=protein');
  assert.equal(core.readingLink('protein','all','x&next=y'),'blog-article.html?id=protein&q=x%26next%3Dy');
});
