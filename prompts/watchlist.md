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


| Approved | Ticker | Research summary | Target entry | Stop-loss |
| -------- | ------ | ---------------- | ------------ | --------- |
| Jun 6, 2026 | UBER | Platform compounder near 52-week low; bookings +21%, Q2 EPS guide +30%+; zero overlap with main/Roth books. | ~$70.40 (50% scale-in first) | $64.75 |


---

## Bought (open positions sourced through this workflow)


| Bought | Ticker | Shares | Entry price | Stop-loss | Thesis |
| ------ | ------ | ------ | ----------- | --------- | ------ |
| —      | —      | —      | —           | —         | —      |


---

## Dropped


| Dropped | Ticker | Reason dropped | Price when dropped |
| ------- | ------ | -------------- | ------------------ |
| —       | —      | —              | —                  |


---

## Agent instructions for this file

At the start of every `discover.md` run:

- Read Active Watch — do not re-surface these names as new discoveries
- Flag any Active Watch names that have been sitting for more than 14 days without an order preview — prompt me to either act or drop them
- Flag any Graduated names not yet bought after 7 days — market has moved, re-run ticker-research.md before proceeding

At the start of every `monitor.md` run:

- Cross-reference Bought section against get_equity_positions
- Any position in Bought but not in get_equity_positions was closed — move it to Dropped with exit note

