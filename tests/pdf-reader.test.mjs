import test from 'node:test';
import assert from 'node:assert/strict';
import {pdfSourceLinks,nativePdfSource} from '../static/js/pdf-reader-core.mjs';

test('PDF and paper source links remain available independently',()=>{
  assert.deepEqual(pdfSourceLinks({pdfUrl:'https://aclanthology.org/2025.acl-long.26.pdf',paperUrl:'https://aclanthology.org/2025.acl-long.26/'}),{
    pdf:'https://aclanthology.org/2025.acl-long.26.pdf',paper:'https://aclanthology.org/2025.acl-long.26/'
  });
  assert.deepEqual(pdfSourceLinks({forumUrl:'https://openreview.net/forum?id=abc'}),{pdf:'',paper:'https://openreview.net/forum?id=abc'});
});

test('unsafe or malformed sources never become embedded frames or source links',()=>{
  for(const url of ['javascript:alert(1)','data:application/pdf;base64,abc','http://example.org/paper.pdf','https://user:secret@example.org/paper.pdf','not a URL']) {
    assert.deepEqual(pdfSourceLinks({pdfUrl:url,paperUrl:url}),{pdf:'',paper:''});
    assert.equal(nativePdfSource(url),'');
  }
});

test('native PDF fallback preserves the source query and fits the reading area',()=>{
  assert.equal(nativePdfSource('https://openreview.net/pdf?id=abc#page=3'),'https://openreview.net/pdf?id=abc#view=FitH');
  assert.equal(nativePdfSource('https://aclanthology.org/2025.acl-long.26.pdf'),'https://aclanthology.org/2025.acl-long.26.pdf#view=FitH');
});
