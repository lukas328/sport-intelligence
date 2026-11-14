// After `next build` (static export): pages without a language path and the 404 page.
//
// The app and old links use addresses like https://handball-intelligence.com/aufnahme/ (no /de/). A static
// export has no server redirects, so this writes a tiny page for each such address that sends the
// visitor to the same page in the browser's language (fr, en, else de), keeping ?query and #hash,
// with a meta refresh to /de/ and plain links when scripts are off. It also writes out/404.html in
// the site's look with three ways on (Start, Demo-Spiel, Fragen).
//
// Real hosting should still answer these with a server redirect (see README, «Hosting»).
import { existsSync, mkdirSync, readFileSync, readdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = join(root, "out");

const slugsOf = (file) => [...readFileSync(join(root, file), "utf8").matchAll(/slug: "([a-z0-9-]+)"/g)].map((m) => m[1]);
const PAGES = ["so-funktioniert-es", "aufnahme", "demo", "preise", "hilfe", "ratgeber", "fakten", "vorlagen", "vorlagen/einwilligung", "vorlagen/strichliste", "vorlagen/spieltag", "rechner/wurfquote", "rechner/speicher", "ueber-uns", "daten", "kontakt", "blog", "agb", "datenschutz", "impressum", "funktionen"];
const paths = [
  ...PAGES,
  ...slugsOf("content/help/index.ts").map((s) => `hilfe/${s}`),
  ...slugsOf("content/blog/index.ts").map((s) => `blog/${s}`),
  ...slugsOf("content/ratgeber/index.ts").map((s) => `ratgeber/${s}`),
];
// absolute addresses for canonical and hreflang (search engines ignore relative ones)
const SITE = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://handball-intelligence.com").replace(/\/$/, "");

// the built stylesheet(s) of the site, so these pages look like the rest without their own CSS
const home = readFileSync(join(out, "de", "index.html"), "utf8");
const css = [...home.matchAll(/<link rel="stylesheet" href="([^"]+)"/g)].map((m) => `<link rel="stylesheet" href="${m[1]}">`).join("");
const htmlClass = (home.match(/<html[^>]*class="([^"]+)"/) ?? [])[1] ?? "";
const fonts = [...home.matchAll(/<link rel="preload" href="([^"]+\.woff2)"[^>]*>/g)].map((m) => m[0]).join("");

const head = (title, extra = "") => `<!doctype html>
<html lang="de-CH" class="${htmlClass}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${title}</title>
<meta name="robots" content="noindex">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
${fonts}${css}${extra}
</head>`;

const LANGS = { de: "Deutsch", fr: "Français", en: "English" };
const pick = `var l=(navigator.language||"de").slice(0,2).toLowerCase();l=(l==="fr"||l==="en")?l:"de";`;

function redirectPage(path) {
  const de = `/de/${path}/`;
  // guides that exist only in German send every language there
  const has = (l) => existsSync(join(out, l, path, "index.html"));
  const langs = ["fr", "en"].filter(has);
  const choose = `var ok=${JSON.stringify(["de", ...langs])};if(ok.indexOf(l)<0)l="de";`;
  const others = langs.map((l) => ` · <a class="link" href="/${l}/${path}/">${l === "fr" ? "Continuer" : "Continue"}</a>`).join("");
  return `${head("Handball Intelligence", `
<link rel="canonical" href="${SITE}${de}">
<meta http-equiv="refresh" content="1; url=${de}">
<script>(function(){${pick}${choose}location.replace("/"+l+"/${path}/"+location.search+location.hash);})();</script>`)}
<body>
<main class="wrap py-16">
<p><a class="link" href="${de}">Weiter</a>${others}</p>
</main>
</body>
</html>
`;
}

const NOT_FOUND = {
  de: { title: "Diese Seite gibt es nicht.", lead: "Vielleicht ein alter Link. Hier geht es weiter:", start: "Zur Startseite", demo: "Demo-Spiel ansehen", faq: "Fragen und Antworten" },
  fr: { title: "Cette page n'existe pas.", lead: "Peut-être un ancien lien. Pour continuer :", start: "Vers l'accueil", demo: "Voir le match de démo", faq: "Questions et réponses" },
  en: { title: "This page does not exist.", lead: "Perhaps an old link. Carry on here:", start: "To the home page", demo: "See the demo match", faq: "Questions and answers" },
};

function notFoundPage() {
  const blocks = Object.entries(NOT_FOUND)
    .map(
      ([l, t]) => `<section lang="${l}" data-lang="${l}"${l === "de" ? "" : " hidden"}>
<h1 class="max-w-[52rem] text-[2.5rem] leading-[.96] md:text-[4rem]">${t.title}</h1>
<p class="mt-5 max-w-[40rem] text-[1.1875rem] text-ink-2 md:text-[1.3125rem]">${t.lead}</p>
<div class="mt-8 flex flex-col gap-3 sm:flex-row sm:flex-wrap">
<a class="btn btn-ink" href="/${l}/">${t.start}</a>
<a class="btn btn-line" href="/${l}/demo/">${t.demo}</a>
<a class="btn btn-line" href="/${l}/hilfe/">${t.faq}</a>
</div>
</section>`,
    )
    .join("\n");
  return `${head("Seite nicht gefunden | Handball Intelligence")}
<body>
<header class="border-b-2 border-ink"><div class="wrap flex min-h-[4.5rem] items-center py-2">
<a href="/" class="inline-flex items-center py-1" aria-label="Handball Intelligence"><img src="/brand/wortmarke-zweizeilig.svg" alt="" width="1456" height="512" class="h-14 w-auto md:h-16"></a>
</div></header>
<main id="main">
<div class="relative pt-8 pb-10 md:pt-14 md:pb-14"><div class="wrap">
${blocks}
<p class="mt-10 flex flex-wrap gap-x-6">${Object.entries(LANGS)
    .map(([l, n]) => `<a class="link" lang="${l}" href="/${l}/">${n}</a>`)
    .join("")}</p>
</div>
<span aria-hidden="true" class="absolute right-0 bottom-0 left-0 h-3.5 bg-club [clip-path:polygon(0_0,100%_78%,100%_100%,0_100%)] md:h-[22px]"></span>
</div>
</main>
<script>(function(){${pick}var m=location.pathname.match(/^\\/(de|fr|en)(\\/|$)/);if(m)l=m[1];if(l==="de")return;document.documentElement.lang=l==="fr"?"fr-CH":"en";document.querySelectorAll("[data-lang]").forEach(function(s){s.hidden=s.getAttribute("data-lang")!==l;});document.title=${JSON.stringify(
    Object.fromEntries(Object.entries(NOT_FOUND).map(([l, t]) => [l, `${t.title} | Handball Intelligence`])),
  )}[l];})();</script>
</body>
</html>
`;
}

let n = 0;
for (const path of paths) {
  const dir = join(out, path);
  mkdirSync(dir, { recursive: true });
  // never overwrite a real page (paths are without language, real pages all live under /de/ etc.)
  if (readdirSync(dir).includes("index.html")) continue;
  writeFileSync(join(dir, "index.html"), redirectPage(path));
  n++;
}
writeFileSync(join(out, "404.html"), notFoundPage());

// the language choice at / (public/index.html): absolute canonical and hreflang, Swiss French
const rootFile = join(out, "index.html");
writeFileSync(
  rootFile,
  readFileSync(rootFile, "utf8")
    .replace(/hreflang="fr"/g, 'hreflang="fr-CH"')
    .replace(/(<link rel="(?:canonical|alternate)"[^>]*href=")\//g, `$1${SITE}/`)
    .replace('<link rel="alternate" hreflang="en"', `<link rel="alternate" hreflang="x-default" href="${SITE}/de/">\n<link rel="alternate" hreflang="en"`),
);
console.log(`redirects: ${n} pages without a language path, 404.html`);
