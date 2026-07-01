"use client";

import dynamic from "next/dynamic";
import { useEffect, useMemo, useState } from "react";
import MermaidDiagram from "../components/MermaidDiagram";
import Sparkline from "../components/Sparkline";
import { TOPIC_META, fmtDate, loadJSON, topicColor, topicLabel } from "../lib/data";

// three.js graph is heavy + browser-only → load client-side on demand.
const CitationGraph = dynamic(() => import("../components/CitationGraph"), { ssr: false });

const TOPIC_ORDER = ["physical_ai", "multi_agent", "vision_ai"];
const REFRESH_MS = 10 * 60 * 1000; // re-pull the hourly-updated JSON every 10 min

export default function Page() {
  const [items, setItems] = useState([]);
  const [stats, setStats] = useState(null);
  const [meta, setMeta] = useState(null);
  const [error, setError] = useState(null);
  const [topic, setTopic] = useState("all");
  const [sort, setSort] = useState("newest");
  const [selected, setSelected] = useState(null);

  async function refresh() {
    try {
      const [i, s, m] = await Promise.all([
        loadJSON("items.json"),
        loadJSON("stats.json"),
        loadJSON("meta.json"),
      ]);
      setItems(i);
      setStats(s);
      setMeta(m);
      setError(null);
    } catch (e) {
      setError(String(e.message || e));
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, REFRESH_MS);
    return () => clearInterval(t);
  }, []);

  const sorted = useMemo(() => {
    const arr = [...items];
    const cmp = {
      newest: (a, b) => (b.published_at || b.enriched_at || "").localeCompare(a.published_at || a.enriched_at || ""),
      novelty: (a, b) => (b.novelty_score || 0) - (a.novelty_score || 0),
      impact: (a, b) => (b.impact_score || 0) - (a.impact_score || 0),
    }[sort];
    return arr.sort(cmp);
  }, [items, sort]);

  const visible = useMemo(
    () => (topic === "all" ? sorted : sorted.filter((i) => (i.topics || []).includes(topic))),
    [sorted, topic]
  );

  const grouped = useMemo(() => {
    const g = {};
    for (const key of TOPIC_ORDER) g[key] = [];
    for (const it of visible) {
      const t = TOPIC_ORDER.find((k) => (it.topics || []).includes(k)) || "multi_agent";
      g[t].push(it);
    }
    return g;
  }, [visible]);

  const runValues = useMemo(() => {
    if (!stats?.runs) return [];
    return [...stats.runs].reverse().map((r) => r.enriched || 0).slice(-24);
  }, [stats]);

  return (
    <div className="container">
      <Header meta={meta} error={error} />

      {stats && (
        <div className="stats">
          <Stat k="Total items" v={stats.total_items} />
          {TOPIC_ORDER.map((key) => (
            <Stat
              key={key}
              k={TOPIC_META[key].label}
              v={stats.topics?.[key]?.count ?? 0}
              color={topicColor(key)}
            />
          ))}
          <div className="stat trend">
            <div className="trendhead">
              <span className="k">Items / run (last 24)</span>
              <span className="v" style={{ fontSize: 18 }}>{runValues.at(-1) ?? 0}</span>
            </div>
            <Sparkline values={runValues} />
          </div>
        </div>
      )}

      <div className="controls">
        <div className="chips">
          <Chip active={topic === "all"} onClick={() => setTopic("all")} label="All" />
          {TOPIC_ORDER.map((key) => (
            <Chip
              key={key}
              active={topic === key}
              onClick={() => setTopic(key)}
              label={TOPIC_META[key].label}
              color={topicColor(key)}
            />
          ))}
        </div>
        <div className="spacer" />
        <select className="sort" value={sort} onChange={(e) => setSort(e.target.value)}>
          <option value="newest">Newest</option>
          <option value="novelty">Novelty</option>
          <option value="impact">Impact</option>
        </select>
      </div>

      {visible.length === 0 && !error && (
        <div className="empty">No items yet — the pipeline populates this on its next run.</div>
      )}

      {topic === "all"
        ? TOPIC_ORDER.map((key) =>
            grouped[key].length ? (
              <Section key={key} tkey={key} items={grouped[key]} onOpen={setSelected} />
            ) : null
          )
        : visible.length > 0 && (
            <div className="section">
              <div className="grid">
                {visible.map((it) => (
                  <Card key={it.id} item={it} onOpen={setSelected} />
                ))}
              </div>
            </div>
          )}

      <div className="footer">
        MASResearcher · LangGraph multi-agent pipeline · updates hourly via GitHub Actions
      </div>

      {selected && <Drawer item={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}

function Header({ meta, error }) {
  return (
    <div className="header">
      <div className="brand">
        <span className="dot" />
        <h1>MASResearcher</h1>
      </div>
      <div className="sub">
        A multi-agent research feed — Physical AI · Multi-Agent Systems · Vision AI
      </div>
      <div className="meta">
        <span className="live">live</span>
        {meta?.updated_at && <span>updated {fmtDate(meta.updated_at)} {new Date(meta.updated_at).toLocaleTimeString()}</span>}
        {meta?.total_items != null && <span>{meta.total_items} items indexed</span>}
        {error && <span style={{ color: "#f87171" }}>data error: {error}</span>}
      </div>
    </div>
  );
}

function Stat({ k, v, color }) {
  return (
    <div className="stat">
      <div className="k">{k}</div>
      <div className="v" style={color ? { color } : undefined}>{v}</div>
      {color && <div className="bar" style={{ background: color, opacity: 0.5 }} />}
    </div>
  );
}

function Chip({ active, onClick, label, color }) {
  return (
    <button
      className={`chip${active ? " active" : ""}`}
      onClick={onClick}
      style={active ? { background: color || "var(--accent)" } : undefined}
    >
      {label}
    </button>
  );
}

function Section({ tkey, items, onOpen }) {
  return (
    <div className="section">
      <h2>
        <span className="swatch" style={{ background: topicColor(tkey) }} />
        {topicLabel(tkey)}
        <span className="count">· {items.length}</span>
      </h2>
      <div className="grid">
        {items.map((it) => (
          <Card key={it.id} item={it} onOpen={onOpen} />
        ))}
      </div>
    </div>
  );
}

function Card({ item, onOpen }) {
  return (
    <div className="card" onClick={() => onOpen(item)}>
      <div className="top">
        <span className="badge">{item.source_name}</span>
        <span className="date">{fmtDate(item.published_at)}</span>
      </div>
      <h3>{item.title}</h3>
      {item.tldr && <p className="tldr">{item.tldr}</p>}
      {item.tags?.length > 0 && (
        <div className="tags">
          {item.tags.slice(0, 4).map((t) => (
            <span className="tag" key={t}>{t}</span>
          ))}
        </div>
      )}
      <div className="scores">
        <ScoreBar label="Novelty" value={item.novelty_score} color="#5b8cff" />
        <ScoreBar label="Impact" value={item.impact_score} color="#34d399" />
      </div>
    </div>
  );
}

function ScoreBar({ label, value, color }) {
  const pct = Math.round((value || 0) * 100);
  return (
    <div className="score">
      <div className="lbl">{label} · {pct}</div>
      <div className="track">
        <div className="fill" style={{ width: `${pct}%`, background: color }} />
      </div>
    </div>
  );
}

function Citations({ item }) {
  const cites = item.citations || [];
  const count = item.citation_count;
  return (
    <>
      <h4>Cited by{count != null ? ` · ${count}` : ""}</h4>
      {cites.length === 0 ? (
        <p className="muted">
          {count
            ? `${count} citations indexed; citing-paper details unavailable.`
            : "No citations indexed yet — this paper is recent."}
        </p>
      ) : (
        <>
          <CitationGraph center={{ title: item.title, url: item.url }} citations={cites} />
          <div className="cite-hint">Drag to rotate · hover a node for the title · click to open</div>
          <div className="citelist">
            {cites.map((c, i) => (
              <a
                key={i}
                className="citerow"
                href={c.arxiv_id ? `https://arxiv.org/abs/${c.arxiv_id}` : c.url}
                target="_blank"
                rel="noreferrer"
              >
                <span className="citetitle">{c.title}</span>
                <span className="citemeta">
                  {[c.authors?.slice(0, 3).join(", "), c.year].filter(Boolean).join(" · ")}
                </span>
              </a>
            ))}
          </div>
          {count > cites.length && (
            <div className="muted small">Showing {cites.length} of {count} citing papers.</div>
          )}
        </>
      )}
    </>
  );
}

function Drawer({ item, onClose }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  return (
    <>
      <div className="overlay" onClick={onClose} />
      <div className="drawer" role="dialog" aria-modal="true">
        <div className="inner">
          <button className="close" onClick={onClose} aria-label="Close">×</button>
          <div className="tags" style={{ marginBottom: 10 }}>
            {(item.topics || []).map((t) => (
              <span key={t} className="badge" style={{ borderColor: topicColor(t), color: topicColor(t) }}>
                {topicLabel(t)}
              </span>
            ))}
          </div>
          <h2>{item.title}</h2>
          {item.authors?.length > 0 && (
            <div className="authors">{item.authors.slice(0, 8).join(", ")}</div>
          )}
          {item.tldr && <div className="lead">{item.tldr}</div>}

          {item.mermaid && (
            <>
              <h4>Concept diagram</h4>
              <MermaidDiagram code={item.mermaid} id={item.id} />
            </>
          )}

          {item.abstract && (
            <>
              <h4>Abstract</h4>
              <p>{item.abstract}</p>
            </>
          )}
          {item.introduction && (
            <>
              <h4>Introduction</h4>
              <p>{item.introduction}</p>
            </>
          )}
          {item.key_contributions?.length > 0 && (
            <>
              <h4>Key contributions</h4>
              <ul>
                {item.key_contributions.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </>
          )}
          {item.why_it_matters && (
            <>
              <h4>Why it matters</h4>
              <p>{item.why_it_matters}</p>
            </>
          )}

          {item.arxiv_id && <Citations item={item} />}

          {item.tags?.length > 0 && (
            <>
              <h4>Tags</h4>
              <div className="tags">
                {item.tags.map((t) => (
                  <span className="tag" key={t}>{t}</span>
                ))}
              </div>
            </>
          )}

          <a className="src" href={item.url} target="_blank" rel="noreferrer">
            View source ↗
          </a>
        </div>
      </div>
    </>
  );
}
