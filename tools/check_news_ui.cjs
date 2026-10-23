// Manual browser regression check; requires Playwright and installed Chrome.
const fs=require('fs'),path=require('path'),http=require('http'),assert=require('node:assert/strict');const {chromium}=require('playwright');
const stage=path.resolve('_site'),output=path.resolve('.tmp/news-checks');fs.mkdirSync(output,{recursive:true});
const server=http.createServer((req,res)=>{const name=decodeURIComponent(new URL(req.url,'http://localhost').pathname).replace(/^\//,'')||'index.html',file=path.resolve(stage,name);if(!file.startsWith(stage+path.sep)){res.writeHead(403).end();return}fs.readFile(file,(e,b)=>{if(e){res.writeHead(404).end();return}res.setHeader('Content-Type',({'.html':'text/html; charset=utf-8','.css':'text/css','.js':'text/javascript','.mjs':'text/javascript','.json':'application/json','.svg':'image/svg+xml','.png':'image/png','.jpeg':'image/jpeg','.jpg':'image/jpeg'})[path.extname(file)]||'application/octet-stream');res.end(b)})});

(async()=>{await new Promise(r=>server.listen(0,'127.0.0.1',r));const base=process.env.NEWS_URL||'http://127.0.0.1:'+server.address().port+'/';const browser=await chromium.launch({channel:'chrome',headless:true});try{
 const page=await browser.newPage({viewport:{width:1440,height:1000}}),errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.goto(base+'news.html?lang=zh&theme=light');await page.waitForSelector('.news-item');assert.equal(await page.locator('.news-item').count(),2);assert.equal(await page.locator('.news-item time').allTextContents().then(x=>x.join(',')),'2026-10-23,2026-10-16');
 await page.goto(base+'news-article.html?id=cncc-2026-haihong-e&lang=zh');
 await page.waitForFunction(()=>document.querySelector('video')||!document.querySelector('#news-status').hidden&&document.querySelector('#news-status').textContent.includes('无法'));
 assert.equal(await page.locator('#news-body video').count(),1,'the report has an embedded player');
 assert.equal(await page.locator('#news-body h3').count(),8);assert.equal(await page.locator('#news-body img').count(),7);
 assert.equal(await page.locator('#news-toc a').count(),6);const video=page.locator('video');assert(await video.evaluate(v=>v.controls&&v.playsInline&&!v.autoplay));
 await video.scrollIntoViewIfNeeded();await page.waitForFunction(()=>document.querySelector('video').readyState>=1,null,{timeout:45000});
 const metadata=await video.evaluate(v=>({duration:v.duration,width:v.videoWidth,height:v.videoHeight,src:v.currentSrc,error:v.error?.message}));assert(metadata.duration>0);assert(metadata.width>0);
 await video.evaluate(v=>v.play());await page.waitForFunction(()=>document.querySelector('video').currentTime>0.2);await video.evaluate(v=>v.pause());
 await video.evaluate(v=>v.currentTime=Math.min(60,v.duration/2));await page.waitForFunction(()=>!document.querySelector('video').seeking);assert((await video.evaluate(v=>v.currentTime))>1);
 await page.screenshot({path:'.tmp/cncc-video-desktop.png'});console.log('VIDEO',JSON.stringify(metadata));
 for(const width of [320,390,768,1024,1440])for(const lang of ['zh','en'])for(const theme of ['light','dark']){await page.setViewportSize({width,height:1000});await page.goto(base+'news-article.html?id=cncc-2026-haihong-e&lang='+lang+'&theme='+theme);await page.waitForSelector('#news-detail-content:not([hidden])');assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth),JSON.stringify({width,lang,theme}));assert.equal(await page.locator('video').count(),1);}
 await page.setViewportSize({width:390,height:1000});await page.locator('video').scrollIntoViewIfNeeded();await page.screenshot({path:'.tmp/cncc-video-mobile.png'});
 await page.goto(base+'news-article.html?id=dialogue-with-researchers&lang=zh');await page.waitForSelector('#news-detail-content:not([hidden])');assert.equal(await page.locator('#news-date').textContent(),'2026-10-16');const body=await page.locator('#news-body').textContent();assert(!body.includes('课程开源社区：'));assert(!body.includes('课程网站：https://'));assert.equal(await page.locator('#news-body img').count(),11);assert.deepEqual(errors,[]);
 console.log('PASS: dates/removals, two news stories, new report7images/8subheadings, actual OSS playback/seeking, 20 responsive theme/language combinations.');
}finally{await browser.close();server.close()}})().catch(e=>{console.error(e);server.close();process.exit(1)});
