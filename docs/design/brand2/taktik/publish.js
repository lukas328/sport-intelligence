/* Copies the finished logo files from final/ into the apps, unchanged, and builds the web app's
   favicon.ico from the 16 and 32 px drawings and the full mark at 48 px.

     node docs/design/brand2/taktik/build.js     final/*.svg
     node docs/design/brand2/taktik/render.js    final/*.png
     node docs/design/brand2/taktik/publish.js   apps/web, apps/site, apps/mobile

   One colour everywhere (decision E10, README «Farben»): every file copied here is ink on light
   (or white on dark); the `-zweifarbig` files stay in final/ as a record. */
"use strict";
const fs = require("fs"), path = require("path");
const fin = path.join(__dirname, "final"), root = path.join(__dirname, "..", "..", "..", "..");

const COPIES = {
  // the web app
  "apps/web/public/brand/wortmarke-quer.svg": "wortmarke-quer.svg",
  "apps/web/public/brand/wortmarke-zweizeilig.svg": "wortmarke-zweizeilig.svg",
  "apps/web/public/brand/favicon-32.svg": "favicon-32.svg",
  "apps/web/public/brand/favicon-32-tinte.svg": "favicon-32-tinte.svg",
  "apps/web/public/brand/zeichen-tinte.svg": "zeichen-tinte.svg",
  "apps/web/src/app/icon.svg": "favicon-32-tinte.svg",
  "apps/web/src/app/apple-icon.png": "app-icon-180.png",
  "apps/web/src/app/opengraph-image.png": "open-graph.png",
  "apps/web/public/icon-192.png": "app-icon-192.png",
  "apps/web/public/icon-512.png": "app-icon-512.png",
  "apps/web/public/icon-512-maskable.png": "app-icon-maske-512.png",
  // the website
  "apps/site/public/brand/wortmarke-quer.svg": "wortmarke-quer.svg",
  "apps/site/public/brand/wortmarke-zweizeilig.svg": "wortmarke-zweizeilig.svg",
  "apps/site/public/favicon.svg": "favicon-32.svg",
  "apps/site/public/icon.png": "app-icon-512.png",
  "apps/site/public/apple-icon.png": "app-icon-180.png",
  "apps/site/public/og.png": "open-graph.png",
  "apps/site/public/og-de.png": "open-graph-de.png",
  "apps/site/public/og-fr.png": "open-graph-fr.png",
  "apps/site/public/og-en.png": "open-graph-en.png",
  // the mobile app
  "apps/mobile/assets/icon.png": "app-icon-1024.png",
  "apps/mobile/assets/adaptive-icon.png": "app-icon-maske-1024.png",
  "apps/mobile/assets/zeichen.png": "zeichen-tinte-288.png",
  "apps/mobile/assets/zeichen-dunkel.png": "zeichen-weiss-288.png",
};
for (const [to, from] of Object.entries(COPIES)) fs.copyFileSync(path.join(fin, from), path.join(root, to));

/* favicon.ico: an icon directory with the PNGs inside (supported by every current browser) */
const images = [["favicon-16.png", 16], ["favicon-32.png", 32], ["zeichen-48.png", 48]].map(([f, s]) => [fs.readFileSync(path.join(fin, f)), s]);
const head = Buffer.alloc(6 + 16 * images.length);
head.writeUInt16LE(0, 0);
head.writeUInt16LE(1, 2);
head.writeUInt16LE(images.length, 4);
let offset = head.length;
images.forEach(([data, size], i) => {
  const e = 6 + 16 * i;
  head.writeUInt8(size, e);
  head.writeUInt8(size, e + 1);
  head.writeUInt8(0, e + 2);
  head.writeUInt8(0, e + 3);
  head.writeUInt16LE(1, e + 4);
  head.writeUInt16LE(32, e + 6);
  head.writeUInt32LE(data.length, e + 8);
  head.writeUInt32LE(offset, e + 12);
  offset += data.length;
});
fs.writeFileSync(path.join(root, "apps/web/src/app/favicon.ico"), Buffer.concat([head, ...images.map(([d]) => d)]));
console.log("ok", Object.keys(COPIES).length + 1, "files");
