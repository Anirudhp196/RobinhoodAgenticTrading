# Portfolio Screener — Build Plan

A daily stock-screening tool. It pulls market data, scores a watchlist against
transparent criteria, and surfaces a small number of names worth a closer look —
or (most days) tells me to do nothing. It is a **research assistant, not an
auto-trader.** There is intentionally **no order-execution layer.**

> **Read this first, Claude:** Build this incrementally and confirm each phase
> works before moving on. Do not skip ahead to the UI before the data + scoring
> pipeline runs and is tested. After each phase, run it and show me the output.

---

## Guiding principles (do not violate these)

1. **No execution.** This tool never places trades. It outputs information; I decide.
2. **Bias toward "hold."** A screener that always finds something to buy is
   useless and dangerous. The default daily outcome should be "nothing clears
   the bar." Keep the signal threshold strict.
3. **Buy quality on weakness, never chase hype.** Scoring rewards reasonable
   entry points (modest pullbacks on healthy companies) and penalizes buying at
   52-week highs / overbought RSI. This deliberately fights the overtrading
   instinct.
4. **Every signal must be explainable.** No black-box scores. Each suggestion
   shows the underlying numbers and plain-English reasons.
5. **This is a side dish.** My core strategy is automatic ETF investing. This
   watchlist sits *on top* of that. Keep that framing visible in the UI.
6. **Not financial advice.** Surface this disclaimer in the UI footer.

