import { useEffect, useState } from "react";
import { getScreen, getTicker, refresh } from "./api";
import type { ScreenPayload, Signal, TickerDetail } from "./types";

export default function App() {
  const [data, setData] = useState<ScreenPayload | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selected, setSelected] = useState<TickerDetail | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    getScreen()
      .then(setData)
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function onRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      setData(await refresh());
    } catch (e) {
      setError(String(e));
    } finally {
      setRefreshing(false);
    }
  }

  async function onSelect(ticker: string) {
    try {
      setSelected(await getTicker(ticker));
    } catch (e) {
      setError(String(e));
    }
  }

  if (loading) return <div className="state">Loading screen…</div>;
  if (error) return <div className="state error">Error: {error}</div>;
  if (!data) return <div className="state">No data.</div>;

  const qualified = data.signals.filter(
    (s) => s.error === null && s.score >= data.threshold
  );
  const verdictTone = qualified.length === 0 ? "hold" : "active";

  return (
    <div className="app">
      <header>
        <h1>Watchlist Screener</h1>
        <button onClick={onRefresh} disabled={refreshing}>
          {refreshing ? "Refreshing…" : "Refresh"}
        </button>
      </header>

      <section className={`verdict verdict-${verdictTone}`}>
        <div className="verdict-headline">{data.verdict}</div>
        <div className="verdict-sub">
          Threshold: {data.threshold} / 100 &middot; Generated {data.generated_at}
        </div>
      </section>

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
          {data.signals.map((s) => (
            <tr
              key={s.ticker}
              onClick={() => onSelect(s.ticker)}
              className={
                s.error
                  ? "row-error"
                  : s.score >= data.threshold
                  ? "row-pass"
                  : "row-skip"
              }
            >
              <td>{s.ticker}</td>
              <td>
                <ScoreCell s={s} threshold={data.threshold} />
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
