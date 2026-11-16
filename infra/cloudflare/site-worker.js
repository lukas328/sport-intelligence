// The marketing site (apps/site/out) on Cloudflare Workers with static assets. wrangler.jsonc at the
// repository root points here; Workers Builds deploys it on every push to main.
//
// In front of the files: www goes to the bare domain (301), and addresses without a language
// (/aufnahme/, which the app links to) go to the visitor's language (302, fr, en, else de), which a
// static export cannot do on its own (apps/site/README.md, «Hosting»).
const SECTIONS = new Set([
  "so-funktioniert-es", "aufnahme", "demo", "preise", "hilfe", "ratgeber", "fakten", "ueber-uns",
  "daten", "kontakt", "blog", "agb", "datenschutz", "impressum", "funktionen", "vorlagen", "rechner",
]);

function language(header) {
  for (const part of (header || "").toLowerCase().split(",")) {
    const tag = part.trim().slice(0, 2);
    if (tag === "de" || tag === "fr" || tag === "en") return tag;
  }
  return "de";
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.hostname.startsWith("www.")) {
      url.hostname = url.hostname.slice(4);
      return Response.redirect(url.toString(), 301);
    }
    const first = url.pathname.split("/")[1];
    if (SECTIONS.has(first)) {
      url.pathname = `/${language(request.headers.get("accept-language"))}${url.pathname}`;
      return new Response(null, { status: 302, headers: { location: url.pathname + url.search, vary: "accept-language" } });
    }
    return env.ASSETS.fetch(request);
  },
};
