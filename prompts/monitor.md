# Monitor Prompt — Daily Position Health Check

```text
Run a health check on all open positions in the Robinhood Agentic account.
Read-only MCP tools only. Do not place, review, or cancel any orders.

---

DAILY MODE (run every morning before market open)

STEP 1 — Pull positions and quotes

Use get_equity_positions to get all open positions with cost basis.
Use get_equity_quotes on all held tickers.
Use get_portfolio for total value and buying power.

For each position compute:
- Current weight as % of total portfolio value
- Unrealized P&L in $ and %
- Distance from stop-loss (look up stop-loss from watchlist.md Bought section)
- Distance from 52-week high (from quote data)

---

STEP 2 — Flag system

Apply these flags and list them prominently at the top of the report:

STOP ALERT     → position within 5% of its stop-loss level
               → action: run exit.md, do not wait
THESIS REVIEW  → position down more than 15% from entry price
               → action: search for news, assess whether thesis is broken
TRIM CANDIDATE → position grown above 12% of portfolio
               → action: flag for trimming to 8%, run exit.md for partial sell
STALE          → position held more than 90 days with less than 10% gain
               → action: compare to SPY return over same period, consider exit
RUNNER         → position up more than 40% from entry
               → action: flag — consider taking 50% off the table

---

STEP 3 — News check for flagged positions only

For any position with a STOP ALERT or THESIS REVIEW flag:
Search for news on that ticker in the last 48 hours.
Answer: is this a fundamental development or market noise?
If fundamental → escalate to exit.md immediately
If noise → note it, hold, re-check tomorrow

---

STEP 4 — Market context (web search)

- SPY and QQQ: 1-day and 5-day performance
- VIX current level. Flag if above 22.
- Any macro events today or this week: Fed, CPI, major earnings that
  could move the broader market or specific sectors I'm exposed to

---

STEP 5 — Daily summary output

Format exactly as follows:

════════════════════════════════════════
DAILY MONITOR — [DATE] — [TIME]
════════════════════════════════════════

PORTFOLIO
  Total value:    $X
  Cash/BP:        $X
  Open positions: N

ALERTS ⚠
  [TICKER] — STOP ALERT: price $X, stop at $X ([Z]% away) → run exit.md
  [TICKER] — TRIM CANDIDATE: [X]% of portfolio → flag for partial sell

POSITIONS
  [TICKER]  +X.X% from entry | $X unrealized | [X]% of portfolio | No flags
  [TICKER]  -X.X% from entry | $X unrealized | [X]% of portfolio | THESIS REVIEW

MARKET
  SPY: [+/-X%] today | [+/-X%] 5d
  QQQ: [+/-X%] today | [+/-X%] 5d
  VIX: [X] [NORMAL / ELEVATED / HIGH]
  Events this week: [list or "none"]

RECOMMENDED ACTION
  [One sentence. Either a specific action or "No action needed today."]
════════════════════════════════════════

Do not place any orders. Surface flags only.

---

WEEKLY MODE (run Sunday evening or Monday pre-market)
Add the following to the daily output above:

WEEKLY REVIEW
- Portfolio return vs SPY over trailing 7 days: [+/-X%] vs [+/-X%]
- Portfolio return vs SPY over trailing 30 days: [+/-X%] vs [+/-X%]
- Weakest position: [TICKER] — is the original thesis still intact? [Yes/No/Unclear]
- All stop-losses confirmed active: [Yes / Missing: TICKER, TICKER]
- Allocation drift: [any position or sector above target weight?]
- Watchlist.md: any Watch names sitting stale for 14+ days?
- One thing to do this week:
- One thing NOT to do this week:

```

