# Robinhood Agent — Master Workflow

This is the single entry point for every session. It sequences the other files in the right order and tells you exactly which file to invoke at each step. Never skip steps. Never place an order without completing the step before it.

```
FILE MAP
────────────────────────────────────────────────────────
account-snapshot.md   → where am I right now?
discover.md           → what's worth researching today?
ticker-research.md    → is this specific name worth buying?
watchlist.md          → parking lot between Watch and order preview
order-preview.md      → final pre-trade check before placement
monitor.md            → daily health check on open positions
exit.md               → when and how to sell
WORKFLOW.md           → this file — orchestrates all of the above
────────────────────────────────────────────────────────

```

---

## Daily workflow — run in this order every session

### Step 1 — Snapshot (always first)

> Invoke: `account-snapshot.md`

Run this before anything else. You need to know your buying power, current positions, and any open orders before making any other decision. If buying power is $0, skip to Step 4 (monitor only).

Output to look for:

- Buying power available
- Any positions near a stop-loss level (flag immediately)
- Any open orders still pending from a prior session

---

### Step 2 — Monitor open positions (always second)

> Invoke: `monitor.md`

Check the health of everything you already own before looking for anything new. The worst habit in investing is ignoring your existing portfolio while chasing new names. Run this even if you don't intend to sell anything today.

Output to look for:

- Any STOP ALERT or TRIM CANDIDATE flags
- Thesis still intact for each position?
- If a position needs action → jump to `exit.md` before continuing

---

### Step 3 — Discovery (only if buying power > $0 and no urgent exits)

> Invoke: `discover.md`

This generates a fresh shortlist of tickers worth researching today. It is a broad pass — it does not commit to buying anything. Every name it surfaces goes into one of two places: `watchlist.md` (not yet) or straight to `ticker-research.md` (looks compelling enough to dig in now).

---

### Step 4 — Research shortlisted names

> Invoke: `ticker-research.md` with [TICKER] filled in

Run once per candidate from Step 3. The file ends with a forced decision: Ignore / Watch / Research further / Prepare order preview.

- Ignore → drop it, do not add to watchlist
- Watch → add to `watchlist.md` with today's date and reason
- Research further → run `ticker-research.md` again with more specific questions
- Prepare order preview → proceed to Step 5

---

### Step 5 — Order preview (only for names that cleared Step 4)

> Invoke: `order-preview.md` with [TICKER] filled in

This is the last gate before any money moves. The file explicitly does NOT place a trade — it simulates and stops. Review the output carefully:

- Does the sizing make sense given current portfolio weight?
- Is the stop-loss level realistic or just arbitrary?
- Are there any pre-trade warnings from `review_equity_order`?

If everything looks right, give explicit "go ahead" to place the order. If anything looks off, go back to Step 4 or drop the name entirely.

---

### Step 6 — Log the trade

> Update: `watchlist.md` (move from Watch to Bought, add entry price)

Every completed buy gets logged immediately with: date, ticker, shares, price, thesis in one sentence, stop-loss level. Do this before closing the session.

---

## Weekly workflow (run Sunday evening or Monday pre-market)

1. Run `account-snapshot.md`
2. Run `monitor.md` — full weekly review mode (see monitor.md for weekly prompt)
3. Review `watchlist.md` — any Watch names that have gotten more or less compelling since you added them?
4. Compare portfolio return to SPY over trailing 30 days. Log the delta.
5. Ask: is the strategy working? If satellite picks are consistently underperforming SPY, reduce their allocation next month.

---

## Hard rules that apply across all files

- Never skip the account snapshot. You need to know your buying power.
- Never go straight to order-preview without running ticker-research first.
- Never place a trade without a defined stop-loss level.
- Never hold a position that has broken its original thesis just because it hasn't hit the stop yet. Thesis break = exit, regardless of price.
- Maximum 5 open satellite positions at one time. More than that is impossible to monitor well.
- One session = one new position maximum. Do not buy multiple names in a single sitting. Markets will still be there tomorrow.

