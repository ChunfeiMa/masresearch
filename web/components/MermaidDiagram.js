"use client";

import { useEffect, useRef, useState } from "react";

// Renders a Mermaid diagram client-side. Mermaid is dynamically imported so it
// stays out of the initial bundle. Falls back to raw source if render fails.
export default function MermaidDiagram({ code, id }) {
  const ref = useRef(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let active = true;
    if (!code) return;
    (async () => {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          securityLevel: "strict",
          themeVariables: { fontSize: "13px" },
        });
        const gid = `mmd-${id}-${Math.floor(Math.abs(hash(code)))}`;
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
