// Copies Core's ontology view (ontology/B/dashboard.html) into public/atlas.html for the /atlas page.
// The original has no <html>/<body>: only the copy is wrapped, the original is never touched.
// Run after every `python -m atlas.ontology.dashboard`:  node web/scripts/sync-atlas.mjs
import { readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const web = join(dirname(fileURLToPath(import.meta.url)), "..");
const src = join(web, "..", "ontology", "B", "dashboard.html");
const dst = join(web, "public", "atlas.html");

const page = readFileSync(src, "utf8");
const wrapped = /<html[\s>]/i.test(page) ? page : `<!doctype html>\n<html lang="it">\n${page}\n</html>\n`;
writeFileSync(dst, wrapped);
console.log(`wrote ${dst} (${Math.round(wrapped.length / 1024)} KB)`);
