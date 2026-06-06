# Discovery Prompt — Growth Stock Sourcing

```text
Find growth stock candidates for the Robinhood Agentic account today.
This is a research-only pass. Do not review, place, cancel, or modify orders.

---

STEP 1 — Session parameters (confirm with me before running)

Ask:
- Sector focus today, or broad market scan?
- Time horizon: short (weeks) / medium (months) / long (12mo+)?
- Risk appetite today: conservative / moderate / aggressive?

---

STEP 2 — Pull account context

Use get_portfolio and get_equity_positions to establish:
- Available buying power
- Current sector exposures (so we don't double up)
- Any sectors already overweight (skip those in the scan)

---

STEP 3 — Web research pass (run all of these, synthesize together)

Search for:
a) Analyst upgrades and raised price targets from the last 14 days —
   focus on upgrades from Neutral/Hold to Buy, not just reiterated Buys
b) Earnings beats with raised forward guidance from the last 30 days —
   these are the strongest fundamental signals
c) Sectors with accelerating revenue growth vs prior 2 quarters —
   look for the bend in the curve, not just "growing"
d) Macro tailwinds creating specific sector winners right now —
   examples: rate environment, regulation shifts, infrastructure spend,
   energy transition, AI infrastructure buildout, reshoring
e) Institutional accumulation signals — any mid/small caps showing up in
   recent 13F filings or unusual volume vs 30-day average

---

STEP 4 — Hard filters (cut before quoting anything)

Remove any candidate that fails ANY of these:
- Market cap below $500M → too illiquid
- Earnings announcement within 10 days → binary event risk, skip
- Up more than 30% in the last 30 days → likely already priced in
- Negative gross margin → not a real business yet
- Currently in my portfolio → already have it, not a new idea
- In a sector already at or above 30% portfolio weight → already overweight

---

STEP 5 — Quote surviving candidates

Call get_equity_quotes on the shortlist (max 20 symbols per call).
For each surviving name compute:
- % below 52-week high (target range: 10-25% off — some weakness, not broken)
- Any unusual gap up/down since prior close (flag if >5% overnight)

Cut any name that is within 3% of its 52-week high → chasing a top.

---

STEP 6 — Output

Produce a ranked table, best candidates first:

| # | Ticker | Sector | Mkt Cap | Signal source | 52wk High | Current | % Off High | Catalyst |
|---|--------|--------|---------|---------------|-----------|---------|------------|----------|

Then for the top 3 only, write:
- Bull case (2 sentences)
- Bear case (1 sentence)
- Why now vs waiting (1 sentence)

For each name, end with a routing decision:
→ Skip (doesn't survive scrutiny)
→ Add to watchlist (interesting but not urgent)
→ Research now (run ticker-research.md on this name next)

---

CONSTRAINTS
- Do not propose order previews or trades from this file
- Do not call review_equity_order or place_equity_order
- Maximum 5 names in the final output table — force the ranking, do not hedge
- If nothing passes the filters today, say so clearly: "No candidates today."
  That is a valid and common outcome. Do not manufacture candidates.

```

