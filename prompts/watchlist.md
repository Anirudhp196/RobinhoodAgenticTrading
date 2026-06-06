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
| —     | —      | —                   | —                 | —          |


---

## Graduated (approved for order preview, not yet bought)


| Approved | Ticker | Research summary | Target entry | Stop-loss |
| -------- | ------ | ---------------- | ------------ | --------- |
| —        | —      | —                | —            | —         |


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

