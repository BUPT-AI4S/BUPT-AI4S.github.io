// Manual browser regression check; requires Playwright and installed Chrome.
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('node:assert/strict');const {chromium}=require('playwright');
const stage=path.resolve('_site'),output=path.resolve('.tmp/news-checks');fs.mkdirSync(output,{recursive:true});
const server=http.createServer((req,res)=>{const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\//,'')||'index.html',file=path.resolve(stage,name);if(!file.startsWith(stage+path.sep)){res.writeHead(403).end();return}fs.readFile(file,(e,b)=>{if(e){res.writeHead(404).end();return}res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpeg':'image/jpeg','.jpg':'image/jpeg'})[path.extname(file)]||'application/octet-stream');res.end(b)})});


(async()=>{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));
 const base=process.env.NEWS_URL||'http://127.0.0.1:'+server.address().port+'/';
 const browser=await chromium.launch({channel:'chrome',headless:true});
 try{
  const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.route('**/*',route=>route.request().url().startsWith(base)?route.continue():route.abort());
  for(const width of [320,390,768,960,1024,1440,1920])for(const lang of ['zh','en'])for(const theme of ['light','dark']){
   await page.setViewportSize({width,height:1000});
   await page.goto(base+'index.html?lang='+lang+'&theme='+theme);
   await page.waitForSelector('#home-news:not([hidden])');
   assert((await page.locator('#home-news-title').getAttribute('href')).includes('cncc-2026-haihong-e'));
   assert.equal(await page.locator('#home-news-date').textContent(),'2026-10-23');
   const geo=await page.evaluate(()=>{const banner=document.querySelector('#home-news').getBoundingClientRect(),hero=document.querySelector('.hero-inner').getBoundingClientRect(),nav=document.querySelector('.nav').getBoundingClientRect();return {overflow:document.documentElement.scrollWidth>innerWidth,bottom:banner.bottom,heroTop:hero.top,top:banner.top,navBottom:nav.bottom}});
   assert(!geo.overflow,JSON.stringify({width,lang,theme,geo}));assert(geo.bottom<=geo.heroTop);assert(geo.top>=geo.navBottom);
   const title=await page.locator('#home-news-title').textContent();assert(title.includes(lang==='en'?'Haihong E':'鄂海红'));
   if([390,1440].includes(width)&&lang==='zh'&&theme==='light')await page.screenshot({path:'.tmp/home-news-'+width+'.png'});
  }
  await page.locator('#home-news-details').click();await page.waitForSelector('#news-detail-content:not([hidden])');assert(page.url().includes('id=cncc-2026-haihong-e'));
  await page.clock.install();await page.goto(base+'index.html?lang=zh');await page.waitForSelector('#home-news:not([hidden])');await page.locator('.lang-toggle').click();assert((await page.locator('#home-news-title').textContent()).includes('Haihong E'));
  let mode='new',requests=0;
  const catalog={schemaVersion:1,articles:[{id:'old-news',date:'2026-10-16',title:'旧动态',summary:'旧摘要'},{id:'replacement',date:'2026-10-24',title:'新发布动态',titleEn:'Newly published story',summary:'自动更新摘要',summaryEn:'Updated summary'}]};
  await page.route('**/data/news-index.json',route=>{requests++;return mode==='fail'?route.fulfill({status:503,body:''}):route.fulfill({json:mode==='empty'?{schemaVersion:1,articles:[]}:catalog});});
  await page.clock.fastForward(60000);await page.waitForFunction(()=>document.querySelector('#home-news-title').textContent==='Newly published story');assert((await page.locator('#home-news-details').getAttribute('href')).includes('replacement'));
  mode='fail';await page.clock.fastForward(60000);await page.waitForTimeout(100);assert.equal(await page.locator('#home-news-title').textContent(),'Newly published story');
  mode='empty';await page.clock.fastForward(60000);await page.waitForSelector('#home-news[hidden]',{state:'attached'});assert(requests>=3);
  assert.deepEqual(errors,[]);console.log('PASS:28 responsive/language/theme cases; latest article details; live language switching; automatic replacement without reload; connection failure retains teaser; empty catalog hides it.');
 }finally{await browser.close();server.close();}
})().catch(e=>{console.error(e);server.close();process.exit(1)});
