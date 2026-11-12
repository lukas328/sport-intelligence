// node docs/design/brand2/dinge/shots.js -> shots/<idea>.jpg (one board each) and shots/seite.jpg
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const dir = __dirname, out = path.join(dir, 'shots'); fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch(); const p = await b.newPage({ viewport: { width: 1360, height: 1000 }, deviceScaleFactor: 1 });
  const errs = []; p.on('console', m => m.type() === 'error' && errs.push(m.text())); p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.join(dir, 'index.html'), { waitUntil: 'networkidle' }); await p.evaluate(() => document.fonts.ready);
  for (const el of await p.$$('section.tafel, section.rank')) { const id = await el.getAttribute('id'); await el.screenshot({ path: path.join(out, id + '.jpg'), type: 'jpeg', quality: 82 }); }
  await p.screenshot({ path: path.join(out, 'seite.jpg'), type: 'jpeg', quality: 60, fullPage: true });
  const q = await b.newPage({ viewport: { width: 400, height: 900 } }); await q.goto('file://' + path.join(dir, 'index.html'), { waitUntil: 'networkidle' });
  console.log('errors:', errs.length ? errs : 'none', '| scrollWidth@400:', await q.evaluate(() => document.documentElement.scrollWidth));
  await b.close();
})();
