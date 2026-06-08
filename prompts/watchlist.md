# Watchlist — Active Research Parking Lot

This file is the agent's working memory between sessions. Every name that gets a "Watch" verdict from ticker-research.md lives here until it either graduates to an order preview or gets dropped.

The agent reads this file at the start of every discovery session to avoid re-researching names already in the pipeline.

---

## How to use

**Adding a name:** after ticker-research.md returns "Watch", the agent appends a row to the Active Watch section below with: date added, ticker, one-sentence reason, and the price at time of research.

**Graduating a name:** when a watched name becomes compelling enough for an order preview, move it from Active Watch to the Graduated section and run order-preview.md.

**Dropping a name:** if a watched name deteriorates (thesis broken, earnings miss, price ran away), move it to Dropped with a one-line reason. Don't delete — the history is useful for calibrating future research.

**Bought:** once an order executes, move from Graduated to Bought with entry price and stop-loss level. This becomes the source of truth for monitor.md.

---

## Active Watch


| Added | Ticker | Reason (1 sentence) | Price at research | Next check |
| ----- | ------ | ------------------- | ----------------- | ---------- |
| Jun 6, 2026 | AVGO | Post-earnings selloff on Google dual-sourcing fears; fundamentals strong but needs news verification before buying. | ~$385 | After CPI (Jun 10) + news check |
| Jun 6, 2026 | TSM | AI foundry demand intact but stock still near ATH; wait for deeper pullback or post-CPI clarity. | ~$412 | Pullback to $385–390 or after CPI |


---

## Graduated (approved for order preview, not yet bought)

**Orders placed 2026-06-08 (queued for Mon regular session):** NOW, SOXX, HOOD, MRVL, UBER @ $20 each. Move to Bought after fill; place stops immediately.

| Approved | Ticker | Research summary | Target entry | Stop-loss |
| -------- | ------ | ---------------- | ------------ | --------- |
| Jun 8, 2026 | NOW | SaaS rebound; beat/raise Q1; AI Assist target $1.5B; ~47% off highs; diversifies from main book. | $20 market @ ~$112 | $103.25 |
| Jun 8, 2026 | SOXX | Semi ETF with 8% single-name caps; broad AI/semi exposure without picking one memory name. | $20 market @ ~$546 | $502.50 |
| Jun 8, 2026 | HOOD | Fintech diversifier; event contracts + options growing; crypto rev weak but not thesis-breaking. | $20 market @ ~$82 | $75.75 |
| Jun 8, 2026 | MRVL | AI datacenter networking/custom silicon; record Q1 + raised FY27 guide; wait for regular session (avoid chasing pre-market pop). | $20 market @ ~$276 | $254.00 |
| Jun 8, 2026 | UBER | Platform compounder near range low; bookings +21%, Q2 EPS guide +30%+; zero overlap with main/Roth. | $20 market @ ~$71 | $65.00 |


---

## Bought (open positions sourced through this workflow)


| Bought | Ticker | Shares | Entry price | Stop-loss | Thesis |
| ------ | ------ | ------ | ----------- | --------- | ------ |
| —      | —      | —      | —           | —         | —      |


---

## Dropped


| Dropped | Ticker | Reason dropped | Price when dropped |
| ------- | ------ | -------------- | ------------------ |
| Jun 8, 2026 | MU | Swapped for UBER in $100 basket — extended near highs, Jun 24 earnings binary, cyclical memory risk. | ~$880 |


---

## Agent instructions for this file

At the start of every `discover.md` run:

- Read Active Watch — do not re-surface these names as new discoveries
- Flag any Active Watch names that have been sitting for more than 14 days without an order preview — prompt me to either act or drop them
- Flag any Graduated names not yet bought after 7 days — market has moved, re-run ticker-research.md before proceeding

At the start of every `monitor.md` run:

- Cross-reference Bought section against get_equity_positions
- Any position in Bought but not in get_equity_positions was closed — move it to Dropped with exit note

