#!/usr/bin/env node
/**
 * Checks the link preview of shared pages as the chats see it (K20, docs/research/R2): fetches
 * each URL with the user agents of WhatsApp, Signal, Telegram, iMessage and Slack and verifies
 * the server HTML <head>: og:title, og:description, og:url, og:site_name, an absolute og:image of
 * 1200 x 630 (a PNG under 300 KB, really 1200 x 630), twitter:card summary_large_image, noindex,
 * and og:video (MP4) for a highlight reel. The <head> must end within the first 300 KB.
 *
 *   node scripts/check-share-head.mjs https://app.example.ch/s/<token> [more urls]
 *
 * Exits 1 when a check fails.
 */

const AGENTS = {
  WhatsApp: "WhatsApp/2.24.6.77 A",
  Signal: "WhatsApp/2",
  Telegram: "TelegramBot (like TwitterBot)",
  iMessage: "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 facebookexternalhit/1.1 Facebot Twitterbot/1.0",
  Slack: "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
};
const MAX_IMAGE = 300 * 1024;
const MAX_HEAD = 300 * 1024;

function metas(head) {
  const out = {};
  for (const m of head.matchAll(/<meta\s+([^>]+?)\/?>/g)) {
    const attrs = Object.fromEntries([...m[1].matchAll(/([\w:-]+)="([^"]*)"/g)].map((a) => [a[1].toLowerCase(), a[2]]));
    const key = attrs.property ?? attrs.name;
    if (key && attrs.content !== undefined) out[key] ??= attrs.content.replaceAll("&amp;", "&").replaceAll("&quot;", '"').replaceAll("&#x27;", "'");
  }
  return out;
}

function pngSize(buf) {
  const sig = buf.subarray(0, 8).toString("hex");
  if (sig !== "89504e470d0a1a0a") return null;
  return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
}

async function check(url) {
  const failures = [];
  const fail = (agent, msg) => failures.push(`${agent}: ${msg}`);
  let summary = null;
  for (const [agent, ua] of Object.entries(AGENTS)) {
    const res = await fetch(url, { headers: { "user-agent": ua, "accept-language": "de-CH,de;q=0.9" }, redirect: "follow" });
    if (!res.ok) {
      fail(agent, `HTTP ${res.status}`);
      continue;
    }
    const html = await res.text();
    const end = html.indexOf("</head>");
    if (end < 0) {
      fail(agent, "no </head>");
      continue;
    }
    if (Buffer.byteLength(html.slice(0, end)) > MAX_HEAD) fail(agent, "<head> ends after 300 KB");
    const m = metas(html.slice(0, end));
    for (const key of ["og:title", "og:description", "og:url", "og:site_name", "og:image", "twitter:card", "twitter:image"]) if (!m[key]) fail(agent, `missing ${key}`);
    if (m["twitter:card"] && m["twitter:card"] !== "summary_large_image") fail(agent, `twitter:card ${m["twitter:card"]}`);
    if (!/noindex/.test(m.robots ?? "")) fail(agent, "not noindex");
    if (m["og:image"] && !/^https?:\/\//.test(m["og:image"])) fail(agent, `og:image not absolute: ${m["og:image"]}`);
    if (m["og:image:width"] !== "1200" || m["og:image:height"] !== "630") fail(agent, `og:image size ${m["og:image:width"]}x${m["og:image:height"]}`);
    if ((m["og:title"] ?? "").length > 90) fail(agent, `og:title too long (${m["og:title"].length})`);
    if ((m["og:description"] ?? "").length > 120) fail(agent, `og:description too long`);
    if (m["og:type"] === "video.other" && !(m["og:video"] && m["og:video:type"] === "video/mp4")) fail(agent, "video page without og:video mp4");
    summary ??= m;
  }
  if (summary?.["og:image"]) {
    const img = await fetch(summary["og:image"], { headers: { "user-agent": AGENTS.WhatsApp } });
    const buf = Buffer.from(await img.arrayBuffer());
    if (!img.ok) fail("image", `HTTP ${img.status}`);
    if (!(img.headers.get("content-type") ?? "").startsWith("image/png")) fail("image", `content-type ${img.headers.get("content-type")}`);
    if (buf.length > MAX_IMAGE) fail("image", `${Math.round(buf.length / 1024)} KB (max 300 KB)`);
    const size = pngSize(buf);
    if (!size || size.width !== 1200 || size.height !== 630) fail("image", `pixels ${size ? `${size.width}x${size.height}` : "not a PNG"}`);
    summary.__image = `${Math.round(buf.length / 1024)} KB, ${size?.width}x${size?.height}`;
  }
  if (summary?.["og:video"]) {
    const v = await fetch(summary["og:video"], { headers: { range: "bytes=0-1" } });
    if (v.status !== 206) fail("video", `range request answered ${v.status}, not 206`);
  }
  return { url, failures, summary };
}

const urls = process.argv.slice(2);
if (!urls.length) {
  console.error("usage: node scripts/check-share-head.mjs <share url> [...]");
  process.exit(2);
}
let bad = 0;
for (const url of urls) {
  const { failures, summary } = await check(url);
  console.log(`\n${url}`);
  if (summary) {
    console.log(`  title        ${summary["og:title"]}`);
    console.log(`  description  ${summary["og:description"]}`);
    console.log(`  site         ${summary["og:site_name"]}`);
    console.log(`  image        ${summary["og:image"]} (${summary.__image ?? "?"})`);
    if (summary["og:video"]) console.log(`  video        ${summary["og:video"]}`);
  }
  for (const f of failures) console.log(`  FAIL ${f}`);
  if (!failures.length) console.log("  ok for WhatsApp, Signal, Telegram, iMessage, Slack");
  bad += failures.length ? 1 : 0;
}
process.exit(bad ? 1 : 0);
