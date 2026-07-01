// Validate Mermaid diagrams using mermaid's own parser.
//
// stdin:  JSON array of { id, code }
// stdout: JSON array of { id, valid, error? }
//
// A jsdom window is shimmed so mermaid (which expects a browser DOM for its
// DOMPurify sanitizer) can initialize under Node.
import { JSDOM } from "jsdom";
import { readFileSync } from "fs";

const dom = new JSDOM("<!DOCTYPE html><body></body>", { pretendToBeVisual: true });
global.window = dom.window;
global.document = dom.window.document;

const mermaid = (await import("mermaid")).default;
mermaid.initialize({ startOnLoad: false, securityLevel: "strict" });

let items = [];
try {
  items = JSON.parse(readFileSync(0, "utf8") || "[]");
} catch {
  process.stdout.write("[]");
  process.exit(0);
}

const out = [];
for (const it of items) {
  if (!it || !it.code) {
    out.push({ id: it?.id, valid: false, error: "empty" });
    continue;
  }
  try {
    await mermaid.parse(it.code);
    out.push({ id: it.id, valid: true });
  } catch (e) {
    const msg = String((e && e.message) || e).split("\n").slice(0, 3).join(" ");
    out.push({ id: it.id, valid: false, error: msg.slice(0, 200) });
  }
}
process.stdout.write(JSON.stringify(out));
