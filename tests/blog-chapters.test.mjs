import test from 'node:test';
import assert from 'node:assert/strict';
import * as core from '../static/js/blog-core.mjs';

test('chapters preserve every block and keep subsections with their parent chapter',()=>{
  assert.equal(typeof core.splitChapters,'function');
  const blocks=[
    {type:'paragraph',text:'Opening evidence'},
    {type:'image',src:'intro.png'},
    {type:'heading',level:2,text:'First chapter'},
    {type:'table',rows:[['Evidence','Result']]},
    {type:'heading',level:3,text:'A subsection'},
    {type:'paragraph',text:'Subsection evidence'},
    {type:'heading',level:2,text:'Second chapter'},
    {type:'paragraph',text:'Conclusion'}
  ];
  const original=structuredClone(blocks),chapters=core.splitChapters(blocks);
  assert.deepEqual(chapters.map(chapter=>chapter.id),['intro','part-1','part-3']);
  assert.deepEqual(chapters.map(chapter=>chapter.blocks.length),[2,4,2]);
  assert.deepEqual(chapters.flatMap(chapter=>chapter.blocks).map(({headingId,...block})=>block),blocks);
  assert.deepEqual(blocks,original);
});

test('documents starting with a heading have no empty introduction; plain documents stay readable',()=>{
  assert.equal(typeof core.splitChapters,'function');
  assert.equal(core.splitChapters([{type:'heading',level:2,text:'Chapter one'}]).length,1);
  assert.equal(core.splitChapters([{type:'paragraph',text:'Full article'}])[0].id,'intro');
  assert.deepEqual(core.splitChapters([]),[]);
});

test('existing heading links select the containing chapter and invalid hashes return to the start',()=>{
  assert.equal(typeof core.chapterFromHash,'function');
  const chapters=core.splitChapters([
    {type:'paragraph',text:'Introduction'},
    {type:'heading',level:2,text:'First chapter'},
    {type:'heading',level:3,text:'Subsection'},
    {type:'heading',level:2,text:'Second chapter'}
  ]);
  assert.equal(core.chapterFromHash(chapters,'#part-2'),1);
  assert.equal(core.chapterFromHash(chapters,'#part-3'),2);
  for(const hash of ['','#intro','#missing','#%zz'])assert.equal(core.chapterFromHash(chapters,hash),0);
});
