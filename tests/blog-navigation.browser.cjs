// Optional browser regression checks: start the local preview, then run with Playwright on NODE_PATH.
const test=require('node:test');
const assert=require('node:assert/strict');
const {chromium}=require('playwright');
const base=process.env.AI4S_PREVIEW_URL||'http://127.0.0.1:8082/';
let browser;
test.before(async()=>{browser=await chromium.launch({headless:true,channel:'chrome'});});
test.after(async()=>{await browser?.close();});

test('folder, all-articles and popup category selections return to the page top',async t=>{
  const context=await browser.newContext({viewport:{width:1440,height:1000},reducedMotion:'reduce'});
  t.after(()=>context.close());const page=await context.newPage();
  await page.goto(base+'blog.html');await page.waitForSelector('.article-card');
  for(const id of ['foundation','agents','reviews']){
    await page.locator('#pocket-'+id).click();
    assert.ok(await page.locator('.article-card').count()>3);
    assert.equal(await page.evaluate(()=>scrollY),0,'folder '+id);
    await page.locator('#all-articles').click();
    assert.equal(await page.evaluate(()=>scrollY),0,'all articles');
  }
  for(const id of ['foundation','all','data','math-physics']){
    await page.evaluate(()=>window.scrollTo({top:600,behavior:'instant'}));
    await page.locator('#category-toggle').click();
    await page.locator('#category-options [data-collection="'+id+'"]').click();
    await page.waitForFunction(()=>!document.getElementById('category-drawer').open);
    assert.equal(await page.evaluate(()=>scrollY),0,'popup '+id);
    assert.ok((await page.locator('.collection-heading').boundingBox()).y>=0);
  }
});

test('article titles and read links open a new tab while retaining the original list',async t=>{
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  t.after(()=>context.close());const page=await context.newPage();
  await page.goto(base+'blog.html?category=foundation');await page.waitForSelector('.article-card');
  for(const selector of ['.article-card h3 a','.card-read']){
    const url=page.url(),anchor=page.locator(selector).first();
    const [reader]=await Promise.all([context.waitForEvent('page',{timeout:2500}),anchor.click()]);
    await reader.waitForSelector('#article-toc a');
    assert.ok(reader.url().includes('blog-article.html?id=scientific-foundation-models&category=foundation'));
    assert.equal(page.url(),url);
    assert.equal(await page.locator('.article-card').count(),5);
    assert.match(await anchor.getAttribute('rel'),/noopener/);
    await reader.close();
  }
});

test('search filters immediately, combines with folders and clears without resetting the category',async t=>{
  const context=await browser.newContext({viewport:{width:1440,height:1000}});
  t.after(()=>context.close());const page=await context.newPage();
  await page.goto(base+'blog.html?lang=zh');await page.waitForSelector('.article-card');
  await page.locator('#blog-search').fill('Harness');
  assert.equal(await page.locator('.article-card').count(),1);
  assert.equal(await page.locator('.article-card').getAttribute('id'),'scientific-agent-harness');
  await page.locator('#pocket-foundation').click();
  assert.equal(await page.locator('.article-card').count(),0);
  assert.match(await page.locator('#empty-collection h3').textContent(),/没有找到/);
  assert.equal(await page.locator('#blog-search').inputValue(),'Harness');
  await page.locator('#all-articles').click();assert.equal(await page.locator('.article-card').count(),1);
  await page.locator('#pocket-foundation').click();await page.locator('#search-clear').click();
  assert.equal(await page.locator('.article-card').count(),5);
  assert.equal(new URL(page.url()).searchParams.has('q'),false);
  assert.equal(new URL(page.url()).searchParams.get('category'),'foundation');
  await page.locator('#blog-search').fill('unmatched-search-term');
  await page.locator('#pocket-math-physics').click();
  assert.match(await page.locator('#empty-collection h3').textContent(),/新内容/);
});

test('search survives reload, language changes, new tabs and return links, including missing hash targets',async t=>{
  const context=await browser.newContext({viewport:{width:390,height:844}});
  t.after(()=>context.close());const page=await context.newPage();
  await page.goto(base+'blog.html?q=Harness&lang=zh');await page.waitForSelector('.article-card');
  await page.reload();await page.waitForSelector('.article-card');
  assert.equal(await page.locator('#blog-search').inputValue(),'Harness');
  await page.locator('#lang-toggle').click();
  assert.match(await page.locator('#blog-search').getAttribute('placeholder'),/Search/);
  assert.equal(await page.locator('.article-card').count(),1);
  const [reader]=await Promise.all([context.waitForEvent('page'),page.locator('.card-read').click()]);
  await reader.waitForSelector('#article-toc a',{state:'attached'});
  assert.equal(new URL(reader.url()).searchParams.get('q'),'Harness');
  await reader.locator('#back-link').click();await reader.waitForSelector('.article-card');
  assert.equal(await reader.locator('#blog-search').inputValue(),'Harness');
  assert.equal(await reader.locator('.article-card').count(),1);
  await page.goto(base+'blog.html?q=unmatched-search-term#scientific-agent-harness');
  await page.waitForSelector('#empty-collection');
  assert.equal(await page.locator('#load-status').textContent(),'');
  assert.equal(await page.locator('.article-card').count(),0);
});
