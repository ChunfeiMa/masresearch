// Runtime data loading from the statically-served /data/*.json files.
// Cache-busted so the hourly-refreshed JSON is picked up without a hard reload.

export const BASE = process.env.NEXT_PUBLIC_BASE_PATH || "";

export const TOPIC_META = {
  physical_ai: { label: "Physical AI", color: "#f5a524" },
  multi_agent: { label: "Multi-Agent Systems", color: "#a78bfa" },
  vision_ai: { label: "Vision AI", color: "#22d3ee" },
};

export async function loadJSON(name) {
  const res = await fetch(`${BASE}/data/${name}?t=${Date.now()}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${name}: ${res.status}`);
  return res.json();
}

export function topicColor(key) {
  return TOPIC_META[key]?.color || "#94a3b8";
}

export function topicLabel(key) {
  return TOPIC_META[key]?.label || key;
}

export function fmtDate(iso) {
  if (!iso) return "";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso.slice(0, 10);
  }
}
