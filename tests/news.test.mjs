import test from 'node:test';
import assert from 'node:assert/strict';
import {filterNews,articleUrl,findArticle} from '../static/js/news-core.mjs';

const entries=[{id:'course-dialogue',title:'与大咖对话',titleEn:'Dialogue with researchers',summary:'科学智能课程',source:'BUPT Reasoning',date:'2026-10-23'}];
test('news search handles Chinese, English and empty queries without mutating the source',()=>{
 assert.deepEqual(filterNews(entries,' 大咖 '),entries);
 assert.deepEqual(filterNews(entries,'RESEARCHERS'),entries);
 assert.deepEqual(filterNews(entries,'不存在'),[]);
 assert.deepEqual(filterNews(entries,''),entries);
 assert.equal(entries.length,1);
});
test('article links preserve search while identifiers resolve only published entries',()=>{
 assert.equal(articleUrl('course-dialogue','科学'), 'news-article.html?id=course-dialogue&q=%E7%A7%91%E5%AD%A6');
 assert.equal(findArticle(entries,'../private'),undefined);
 assert.equal(findArticle(entries,'missing'),undefined);
 assert.equal(findArticle(entries,'course-dialogue'),entries[0]);
});
