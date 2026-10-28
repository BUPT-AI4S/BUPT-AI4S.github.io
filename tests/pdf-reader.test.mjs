import test from 'node:test';
import assert from 'node:assert/strict';
import {pdfSourceLinks,nativePdfSource,openNativePdf} from '../static/js/pdf-reader-core.mjs';

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

test('native PDF navigation preserves the original URL without injected viewer options',()=>{
  assert.equal(nativePdfSource('https://openreview.net/pdf?id=abc#page=3'),'https://openreview.net/pdf?id=abc#page=3');
  assert.equal(nativePdfSource('https://aclanthology.org/2025.acl-long.26.pdf'),'https://aclanthology.org/2025.acl-long.26.pdf');
});

test('a standalone reader redirects directly to the PDF instead of embedding it',()=>{
  const destinations=[],browser={location:{replace:url=>destinations.push(url)}};browser.parent=browser;
  assert.equal(openNativePdf('https://aclanthology.org/2025.acl-long.26.pdf',browser),true);
  assert.deepEqual(destinations,['https://aclanthology.org/2025.acl-long.26.pdf']);
});

test('an embedded reader navigates the top page and retains browser back navigation',()=>{
  const destinations=[],browser={parent:{},top:{location:{assign:url=>destinations.push(url)}}};
  assert.equal(openNativePdf('https://example.org/paper.pdf',browser),true);
  assert.deepEqual(destinations,['https://example.org/paper.pdf']);
});

test('blocked or unsafe navigation leaves the original source links usable',()=>{
  assert.equal(openNativePdf('javascript:alert(1)',{}),false);
  const browser={parent:{},top:{get location(){throw new Error('Cross-origin parent');}}};
  assert.equal(openNativePdf('https://example.org/paper.pdf',browser),false);
});
