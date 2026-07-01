"use client";

import { useEffect, useRef } from "react";

// Interactive 3D paper graph: the item at the hub, related papers around it.
// Drag rotates the scene (TrackballControls), hover shows the paper title,
// click opens the paper. `outward` flips arrow direction: false = papers cite
// this one (in), true = this paper cites them (out). 3d-force-graph (three.js)
// is dynamically imported so it stays out of the initial bundle.
export default function CitationGraph({ center, citations, accent = "#22d3ee", outward = false }) {
  const ref = useRef(null);
  const instanceRef = useRef(null);

  useEffect(() => {
    let disposed = false;
    (async () => {
      const ForceGraph3D = (await import("3d-force-graph")).default;
      if (disposed || !ref.current) return;

      const nodes = [
        { id: "__center", name: center.title, url: center.url, kind: "center" },
      ];
      const links = [];
      (citations || []).slice(0, 60).forEach((c, i) => {
        const id = "c" + i;
        nodes.push({
          id,
          name: c.year ? `${c.title} (${c.year})` : c.title,
          url: c.arxiv_id ? `https://arxiv.org/abs/${c.arxiv_id}` : c.url,
          kind: "cite",
        });
        // outward: this paper -> reference; inward: citing paper -> this paper
        links.push(outward ? { source: "__center", target: id } : { source: id, target: "__center" });
      });

      const width = ref.current.clientWidth || 640;
      const g = ForceGraph3D()(ref.current)
        .graphData({ nodes, links })
        .width(width)
        .height(380)
        .backgroundColor("#0e1730")
        .nodeLabel("name")
        .nodeVal((n) => (n.kind === "center" ? 10 : 2))
        .nodeColor((n) => (n.kind === "center" ? "#5b8cff" : accent))
        .nodeOpacity(0.95)
        .linkColor(() => "#3a4d78")
        .linkOpacity(0.55)
        .linkWidth(0.6)
        .linkDirectionalArrowLength(3)
        .linkDirectionalArrowRelPos(1)
        .enableNodeDrag(false)
        .showNavInfo(false)
        .onNodeClick((n) => n.url && window.open(n.url, "_blank", "noreferrer"));

      instanceRef.current = g;
    })();

    return () => {
      disposed = true;
      const g = instanceRef.current;
      if (g && typeof g._destructor === "function") {
        try {
          g._destructor();
        } catch {}
      }
      instanceRef.current = null;
    };
  }, [center, citations]);

  return <div className="citegraph" ref={ref} />;
}
