"use client";

import { useEffect, useRef, useState } from "react";

// Renders a Mermaid diagram client-side. Mermaid is dynamically imported so it
// stays out of the initial bundle.
//
// Robustness: some diagrams come from an LLM and can be syntactically invalid.
// We (a) initialize with suppressErrorRendering so mermaid never injects its
// "Syntax error … version X" banner into document.body, and (b) parse-first so
// render() is only ever called on valid input. Invalid diagrams fall back to
// showing the raw source instead of breaking the page.
let initialized = false;

async function getMermaid() {
  const mermaid = (await import("mermaid")).default;
  if (!initialized) {
    mermaid.initialize({
      startOnLoad: false,
      theme: "dark",
      securityLevel: "strict",
      suppressErrorRendering: true,
      themeVariables: { fontSize: "13px" },
    });
    initialized = true;
  }
  return mermaid;
}

export default function MermaidDiagram({ code, id }) {
  const ref = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    if (!code) return;
    setFailed(false);
    (async () => {
      try {
        const mermaid = await getMermaid();
        const gid = `mmd-${id}-${Math.floor(Math.abs(hash(code)))}`;
        await mermaid.parse(code); // throws on invalid — never reaches render()
        const { svg } = await mermaid.render(gid, code);
        if (active && ref.current) ref.current.innerHTML = svg;
      } catch {
        if (active) setFailed(true);
      }
    })();
    return () => {
      active = false;
    };
  }, [code, id]);

  if (!code) return null;
  if (failed) return <pre className="mermaid-fallback">{code}</pre>;
  return <div className="mermaid-wrap" ref={ref} />;
}

function hash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return h;
}
