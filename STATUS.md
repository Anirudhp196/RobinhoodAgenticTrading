# Status & Roadmap

Snapshot of where the screener is and what's left. Companion to [CLAUDE.md](CLAUDE.md)
(which is the original spec — read that first if you're new here).

Last updated: 2026-05-23.

---

## Where we are

### ✅ Complete and verified working

| Phase | What it does | Key files |
|---|---|---|
| 0 — Scaffold | TS + Python projects, ports 8000 / 3000 / 5173 | [server/](server/), [scoring/](scoring/), [client/](client/) |
| 1 — Data layer | FMP `/stable/` fetcher, TTL JSON cache (prices daily / fundamentals weekly), `NormalizedStock` boundary type | [scoring/src/fmp_client.py](scoring/src/fmp_client.py), [scoring/src/cache.py](scoring/src/cache.py), [scoring/src/data_layer.py](scoring/src/data_layer.py) |
| 2 — Scoring | 4 weighted components (trend, pullback, value, quality) + Wilder RSI; risk filters add flags only; reasons attached to every signal | [scoring/src/signals.py](scoring/src/signals.py), [scoring/tests/test_signals.py](scoring/tests/test_signals.py) — 10/10 passing |
| 3 — Cache + history | Score history persisted in `cache/score_history.json` (rolling 365 days, deduped per day) | [scoring/src/cache.py:51](scoring/src/cache.py#L51) |
| 4 — APIs | FastAPI: `/screen`, `/screen/{ticker}`, `/refresh`, `/stream` (SSE), `/discover`. Express proxies all + forwards SSE | [scoring/src/api.py](scoring/src/api.py), [server/src/api.ts](server/src/api.ts) |
| 5 — React UI | Watchlist + Discovery tabs, verdict banner, detail drawer (reasons/flags/metrics/sparkline), refresh, dark theme | [client/src/App.tsx](client/src/App.tsx), [client/src/styles.css](client/src/styles.css) |
| 6 — Cron | `node-cron` daily refresh at 10:00 ET (weekdays) on the server | [server/src/api.ts:80](server/src/api.ts#L80) |
| + Discovery mode | Rolling S&P 500 scan: 17 slices × ~30 tickers/day; persistent score store; tab in UI with "last scored" staleness column | [scoring/src/discovery.py](scoring/src/discovery.py), [scoring/src/sp500.py](scoring/src/sp500.py) |

### Current data state

- **Watchlist** (16 tickers): NVDA 83.7, XOM 83.4, JNJ 81.3, JPM 81.3, GOOGL 78.9 cleared the 70 bar.
- **Discovery store**: 79/503 S&P 500 names scored. Only **TGT** (79.7) cleared the bar.

### How to run

Three terminals (see also [README in this file](#running-locally) below):

```bash
# T1 — scoring
cd scoring && source venv/bin/activate
uvicorn src.api:app --reload --port 8000

# T2 — server
cd server && npm run dev

# T3 — client
cd client && npm run dev   # then open http://localhost:5173
```

---

## What's left

Priorities reflect what'll actually make the tool better, not just what's unfinished. Roughly ordered.

### Soon (next few sessions)

1. **Watch the threshold (currently 50).** Lowered from 70 → 50 on 2026-05-23 — intentional deviation from CLAUDE.md's *"when in doubt, raise it."* At 50 the watchlist surfaces 10/16 names, which means the screener is now saying "these are plausible candidates" rather than "these clear a strict bar." That's a softer tool: more surface area, less discipline against FOMO. Worth watching the day-to-day to see if this turns into overtrading; if it does, the doc's note still stands — *"if I find myself trading frequently because of it, it has failed."*
2. **Run for a week, then look at the score history.** [cache/score_history.json](scoring/cache/) is collecting daily score points per ticker. After 5-7 days, sanity-check whether scores are stable or thrashing day-to-day. Thrashing = scoring is too noisy.
3. **Rotate your FMP API key.** It leaked into early debug output. Regenerate from FMP's dashboard, paste into `scoring/.env`. No code change.
4. **Anirudh's endpoint practice.** Two endpoints are good "do it yourself" targets — see [feedback-endpoint-practice memory](/Users/anirudh/.claude/projects/-Users-anirudh-Documents-Personal-Projects-Trading-Bot/memory/feedback_endpoint_practice.md):
   - `POST /api/refresh` proxy in [server/src/api.ts](server/src/api.ts) — small, well-bounded Express handler.
   - New FastAPI endpoint `GET /screen/qualified` (returns only signals ≥ threshold) — small, Pydantic + decorator practice.

### Stretch goals from CLAUDE.md not yet built

5. **Sentiment risk-filter.** Doc says: *"scan recent headlines for a ticker; use it only to flag 'something's blowing up here, investigate.'"* Treat as a caution layer, not alpha. Implementation idea: hit a free news API (e.g. NewsAPI free tier or RSS) per qualifying ticker, run a simple negativity check, attach a flag.
6. **Backtest the scoring rules.** Replay historical OHLCV against the scoring engine. Did names that cleared the bar in the past beat the index over the next 30/60/90 days? If not, the engine is decorative and you should know that. Hardest item on this list because of survivorship bias and lookahead bias.
7. **Track suggestion outcomes.** Lighter than a full backtest: every time a ticker clears the bar, record it. 90 days later, compare its return to SPY's return. After a year of data you'll have a real "does this tool add value vs just buying VOO" answer.
8. **Editable watchlist/thresholds from the UI.** Currently `config.json` is the source of truth; UI changes require restart. Not urgent — solo tool.
9. **CSV export.** Trivial. Skip unless you actually want it.

### Operational quirks worth knowing

- **FMP free tier: 250 calls/day.** Watchlist costs ~16/day cold (less when fundamentals cache is warm; the fundamentals cache is *weekly*). Discovery slice costs ~30/day. Combined comfortable budget. If you ever see `402 Payment Required` mid-scan, you've burned through it — wait until the next day.
- **FMP legacy endpoints (`/api/v3/*`) are paywalled.** Use `/stable/` only. Free tier blocks multi-symbol batching — that's why all fetches are per-ticker. Documented in [fmp_client.py:5](scoring/src/fmp_client.py#L5).
- **yfinance is rate-limit-blocked by Yahoo** as of mid-2024 and has stayed that way. Don't re-introduce it. If you ever want batch or wider universe, the realistic paths are Tiingo (free key, 500 req/hr) or FMP Starter ($14/mo).
- **Wikipedia fetch needs httpx, not pandas' default urllib.** macOS Python's missing root certs cause `CERTIFICATE_VERIFY_FAILED`. Handled in [sp500.py:29](scoring/src/sp500.py#L29) by routing through httpx (which uses certifi).
- **SSE through Express works** but uses Node 20's built-in fetch streaming. If you upgrade Node or switch the runtime, retest [server/src/api.ts:60](server/src/api.ts#L60).
- **Discovery store survives partial scans.** If FMP returns 402 mid-scan, already-scored tickers in `cache/discovery_scores.json` stay. Bad-data tickers get `error: "no price data"` in the store and show as `—` in the UI.

### Things that are intentionally NOT here

- **No order execution.** Not in scope, not coming. The doc's principle 1.
- **No paid data tier auto-recommendation.** When/if you upgrade is a deliberate call, not something to default to.
- **No "auto-trader" framing.** The repo says "Trading Bot" but the code is a screener. Don't drift.

---

## Running locally

Quick reference. Full details in conversation history.

```bash
# One-time setup if cloning fresh:
cd scoring && python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # then paste your FMP_API_KEY

cd ../server && npm install
cd ../client && npm install

# Daily — three terminals:
# T1
cd scoring && deactivate 2>/dev/null; source venv/bin/activate
uvicorn src.api:app --reload --port 8000

# T2
cd server && npm run dev

# T3
cd client && npm run dev   # open http://localhost:5173
```

To stop everything: `lsof -ti:8000,3000,5173 | xargs kill -9`

To run tests: `cd scoring && ./venv/bin/pytest tests/`

---

## Definition of done (from CLAUDE.md) — status

- [x] `npm run dev` starts API + serves the React UI
- [x] Hitting the dashboard shows today's screen with real data
- [x] When it surfaces names, each is fully explained (reasons + flags + metrics)
- [x] Second run same day uses cache (no redundant API calls)
- [x] Disclaimer is visible. No execution code exists anywhere.
- [ ] *"Most days it says 'hold'"* — explicitly relaxed on 2026-05-23 (threshold dropped to 50). Anirudh chose surface-area over discipline. Watch in practice.
