// node runde2/shots.js <name>  ->  runde2/<name>/shots/*.jpg and bogen.jpg
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
(async () => {
  const name = process.argv[2], dir = path.join(__dirname, name), out = path.join(dir, 'shots');
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1400, height: 1000 }, deviceScaleFactor: 1 });
  const errs = [];
  p.on('console', m => { if (m.type() === 'error') errs.push(m.text()); });
  p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.join(dir, 'index.html'), { waitUntil: 'networkidle' });
  await p.evaluate(() => document.fonts.ready); await p.waitForTimeout(400);
  const ids = ['start-desk', 'start-phone', 'spiel-desk', 'spiel-phone', 'video-desk', 'zahlen-desk'];
  for (const id of ids) {
    const el = await p.$('#' + id + ' .frame');
    await el.screenshot({ path: path.join(out, id + '.jpg'), type: 'jpeg', quality: 82 });
  }
  const fonts = await p.evaluate(() => [...document.fonts].filter(f => f.status !== 'loaded' && f.status !== 'unloaded').map(f => f.family + ' ' + f.status));
  // overflow check at 400 px
  const q = await b.newPage({ viewport: { width: 400, height: 900 } });
  await q.goto('file://' + path.join(dir, 'index.html'), { waitUntil: 'networkidle' }); await q.waitForTimeout(300);
  const over = await q.evaluate(() => document.documentElement.scrollWidth);
  // contact sheet
  const img = f => 'data:image/jpeg;base64,' + fs.readFileSync(path.join(out, f + '.jpg')).toString('base64');
  const html = `<body style="margin:0;background:${process.argv[3] || '#222'};padding:40px;font:600 22px sans-serif;color:#888">
  <div style="display:grid;grid-template-columns:1280px 390px;gap:40px;align-items:start">
  <img src="${img('start-desk')}"><img src="${img('start-phone')}">
  <img src="${img('spiel-desk')}"><img src="${img('spiel-phone')}">
  <img src="${img('video-desk')}"><span></span>
  <img src="${img('zahlen-desk')}"><span></span></div></body>`;
  const r = await b.newPage({ viewport: { width: 1790, height: 1000 } });
  await r.setContent(html); await r.waitForTimeout(300);
  await r.screenshot({ path: path.join(out, 'bogen.jpg'), type: 'jpeg', quality: 72, fullPage: true });
  console.log('errors:', errs.length ? errs : 'none', '| fonts not loaded:', fonts.length ? fonts : 'none', '| scrollWidth@400:', over);
  await b.close();
})();
