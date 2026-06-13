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

**Session note (Jun 13):** Path **C** — fund Agentic over the weekend; Monday targets **AVGO** + **XLE** after deposit clears. Re-run `ticker-research.md` before order preview. **NOW** soft stop breached — user to decide exit separately.

| Added | Ticker | Reason (1 sentence) | Price at research | Next check |
| ----- | ------ | ------------------- | ----------------- | ---------- |
| Jun 6, 2026 | AVGO | Q2 AI revenue strong; guidance reset priced in (~23% off highs); custom ASIC thesis intact post-CPI. | ~$382 (Jun 12) | After weekend fund + Mon open; Sep earnings |
| Jun 13, 2026 | XLE | Energy diversifier for Agentic book; whole-share (~$58) enables broker stop; CPI/geo tailwind. | ~$58 (Jun 12) | After weekend fund + Mon open; propose stop ~$53.30 |
| Jun 6, 2026 | TSM | AI foundry demand intact but stock still near ATH; wait for deeper pullback or post-CPI clarity. | ~$422 (Jun 12) | Pullback to $385–390 — skip until target zone |


---

## Graduated (approved for order preview, not yet bought)

| Approved | Ticker | Research summary | Target entry | Stop-loss |
| -------- | ------ | ---------------- | ------------ | --------- |
| —        | —      | —                | —            | —         |


---

## Bought (open positions sourced through this workflow)

**Note (2026-06-08):** All five positions filled as **fractional shares** at the open. Robinhood does **not** allow broker stop orders on fractional positions (`Invalid trigger for fractional order` via MCP). Soft stops below are monitored in `monitor.md`; market exit on stop breach requires agent + user approval.

| Bought | Ticker | Shares | Entry price | Soft stop | Thesis |
| ------ | ------ | ------ | ----------- | --------- | ------ |
| Jun 8, 2026 | NOW | 0.179211 | $111.60 | **$103.25** | SaaS/AI workflow rebound; diversifies from main mega-cap tech. |
| Jun 8, 2026 | SOXX | 0.035075 | $570.20 | **$502.50** | Broad semi ETF; capped single-name weights. |
| Jun 8, 2026 | HOOD | 0.236322 | $84.63 | **$75.75** | Fintech; event contracts + options offset weak crypto. |
| Jun 8, 2026 | MRVL | 0.069285 | $288.66 | **$254.00** | AI datacenter networking/custom silicon. |
| Jun 8, 2026 | UBER | 0.284131 | $70.39 | **$65.00** | Platform compounder near range low; zero main-book overlap. |


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

