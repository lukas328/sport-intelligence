/* Renders the PNG files in final/ and the screenshots in shots/.
   node docs/design/brand2/taktik/render.js */
const { chromium } = require('playwright'); const path = require('path'); const fs = require('fs');
(async () => {
  const dir = __dirname, fin = path.join(dir, 'final'), shots = path.join(dir, 'shots');
  fs.mkdirSync(shots, { recursive: true });
  const b = await chromium.launch();
  /* PNGs: the SVG at exact pixel size, transparent where the SVG has no background */
  const png = async (svgFile, out, w, h) => {
    const p = await b.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 1 });
    const svg = fs.readFileSync(path.join(fin, svgFile), 'utf8').replace('<svg ', `<svg width="${w}" height="${h}" `);
    await p.setContent(`<html><body style="margin:0;background:transparent">${svg}</body></html>`);
    await p.screenshot({ path: path.join(fin, out), omitBackground: true, clip: { x: 0, y: 0, width: w, height: h } });
    await p.close();
  };
  await png('favicon-16.svg', 'favicon-16.png', 16, 16);
  await png('favicon-32.svg', 'favicon-32.png', 32, 32);
  await png('app-icon.svg', 'app-icon-1024.png', 1024, 1024);
  await png('app-icon.svg', 'app-icon-512.png', 512, 512);
  await png('app-icon-maske.svg', 'app-icon-maske-1024.png', 1024, 1024);
  await png('app-icon-maske.svg', 'app-icon-maske-512.png', 512, 512);
  await png('open-graph.svg', 'open-graph.png', 1200, 630);
  await png('zeichen.svg', 'zeichen-1024.png', 1024, 1024);
  /* page screenshots, one per section */
  const p = await b.newPage({ viewport: { width: 1360, height: 1000 } });
  const errs = []; p.on('console', m => m.type() === 'error' && errs.push(m.text())); p.on('pageerror', e => errs.push(e.message));
  await p.goto('file://' + path.join(dir, 'index.html'), { waitUntil: 'networkidle' }); await p.evaluate(() => document.fonts.ready);
  for (const el of await p.$$('section.sec')) { const id = await el.getAttribute('id'); await el.screenshot({ path: path.join(shots, id + '.jpg'), type: 'jpeg', quality: 80 }); }
  await p.screenshot({ path: path.join(shots, 'seite.jpg'), type: 'jpeg', quality: 55, fullPage: true });
  const q = await b.newPage({ viewport: { width: 400, height: 900 } }); await q.goto('file://' + path.join(dir, 'index.html'), { waitUntil: 'networkidle' });
  console.log('errors:', errs.length ? errs : 'none', '| scrollWidth@400:', await q.evaluate(() => document.documentElement.scrollWidth));
  await b.close();
})();
