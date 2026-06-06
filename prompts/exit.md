# Exit Prompt — When and How to Sell

```text
Evaluate and prepare an exit for [TICKER] in the Robinhood Agentic account.
Do not place a sell order until I give explicit approval.

---

STEP 1 — Identify the exit trigger

Confirm which trigger applies:

HARD EXITS (strong recommendation to sell, act today)
  □ Stop-loss hit — price has crossed below the level set at entry
  □ Thesis broken — the reason I bought is no longer true
    (examples: guidance cut sharply, key product failure, CEO/fraud news)
  □ Down 20%+ with a clear fundamental explanation from news

SOFT EXITS (flag and discuss, I decide)
  □ RUNNER — position up 40%+ → propose selling 50%, letting 50% run
  □ TRIM — position above 12% of portfolio → propose trimming to 8%
  □ STALE — held 90+ days, less than 10% gain, underperforming SPY
    over same period → opportunity cost argument, discuss before acting

---

STEP 2 — Pre-exit research

Search for news on [TICKER] in the last 72 hours.
Answer explicitly:
- Is the current price move driven by a fundamental change or market noise?
- If fundamental: what changed, and is it reversible?
- If noise: is the thesis still intact? If yes, holding may be correct.

For HARD EXIT triggers: news check still required but should not override
a stop-loss hit. The stop exists to remove emotion from this decision.

---

STEP 3 — Pull position data

Use get_equity_positions to confirm:
- Current shares held
- Cost basis per share
- Total cost basis

Use get_equity_quotes to confirm:
- Current price
- Prior close

Compute:
- Unrealized P&L in $ and %
- Holding period (from watchlist.md Bought date)
- Tax note: if held less than 365 days, gain is short-term (taxed as
  ordinary income). If within 14 days of the 1-year mark and the exit
  is soft (not hard), flag this and recommend waiting unless thesis is broken.

---

STEP 4 — Determine sell size

FULL EXIT (hard triggers, or soft trigger where thesis is clearly broken):
  → Sell 100% of position

PARTIAL EXIT (RUNNER or TRIM triggers):
  → Sell enough shares to bring position to 8% of portfolio for TRIM,
    or sell 50% of shares for RUNNER (let the rest compound)
  → Compute exact share count for each scenario and show both

---

STEP 5 — Pre-exit summary (required before review_equity_order)

Output exactly:
"I am proposing to SELL [X shares / all shares] of [TICKER] at ~$[current price].
Trigger: [exit trigger name].
Reason: [1 sentence].
Expected proceeds: $[X].
P&L on this position: [+/-X%] / [+/-$X] over [N days].
vs SPY over same period: SPY [+/-X%].
Tax note: [short-term / long-term / near 1-year mark — consider waiting].
After this sale, cash/buying power becomes: ~$[X].
Type GO to proceed to order preview, or CANCEL to hold."

---

STEP 6 — Order preview (only after GO)

Use review_equity_order to simulate the sell.
Show any pre-trade warnings.
Do NOT call place_equity_order — wait for a second explicit GO.

---

STEP 7 — After execution (once GO is given and order placed)

Update watchlist.md:
- Move [TICKER] from Bought to Dropped
- Record: exit date, exit price, total return %, holding period, vs SPY delta
- Record: which exit trigger fired

This trade history is the only honest way to measure whether this workflow
is adding value over just holding SPY.

```