---

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐     ┌──────────┐
│  Data layer │ ──> │ Scoring layer│ ──> │ Express API │ ──> │ React UI │
│ (fetch)     │     │ (signals)    │     │ (serve JSON)│     │ (realtime)│
└─────────────┘     └──────────────┘     └─────────────┘     └──────────┘
```

### Backend language choice
Use **Node.js + Express** for the API and a **Node-based data/scoring core**.
Rationale: the user explicitly wants an Express API, and keeping the whole
backend in one language (JS/TS) removes the Python<->Node bridge, simplifies
deployment, and makes the parsing optimizations (below) easier to own.

> If you (Claude) judge that a Python scoring core is materially better here,
> you may instead run Python for scoring and have Express shell out to it or
> call it over a local port — but default to all-Node unless there's a real
> reason. Flag the tradeoff to me before splitting languages.

---

## Phase 0 — Project setup

- Initialize: `npm init`, install `express`, `cors`, and a fetch lib if needed.
- Use **TypeScript** for the backend (catches the dumb bugs that lose money-
  adjacent code its credibility). Set up `tsconfig.json`.
- Folder layout:
  ```
  /server
    /src
      dataLayer.ts      # Phase 1
      signals.ts        # Phase 2
      cache.ts          # Phase 3 (parsing/perf)
      api.ts            # Phase 4 (Express)
    config.json         # watchlist + tunable thresholds
  /client               # Phase 5 (React UI)
  ```
- Create `config.json` with: `universe` (array of tickers), `signalThreshold`
  (default 70), scoring `weights` (value/trend/pullback/quality summing to 1),
  and `riskFilters` (maxRsi 75, minMarketCap 2e9, maxPe 60).

**Confirm:** project builds and `npm run dev` starts an empty server.

---

## Phase 1 — Data layer (`dataLayer.ts`)

Fetch ~1 year of daily OHLCV + basic fundamentals (P/E, market cap, profit
margin) per ticker.

- **Data source:** Start with a free provider. Options, in order of preference:
  1. **Financial Modeling Prep** or **Alpha Vantage** free tier (real API,
     stable JSON, free key) — recommended for a clean API.
  2. `yahoo-finance2` npm package (no key, but unofficial and can break).
- Each fetch must **never throw** — return a result object with an optional
  `error` field so one bad ticker doesn't kill the run.
- Fetch sequentially with a small delay, OR batch if the provider supports it.

**Optimize the parsing here (this is the part the user cares about):**
- Parse provider JSON into a **typed, normalized shape** once
  (`{ ticker, closes: number[], pe, marketCap, profitMargin }`), so the scoring
  layer never touches raw provider responses.
- Use typed arrays (`Float64Array`) for the price series if you're computing
  many indicators — avoids GC churn on large universes.
- Validate/coerce types at the boundary; reject NaNs early.

**Confirm:** fetch 3 tickers, log the normalized objects, verify shape.

---

## Phase 2 — Scoring layer (`signals.ts`)

Pure functions, no I/O. Input: normalized stock data. Output: a `Signal`
`{ ticker, score (0-100), reasons[], flags[], metrics }`.

Compute these indicators:
- **Trend:** price vs 200-day moving average. Above = healthy.
- **Pullback:** % below trailing 52wk high. ~5–15% off = sweet spot (good
  entry). ~0% off = flag "buying the top." >15% = flag "check why it's down."
- **RSI(14):** >75 = overbought flag (risk filter, don't score-reward it).
- **Value:** score inversely to P/E around a fair band (~15).
- **Quality:** profitable companies score higher (profit margin based).

Final score = weighted sum using `config.weights`. Risk filters add **flags**
but I want them visible, not silently excluded.

**Reference implementation exists** — I have working Python versions of these
exact formulas (RSI, pct-from-high, the weighted score). Ask me for them and
port the math faithfully; they're tested and produce sane results (a quality
name on a 9% dip scored 89/100; an overheated expensive name scored 34/100).

**Confirm:** unit-test scoring with synthetic data — one "good dip" stock and
one "overheated" stock. Assert the good one scores high and the hyped one low.

---

## Phase 3 — Caching & parsing performance (`cache.ts`)

- Cache fetched+normalized data to disk (JSON or SQLite) keyed by
  `ticker + date`. Don't re-hit the API for data you already pulled today.
- On run, only fetch tickers whose cache is stale (older than today).
- Keep a rolling history of daily scores so the UI can chart a ticker's score
  over time later.
- This is where "optimize the backend parsing" pays off: parse-once, cache the
  normalized form, never re-parse raw payloads.

**Confirm:** second run of the same day hits cache, makes zero network calls.

---

## Phase 4 — Express API (`api.ts`)

Endpoints:
- `GET /api/screen` — runs (or returns cached) today's screen; returns the full
  ranked array of signals as JSON.
- `GET /api/screen/:ticker` — single ticker detail + metrics + score history.
- `GET /api/health` — liveness check.
- `POST /api/refresh` — force a fresh fetch (ignore cache).

Details:
- Enable `cors` for the React dev server.
- For **realtime** UI updates, add **Server-Sent Events** at `GET /api/stream`
  that pushes progress as each ticker is fetched/scored (simpler than WebSockets
  and perfect for a one-way progress feed). Fall back to polling if you prefer.
- Return well-typed JSON; never leak raw provider payloads.

**Confirm:** `curl localhost:PORT/api/screen` returns valid JSON.

---

## Phase 5 — React UI (`/client`)

A small, clean dashboard. Vite + React. Keep it genuinely useful, not flashy.

Must-haves:
- **Watchlist table:** ticker, score (color-coded), trend/pullback/RSI at a
  glance, sortable by score.
- **"Today's verdict" banner:** big and honest. If nothing clears the bar, say
  so loudly: *"Nothing meets the bar today. Hold."* Make the boring outcome feel
  like a valid result, not a failure.
- **Detail drawer/panel:** click a ticker → see all reasons, all flags, raw
  metrics, and (later) a small score-history sparkline.
- **Realtime progress:** subscribe to `/api/stream` (SSE); show a progress bar
  as tickers come in.
- **Refresh button:** calls `POST /api/refresh`.
- **Persistent disclaimer footer:** "Not financial advice. Research tool only.
  No trades are placed. Your ETF auto-investing is the real strategy."

Nice-to-haves (later): score history charts, editable watchlist/thresholds from
the UI (writes back to config), CSV export.

**Confirm:** UI loads, shows live data from the API, detail panel works.

---

## Phase 6 — Scheduling (run it daily in the background)

- The user wants this running daily. Options:
  - **macOS/Linux:** a `cron` entry hitting `POST /api/refresh` each morning, OR
    a small `node-cron` job inside the server process.
  - **Windows:** Task Scheduler.
- The server can stay up; `node-cron` triggers a refresh at, say, 30 min after
  market open so it's not chasing the opening volatility.

**Confirm:** scheduled job fires and updates the cached screen.

---

## Stretch / iterate later

- Add a **sentiment risk-filter** (NOT a buy signal): scan recent headlines for
  a ticker; use it only to *flag* "something's blowing up here, investigate"
  rather than to recommend buying on positive buzz. Positive sentiment is
  usually already priced in — treat it as a caution layer, not alpha.
- Backtest the scoring rules against historical data before trusting them.
- Track suggestion outcomes over time to see if the screen actually adds value
  versus just buying the ETF. Be willing to conclude it doesn't.

---

## Definition of done (v1)

- [ ] `npm run dev` starts API + serves the React UI.
- [ ] Hitting the dashboard shows today's screen with real data.
- [ ] Most days it says "hold"; when it surfaces names, each is fully explained.
- [ ] Second run same day uses cache (no redundant API calls).
- [ ] Disclaimer is visible. No execution code exists anywhere.

---

## A note I want kept in the repo

This tool exists to make me *more deliberate*, not more active. If I find myself
trading frequently because of it, it has failed. The single most important
number is `signalThreshold` — when in doubt, raise it.
