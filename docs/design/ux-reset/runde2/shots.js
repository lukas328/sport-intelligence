// Renders the six views and the overview sheet of one direction.
// Usage: node docs/design/ux-reset/runde2/shots.js <kurzname> [club] [scale]
const { chromium } = require('playwright');
const path = require('path');
const fs = require('fs');
const dir = path.join(__dirname, process.argv[2]);
const club = process.argv[3] || 'rot';
const scale = Number(process.argv[4] || 2);
const out = process.argv[5] || path.join(dir, 'shots');
(async () => {
  fs.mkdirSync(out, { recursive: true });
  const b = await chromium.launch();
  const p = await b.newPage({ viewport: { width: 1400, height: 1000 }, deviceScaleFactor: scale });
  await p.goto('file://' + path.join(dir, 'index.html'));
  await p.evaluate(c => { document.documentElement.dataset.club = c; document.body.classList.add('shot'); }, club);
  await p.evaluate(() => document.fonts.ready);
  await p.waitForTimeout(800);
  await p.evaluate(() => window.dispatchEvent(new Event('resize')));
  const ids = ['start-desk', 'start-phone', 'spiel-desk', 'spiel-phone', 'video-desk', 'zahlen-desk'];
  for (const id of ids) {
    await p.locator('#' + id).screenshot({ path: path.join(out, id + '.jpg'), type: 'jpeg', quality: 82 });
  }
  // overflow check on phone frames: any element wider than its frame
  const issues = await p.evaluate(() => {
    const r = [];
    document.querySelectorAll('.frame').forEach(f => {
      const fr = f.getBoundingClientRect();
      f.querySelectorAll('*').forEach(e => { if (e.closest('.run') || e.closest('svg')) return;
        const b = e.getBoundingClientRect();
        if (b.width && (b.right > fr.right + 1 || b.left < fr.left - 1)) r.push(f.id + ' ' + e.tagName + '.' + e.className + ' ' + Math.round(b.right - fr.right));
        if (e.children.length === 0 && e.scrollWidth > e.clientWidth + 1 && getComputedStyle(e).overflow !== 'visible') r.push(f.id + ' clipped ' + e.tagName + '.' + e.className);
      });
    });
    return r.slice(0, 30);
  });
  if (issues.length) console.log('ISSUES', issues.join('\n'));
  // overview sheet
  const imgs = ids.map(i => 'data:image/jpeg;base64,' + fs.readFileSync(path.join(out, i + '.jpg')).toString('base64'));
  const title = await p.evaluate(() => document.querySelector('.doc h1').textContent + '|' + document.querySelector('.doc .lead').textContent);
  const [t, lead] = title.split('|');
  const q = await b.newPage({ viewport: { width: 2400, height: 1000 }, deviceScaleFactor: 1 });
  await q.setContent(`<html><body style="margin:0;background:#111;color:#eee;font:20px system-ui;padding:40px">
  <h1 style="font-size:56px;margin:0">${t}</h1><p style="max-width:1400px;margin:8px 0 32px;color:#bbb">${lead}</p>
  <div style="display:grid;grid-template-columns:1280px 400px 400px;gap:40px;align-items:start">
   <div style="display:grid;gap:40px"><img src="${imgs[0]}" width="1280"><img src="${imgs[2]}" width="1280"></div>
   <div style="display:grid;gap:40px"><img src="${imgs[1]}" width="390"></div>
   <div style="display:grid;gap:40px"><img src="${imgs[3]}" width="390"></div>
  </div>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:40px"><img src="${imgs[4]}" style="width:100%"><img src="${imgs[5]}" style="width:100%"></div>
  </body></html>`);
  await q.waitForTimeout(500); await q.evaluate(() => Promise.all([...document.images].map(i => i.decode())));
  await q.screenshot({ path: path.join(out, 'bogen.jpg'), type: 'jpeg', quality: 72, fullPage: true });
  await b.close();
})();
