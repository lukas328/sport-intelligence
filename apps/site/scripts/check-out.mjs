// Checks the built site in out/ (runs after `next build` and redirects.mjs, and in the tests when
// out/ exists). Fails the build when a page breaks a rule that search engines and assistants rely on:
//
// - every page has exactly one h1
// - indexable pages: a title of at most 60 characters and a description of 70 to 160, both unique
// - canonical points to the page itself; hreflang lists the page, x-default and every language
//   version, and each version lists the same set back
// - every JSON-LD block parses, and questions, answers, steps, breadcrumbs and headlines it names
//   are visible on the page
// - every internal link leads to a page; every indexable page is in the sitemap and has at least
//   one link from another page
// - no page, sitemap, robots.txt or llms file names the old domain
//
// Usage: node scripts/check-out.mjs [outDir]. Prints every problem and exits 1 if there is one.
import { existsSync, readFileSync, readdirSync, statSync } from "node:fs";
import { dirname, join, relative } from "node:path";
import { fileURLToPath } from "node:url";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const out = process.argv[2] ?? join(root, "out");
const SITE = (process.env.NEXT_PUBLIC_SITE_URL ?? "https://handball-intelligence.com").replace(/\/$/, "");
const OLD = ["handball-ai.ch", "handball-ai"];

