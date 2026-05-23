import type { ScreenPayload, TickerDetail } from "./types";

const BASE = "http://localhost:3000";

export async function getScreen(): Promise<ScreenPayload> {
  const r = await fetch(`${BASE}/api/screen`);
  if (!r.ok) throw new Error(`screen failed: ${r.status}`);
  return r.json();
}

export async function getTicker(ticker: string): Promise<TickerDetail> {
  const r = await fetch(`${BASE}/api/screen/${ticker}`);
  if (!r.ok) throw new Error(`detail failed: ${r.status}`);
  return r.json();
}

export async function refresh(): Promise<ScreenPayload> {
  const r = await fetch(`${BASE}/api/refresh`, { method: "POST" });
  if (!r.ok) throw new Error(`refresh failed: ${r.status}`);
  return r.json();
}

export type DiscoveryEntry = import("./types").Signal & { last_scored: string };

export type DiscoveryPayload = {
  generated_at: string;
  threshold: number;
  universe_size: number;
  scored_count: number;
  qualifiers_count: number;
  slice_today: number;
  total_slices: number;
  verdict: string;
  entries: DiscoveryEntry[];
};

export async function getDiscovery(): Promise<DiscoveryPayload> {
  // First call is slow (~5-8 min on cold cache). Browser fetch has no client
  // timeout by default so this just waits.
  const r = await fetch(`${BASE}/api/discover`);
  if (!r.ok) throw new Error(`discover failed: ${r.status}`);
  return r.json();
}

export type ProgressEvent =
  | { type: "start"; total: number }
  | { type: "progress"; done: number; total: number; ticker: string; score: number }
  | { type: "done"; payload: ScreenPayload }
  | { type: "error"; error: string };

export function streamProgress(
  onEvent: (e: ProgressEvent) => void
): EventSource {
  const es = new EventSource(`${BASE}/api/stream`);
  es.onmessage = (ev) => {
    try {
      onEvent(JSON.parse(ev.data));
    } catch {
      // ignore malformed
    }
  };
  return es;
}
