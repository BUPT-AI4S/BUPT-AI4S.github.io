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