export function checkOut(dir = out) {
  const problems = [];
  const files = [];
  const walk = (d) => {
    for (const f of readdirSync(d)) {
      const p = join(d, f);
      if (statSync(p).isDirectory()) walk(p);
      else files.push(p);
    }
  };
  walk(dir);

  const decode = (s) =>
    s
      .replace(/&amp;/g, "&")
      .replace(/&lt;/g, "<")
      .replace(/&gt;/g, ">")
      .replace(/&quot;/g, '"')
      .replace(/&#x27;|&#39;/g, "'")
      .replace(/&nbsp;/g, " ");
  const attr = (tag, name) => decode((tag.match(new RegExp(`${name}="([^"]*)"`)) ?? [])[1] ?? "");

  /** @type {Map<string, {title: string, desc: string, canonical: string, alts: Record<string,string>, noindex: boolean, links: Set<string>}>} */
  const pages = new Map();
  for (const f of files) {
    const rel = `/${relative(dir, f)}`;
    if (/\.(html|txt|xml)$/.test(f)) {
      const text = readFileSync(f, "utf8");
      for (const o of OLD) if (text.includes(o)) problems.push(`${rel}: names the old domain «${o}»`);
    }
    if (!f.endsWith("index.html")) continue;
    const path = rel.replace(/index\.html$/, "");
    if (!/^\/(de|fr|en)\//.test(path)) continue; // redirect pages and the language choice
    const html = readFileSync(f, "utf8");
    const head = html.slice(0, html.indexOf("</head>"));
    const noindex = /<meta name="robots" content="[^"]*noindex/.test(head);
    const title = decode((head.match(/<title>([^<]*)<\/title>/) ?? [])[1] ?? "");
    const desc = attr((head.match(/<meta name="description"[^>]*>/) ?? [""])[0], "content");
    const canonical = attr((head.match(/<link rel="canonical"[^>]*>/) ?? [""])[0], "href");
    const alts = {};
    for (const tag of head.match(/<link rel="alternate" hrefLang="[^"]+"[^>]*>/g) ?? []) alts[attr(tag, "hrefLang")] = attr(tag, "href");
    const h1 = (html.match(/<h1[\s>]/g) ?? []).length;
    if (h1 !== 1) problems.push(`${path}: ${h1} h1`);
    const body = html.slice(html.indexOf("<body"));
    const links = new Set(
      [...body.matchAll(/<a [^>]*href="(\/(?:de|fr|en)\/[^"#?]*)/g)].map((m) => m[1]).filter((h) => h !== path),
    );
    pages.set(path, { title, desc, canonical, alts, noindex, links });

    // JSON-LD: parses, and names only what the page shows
    const visible = decode(
      body
        .replace(/<script[\s\S]*?<\/script>/g, " ")
        .replace(/<[^>]+>/g, " ")
        .replace(/\s+/g, " "),
    ).replace(/ ([,.;:!?])/g, "$1");
    const flat = visible.replace(/\s/g, "");
    for (const m of html.matchAll(/<script type="application\/ld\+json">([\s\S]*?)<\/script>/g)) {
      let data;
      try {
        data = JSON.parse(m[1]);
      } catch {
        problems.push(`${path}: JSON-LD does not parse`);
        continue;
      }
      const seen = (s) => flat.includes(String(s).replace(/\s/g, ""));
      const visit = (node) => {
        if (Array.isArray(node)) return node.forEach(visit);
        if (!node || typeof node !== "object") return;
        const t = node["@type"];
        const shown = [];
        if (t === "Question") shown.push(node.name, node.acceptedAnswer?.text);
        if (t === "HowToStep") shown.push(node.name, node.text);
        if (t === "ListItem") shown.push(node.name);
        if (t === "Article" || t === "BlogPosting" || t === "TechArticle") shown.push(node.headline);
        for (const s of shown) if (s && !seen(s)) problems.push(`${path}: JSON-LD ${t} not visible: «${String(s).slice(0, 60)}»`);
        if ("aggregateRating" in node || "review" in node) problems.push(`${path}: JSON-LD rating or review`);
        for (const [k, v] of Object.entries(node)) if (!k.startsWith("@") || k === "@graph") visit(v);
      };
      visit(data);
    }
  }

  // titles, descriptions, canonical, hreflang
  const indexable = [...pages.entries()].filter(([, p]) => !p.noindex);
  // unique within a language (the same page in another language may share a name, e.g. «Impressum»)
  const lang = (path) => path.slice(1, 3);
  const count = (key) => indexable.reduce((m, [path, p]) => m.set(`${lang(path)} ${p[key]}`, (m.get(`${lang(path)} ${p[key]}`) ?? 0) + 1), new Map());
  const titles = count("title");
  const descs = count("desc");
  for (const [path, p] of indexable) {
    if (!p.title || p.title.length > 60) problems.push(`${path}: title ${p.title.length} characters «${p.title}»`);
    if (titles.get(`${lang(path)} ${p.title}`) > 1) problems.push(`${path}: title not unique «${p.title}»`);
    if (p.desc.length < 70 || p.desc.length > 160) problems.push(`${path}: description ${p.desc.length} characters`);
    if (descs.get(`${lang(path)} ${p.desc}`) > 1) problems.push(`${path}: description not unique`);
    if (p.canonical !== `${SITE}${path}`) problems.push(`${path}: canonical ${p.canonical}`);
    const codes = Object.keys(p.alts);
    if (!codes.includes("x-default")) problems.push(`${path}: no x-default`);
    if (!Object.values(p.alts).includes(`${SITE}${path}`)) problems.push(`${path}: hreflang does not list the page itself`);
    for (const [code, url] of Object.entries(p.alts)) {
      if (code === "x-default") continue;
      const other = pages.get(url.replace(SITE, ""));
      if (!other) {
        problems.push(`${path}: hreflang ${code} points to a missing page ${url}`);
        continue;
      }
      const a = JSON.stringify(Object.entries(p.alts).sort());
      const b = JSON.stringify(Object.entries(other.alts).sort());
      if (a !== b) problems.push(`${path}: hreflang not reciprocal with ${url}`);
    }
  }

  // sitemap and incoming links
  const sitemapFile = join(dir, "sitemap.xml");
  const sitemap = existsSync(sitemapFile) ? readFileSync(sitemapFile, "utf8") : "";
  const listed = new Set([...sitemap.matchAll(/<loc>([^<]+)<\/loc>/g)].map((m) => m[1].replace(SITE, "")));
  const incoming = new Map();
  for (const [from, p] of pages) for (const to of p.links) if (to !== from) incoming.set(to, (incoming.get(to) ?? 0) + 1);
  for (const [from, p] of pages)
    for (const to of p.links) if (!existsSync(join(dir, to, "index.html"))) problems.push(`${from}: link to a missing page ${to}`);
  for (const [path] of indexable) {
    if (!listed.has(path)) problems.push(`${path}: not in the sitemap`);
    if (!incoming.get(path)) problems.push(`${path}: no link from another page`);
  }
  for (const path of listed) if (pages.get(path)?.noindex) problems.push(`${path}: noindex page in the sitemap`);

  return { problems, pages: pages.size, indexable: indexable.length };
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  if (!existsSync(out)) {
    console.error(`check-out: ${out} does not exist; build first`);
    process.exit(1);
  }
  const { problems, pages, indexable } = checkOut(out);
  for (const p of problems) console.error(`check-out: ${p}`);
  console.log(`check-out: ${pages} pages, ${indexable} indexable, ${problems.length} problems`);
  process.exit(problems.length ? 1 : 0);
}
