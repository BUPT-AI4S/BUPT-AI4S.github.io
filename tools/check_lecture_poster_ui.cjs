// Browser regression: missing announcement, cropped poster, overflow, or broken keyboard dismissal must fail.
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const assert = require('node:assert/strict');
const { chromium } = require('playwright');
const root = path.resolve(__dirname, '..');
const output = path.join(root, '.tmp', 'lecture-poster-checks');
fs.mkdirSync(output, { recursive: true });
const server = http.createServer((req, res) => {
  const name = decodeURIComponent(new URL(req.url, 'http://localhost').pathname).replace(/^\//, '') || 'index.html';
  const file = path.resolve(root, name);
  if (!file.startsWith(root + path.sep)) { res.writeHead(403).end(); return; }
  fs.readFile(file, (error, body) => {
    if (error) { res.writeHead(404).end(); return; }
    res.setHeader('Content-Type', ({ '.html': 'text/html; charset=utf-8', '.css': 'text/css', '.js': 'text/javascript', '.mjs': 'text/javascript', '.json': 'application/json', '.svg': 'image/svg+xml', '.png': 'image/png' })[path.extname(file)] || 'application/octet-stream');
    res.end(body);
  });
});
(async () => {
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  const base = 'http://127.0.0.1:' + server.address().port + '/';
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  try {
    const page = await browser.newPage({ reducedMotion: 'reduce' });
    const errors = [];
    page.on('pageerror', error => errors.push(error.message));
    await page.route('**/*', route => route.request().url().startsWith(base) ? route.continue() : route.abort());
    for (const width of [320, 390, 768, 960, 1440]) for (const lang of ['zh', 'en']) for (const theme of ['light', 'dark']) {
      await page.setViewportSize({ width, height: 1000 });
      await page.goto(base + 'index.html?lang=' + lang + '&theme=' + theme);
      await page.locator('#lecture-announcement').waitFor({ timeout: 3000 });
      await page.locator('#home-news:not([hidden])').waitFor();
      const geometry = await page.evaluate(() => {
        const rect = selector => document.querySelector(selector).getBoundingClientRect();
        const card = rect('#lecture-announcement'), news = rect('#home-news'), hero = rect('.hero-inner'), nav = rect('.nav');
        const image = document.querySelector('.lecture-poster-thumbnail img'), thumbnail = image.getBoundingClientRect();
        return { overflow: document.documentElement.scrollWidth > innerWidth, cardTop: card.top, cardBottom: card.bottom, cardHeight: card.height, newsBottom: news.bottom, heroTop: hero.top, navBottom: nav.bottom, thumbnailWidth: thumbnail.width, thumbnailRatio: thumbnail.width / thumbnail.height, originalRatio: image.naturalWidth / image.naturalHeight };
      });
      const context = JSON.stringify({ width, lang, theme, geometry });
      assert(!geometry.overflow, context);
      assert(geometry.newsBottom <= geometry.cardTop && geometry.cardBottom <= geometry.heroTop && geometry.cardTop >= geometry.navBottom, context);
      assert(Math.abs(geometry.thumbnailRatio - geometry.originalRatio) < 0.001, context);
      assert(geometry.thumbnailWidth >= (width < 600 ? 90 : 140) && geometry.thumbnailWidth <= (width < 600 ? 110 : 160), context);
      if (width < 600) assert(geometry.cardHeight < 450, context);
      assert((await page.locator('#lecture-announcement').innerText()).includes(lang === 'en' ? 'Guangyi Liu' : '刘光毅'));
      assert.equal(await page.locator('.hero-book-cover img').count(), 1);
      const open = page.locator('.lecture-poster-open');
      await open.focus();
      await page.keyboard.press('Enter');
      assert(await page.locator('#lecture-poster-dialog').evaluate(dialog => dialog.open));
      assert.equal(await page.evaluate(() => document.activeElement.id), 'lecture-poster-close');
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'lecture-poster-close');
      await page.keyboard.press('Shift+Tab');
      assert.equal(await page.evaluate(() => document.activeElement.id), 'lecture-poster-close');
      assert.equal(await page.locator('#lecture-poster-dialog img').getAttribute('src'), 'static/images/lecture-liu-guangyi-20261027.png');
      assert.equal(await page.evaluate(() => getComputedStyle(document.documentElement).overflow), 'hidden');
      await page.keyboard.press('Escape');
      assert.equal(await page.locator('#lecture-poster-dialog').evaluate(dialog => dialog.open), false);
      assert(await open.evaluate(button => document.activeElement === button));
      await page.locator('.lecture-poster-thumbnail').click();
      await page.locator('#lecture-poster-close').click();
      assert(await page.locator('.lecture-poster-thumbnail').evaluate(button => document.activeElement === button));
      await page.evaluate(() => scrollTo(0, 0));
      if ([390, 1440].includes(width)) await page.screenshot({ path: path.join(output, `${width}-${lang}-${theme}.png`) });
    }
    await page.locator('.lang-toggle').click();
    assert((await page.locator('#lecture-poster-close').getAttribute('aria-label')).includes('关闭'));
    await page.locator('.lecture-poster-open').click();
    await page.screenshot({ path: path.join(output, 'dialog-1440-zh-dark.png') });
    await page.locator('#lecture-poster-close').click();
    await page.setViewportSize({ width: 320, height: 700 });
    await page.locator('.lecture-poster-open').click();
    await page.screenshot({ path: path.join(output, 'dialog-320-zh-dark.png') });
    assert.deepEqual(errors, []);
    console.log('PASS: 20 responsive/language/theme cases; original aspect ratio; news, course and book retained; poster/button opening; close/Escape/focus return and keyboard containment; live language labels; no horizontal overflow.');
  } finally { await browser.close(); server.close(); }
})().catch(error => { console.error(error); server.close(); process.exitCode = 1; });
