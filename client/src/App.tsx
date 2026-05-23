import { useEffect, useState } from "react";
import { getDiscovery, getScreen, getTicker, refresh } from "./api";
import type { DiscoveryEntry, DiscoveryPayload } from "./api";
import type { ScreenPayload, Signal, TickerDetail } from "./types";

type Mode = "watchlist" | "discovery";

export default function App() {
  const [mode, setMode] = useState<Mode>("watchlist");

  // Watchlist state
  const [watchData, setWatchData] = useState<ScreenPayload | null>(null);
  const [watchLoading, setWatchLoading] = useState(true);
  const [watchError, setWatchError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Discovery state (lazy: only fetches when first selected)
  const [discoData, setDiscoData] = useState<DiscoveryPayload | null>(null);
  const [discoLoading, setDiscoLoading] = useState(false);
  const [discoError, setDiscoError] = useState<string | null>(null);

  const [selected, setSelected] = useState<TickerDetail | null>(null);

  useEffect(() => {
    getScreen()
      .then(setWatchData)
      .catch((e) => setWatchError(String(e)))
      .finally(() => setWatchLoading(false));
  }, []);

  // Lazy-load discovery the first time the tab is opened.
  useEffect(() => {
    if (mode === "discovery" && discoData === null && !discoLoading && !discoError) {
      setDiscoLoading(true);
      getDiscovery()
        .then(setDiscoData)
        .catch((e) => setDiscoError(String(e)))
        .finally(() => setDiscoLoading(false));
    }
  }, [mode, discoData, discoLoading, discoError]);

  async function onRefreshWatchlist() {
    setRefreshing(true);
    setWatchError(null);
    try {
      setWatchData(await refresh());
    } catch (e) {
      setWatchError(String(e));
    } finally {
      setRefreshing(false);
    }
  }

  async function onRefreshDiscovery() {
    setDiscoLoading(true);
    setDiscoError(null);
    setDiscoData(null);
    try {
      setDiscoData(await getDiscovery());
    } catch (e) {
      setDiscoError(String(e));
    } finally {
      setDiscoLoading(false);
    }
  }

  async function onSelect(ticker: string) {
    try {
      setSelected(await getTicker(ticker));
    } catch (e) {
      // Discovery tickers may not be in the watchlist universe — detail endpoint
      // currently restricts to watchlist. Silently skip for now.
      console.warn("detail unavailable:", e);
    }
  }

  return (
    <div className="app">
      <header>
        <h1>Watchlist Screener</h1>
        <nav className="tabs">
          <button
            className={mode === "watchlist" ? "tab tab-active" : "tab"}
            onClick={() => setMode("watchlist")}
          >
            Watchlist
          </button>
          <button
            className={mode === "discovery" ? "tab tab-active" : "tab"}
            onClick={() => setMode("discovery")}
          >
            Discovery (S&P 500)
          </button>
        </nav>
        {mode === "watchlist" ? (
          <button onClick={onRefreshWatchlist} disabled={refreshing}>
            {refreshing ? "Refreshing…" : "Refresh"}
          </button>
        ) : (
          <button onClick={onRefreshDiscovery} disabled={discoLoading}>
            {discoLoading ? "Scanning…" : "Re-scan"}
          </button>
        )}
      </header>

      {mode === "watchlist" ? (
        <WatchlistView
          data={watchData}
          loading={watchLoading}
          error={watchError}
          onSelect={onSelect}
        />
      ) : (
        <DiscoveryView
          data={discoData}
          loading={discoLoading}
          error={discoError}
          onSelect={onSelect}
        />
      )}

      {selected && (
        <DetailDrawer detail={selected} onClose={() => setSelected(null)} />
      )}

      <footer className="disclaimer">
        Not financial advice. Research tool only. No trades are placed. Your
        ETF auto-investing is the real strategy.
      </footer>
    </div>
  );
}

function WatchlistView({
  data,
  loading,
  error,
  onSelect,
}: {
  data: ScreenPayload | null;
  loading: boolean;
  error: string | null;
  onSelect: (t: string) => void;
}) {
  if (loading) return <div className="state">Loading watchlist…</div>;
  if (error) return <div className="state error">Error: {error}</div>;
  if (!data) return <div className="state">No data.</div>;

  const qualified = data.signals.filter(
    (s) => s.error === null && s.score >= data.threshold
  );
  const verdictTone = qualified.length === 0 ? "hold" : "active";

  return (
    <>
      <section className={`verdict verdict-${verdictTone}`}>
        <div className="verdict-headline">{data.verdict}</div>
        <div className="verdict-sub">
          Threshold: {data.threshold} / 100 · Generated {data.generated_at}
        </div>
      </section>
      <SignalTable
        signals={data.signals}
        threshold={data.threshold}
        onSelect={onSelect}
      />
    </>
  );
}

function DiscoveryView({
  data,
  loading,
  error,
  onSelect,
}: {
  data: DiscoveryPayload | null;
  loading: boolean;
  error: string | null;
  onSelect: (t: string) => void;
}) {
  if (loading) {
    return (
      <div className="state">
        Scanning today's S&P 500 slice…
        <div className="state-sub">
          Rolling-scan mode: ~50 tickers per day on FMP free tier.
          Full coverage takes ~10 days. Each call scans today's slice and
          merges it with previously-scored names.
        </div>
      </div>
    );
  }
  if (error) return <div className="state error">Error: {error}</div>;
  if (!data) return <div className="state">Click "Discovery" to scan.</div>;

  const tone = data.qualifiers_count === 0 ? "hold" : "active";
  const coveragePct = ((data.scored_count / data.universe_size) * 100).toFixed(0);

  return (
    <>
      <section className={`verdict verdict-${tone}`}>
        <div className="verdict-headline">{data.verdict}</div>
        <div className="verdict-sub">
          Threshold: {data.threshold} / 100 · Coverage:{" "}
          {data.scored_count}/{data.universe_size} ({coveragePct}%) · Slice{" "}
          {data.slice_today}/{data.total_slices} today · Generated{" "}
          {data.generated_at}
        </div>
      </section>
      <DiscoveryTable
        entries={data.entries}
        threshold={data.threshold}
        onSelect={onSelect}
      />
    </>
  );
}

function DiscoveryTable({
  entries,
  threshold,
  onSelect,
}: {
  entries: DiscoveryEntry[];
  threshold: number;
  onSelect: (t: string) => void;
}) {
  return (
    <table className="watchlist">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Score</th>
          <th>RSI</th>
          <th>% off 52w high</th>
          <th>Price</th>
          <th>Last scored</th>
          <th>Flags</th>
        </tr>
      </thead>
      <tbody>
        {entries.map((e) => (
          <tr
            key={e.ticker}
            onClick={() => onSelect(e.ticker)}
            className={
              e.error
                ? "row-error"
                : e.score >= threshold
                ? "row-pass"
                : "row-skip"
            }
          >
            <td>{e.ticker}</td>
            <td><ScoreCell s={e} threshold={threshold} /></td>
            <td>{fmt(e.metrics?.rsi, 1)}</td>
            <td>{fmtPct(e.metrics?.pct_from_high)}</td>
            <td>{fmt(e.metrics?.current_price, 2, "$")}</td>
            <td className="staleness">{daysAgo(e.last_scored)}</td>
            <td>
              {e.flags.map((f) => (
                <span key={f} className="flag">{f}</span>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function daysAgo(iso: string): string {
  const then = new Date(iso + "T00:00:00").getTime();
  const now = Date.now();
  const days = Math.round((now - then) / 86400000);
  if (days <= 0) return "today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
}

function SignalTable({
  signals,
  threshold,
  onSelect,
}: {
  signals: Signal[];
  threshold: number;
  onSelect: (t: string) => void;
}) {
  return (
    <table className="watchlist">
      <thead>
        <tr>
          <th>Ticker</th>
          <th>Score</th>
          <th>RSI</th>
          <th>% off 52w high</th>
          <th>Price</th>
          <th>Flags</th>
        </tr>
      </thead>
      <tbody>
        {signals.map((s) => (
          <tr
            key={s.ticker}
            onClick={() => onSelect(s.ticker)}
            className={
              s.error
                ? "row-error"
                : s.score >= threshold
                ? "row-pass"
                : "row-skip"
            }
          >
            <td>{s.ticker}</td>
            <td>
              <ScoreCell s={s} threshold={threshold} />
            </td>
            <td>{fmt(s.metrics?.rsi, 1)}</td>
            <td>{fmtPct(s.metrics?.pct_from_high)}</td>
            <td>{fmt(s.metrics?.current_price, 2, "$")}</td>
            <td>
              {s.flags.map((f) => (
                <span key={f} className="flag">
                  {f}
                </span>
              ))}
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function ScoreCell({ s, threshold }: { s: Signal; threshold: number }) {
  if (s.error) return <span className="score-error">—</span>;
  const cls =
    s.score >= threshold
      ? "score-high"
      : s.score >= threshold - 15
      ? "score-mid"
      : "score-low";
  return <span className={cls}>{s.score.toFixed(1)}</span>;
}

function DetailDrawer({
  detail,
  onClose,
}: {
  detail: TickerDetail;
  onClose: () => void;
}) {
  const { signal: s, history } = detail;
  return (
    <div className="drawer-backdrop" onClick={onClose}>
      <aside className="drawer" onClick={(e) => e.stopPropagation()}>
        <header>
          <h2>{s.ticker}</h2>
          <button onClick={onClose}>×</button>
        </header>
        <div className="drawer-score">
          {s.error ? `Error: ${s.error}` : `${s.score.toFixed(1)} / 100`}
        </div>
        {s.reasons.length > 0 && (
          <section>
            <h3>Reasons</h3>
            <ul>
              {s.reasons.map((r) => (
                <li key={r}>{r}</li>
              ))}
            </ul>
          </section>
        )}
        {s.flags.length > 0 && (
          <section>
            <h3>Flags</h3>
            <ul>
              {s.flags.map((f) => (
                <li key={f} className="flag-item">
                  {f}
                </li>
              ))}
            </ul>
          </section>
        )}
        <section>
          <h3>Metrics</h3>
          <dl className="metrics">
            <dt>Current price</dt>
            <dd>{fmt(s.metrics?.current_price, 2, "$")}</dd>
            <dt>200-day MA</dt>
            <dd>{fmt(s.metrics?.ma200, 2, "$")}</dd>
            <dt>RSI(14)</dt>
            <dd>{fmt(s.metrics?.rsi, 1)}</dd>
            <dt>% off 52w high</dt>
            <dd>{fmtPct(s.metrics?.pct_from_high)}</dd>
          </dl>
        </section>
        {history.length > 1 && (
          <section>
            <h3>Score history ({history.length} day{history.length === 1 ? "" : "s"})</h3>
            <Sparkline history={history} />
          </section>
        )}
      </aside>
    </div>
  );
}

function Sparkline({ history }: { history: { date: string; score: number }[] }) {
  const w = 320;
  const h = 60;
  const scores = history.map((p) => p.score);
  const min = Math.min(0, ...scores);
  const max = Math.max(100, ...scores);
  const points = history
    .map((p, i) => {
      const x = (i / Math.max(1, history.length - 1)) * w;
      const y = h - ((p.score - min) / (max - min)) * h;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  return (
    <svg width={w} height={h} className="sparkline">
      <polyline points={points} fill="none" stroke="#3b82f6" strokeWidth="2" />
    </svg>
  );
}

function fmt(
  v: number | null | undefined,
  digits: number,
  prefix = ""
): string {
  return v == null ? "—" : `${prefix}${v.toFixed(digits)}`;
}

function fmtPct(v: number | null | undefined): string {
  return v == null ? "—" : `${(v * 100).toFixed(1)}%`;
}
