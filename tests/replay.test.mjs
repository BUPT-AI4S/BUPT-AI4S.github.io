import test from 'node:test';
import assert from 'node:assert/strict';
import {findMatches, activeSegment, formatTime, courseLabels, sortCourses} from '../static/js/replay-core.mjs';
test('course categories have independent numbering', () => {
  assert.deepEqual(courseLabels([
    {id:'lecture-01',title:'课程'}, {id:'chairs-01',title:'大师讲堂'},
    {id:'lecture-02',title:'课程'}, {id:'chairs-02',title:'大师讲堂'}
  ]), [
    {label:'课程',number:'01'}, {label:'大师讲堂',number:'01'},
    {label:'课程',number:'02'}, {label:'大师讲堂',number:'02'}
  ]);
});
test('search counts occurrences and treats punctuation literally', () => {
  assert.deepEqual(findMatches([{text:'AI ai [x]'}], 'ai'), [{index:0,start:0,end:2},{index:0,start:3,end:5}]);
  assert.equal(findMatches([{text:'AI [x]'}], '[x]').length, 1);
  assert.deepEqual(findMatches([{text:'abc'}], ' '), []);
});

test('expert reports have their own numbering without advancing lecture numbers', () => {
  assert.deepEqual(courseLabels([
    {id:'expert-01',title:'专家报告1'}, {id:'lecture-01',title:'第一讲'},
    {id:'chairs-01',title:'大师讲堂1'}, {id:'expert-02',title:'专家报告2'},
    {id:'lecture-02',title:'第二讲'}, {id:'legacy-report',title:'专家报告3'}
  ]), [
    {label:'专家报告',number:'01'}, {label:'课程',number:'01'},
    {label:'大师讲堂',number:'01'}, {label:'专家报告',number:'02'},
    {label:'课程',number:'02'}, {label:'专家报告',number:'03'}
  ]);
});

test('directory groups lectures, masterclasses and expert reports in numeric order', () => {
  const courses=[
    {id:'expert-02',title:'专家报告2'}, {id:'lecture-10',title:'第十讲'},
    {id:'chairs-02',title:'大师讲堂2'}, {id:'expert-01',title:'专家报告1'},
    {id:'lecture-02',title:'第二讲'}, {id:'chairs-01',title:'大师讲堂1'}
  ];
  const before=structuredClone(courses);
  assert.deepEqual(sortCourses(courses).map(c=>c.id),[
    'lecture-02','lecture-10','chairs-01','chairs-02','expert-01','expert-02'
  ]);
  assert.deepEqual(courses,before);
});
test('timeline does not highlight silence or the previous sentence boundary', () => {
  const rows=[{start:0,end:1000},{start:2000,end:3000}];
  assert.equal(activeSegment(rows,500),0);
  assert.equal(activeSegment(rows,1000),-1);
  assert.equal(activeSegment(rows,2000),1);
});
test('formats long courses and invalid times', () => {
  assert.equal(formatTime(3661000),'1:01:01');
  assert.equal(formatTime(null),'—');
});
