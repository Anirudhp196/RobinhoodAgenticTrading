# Robinhood Agentic Trading Workspace

This repo is now a lightweight operating workspace for the official Robinhood
Trading MCP in Cursor.

The old FMP/React/Express screener has been removed. The project is no longer a
local stock-screening app; it is a set of instructions, prompts, and logs for
running a disciplined agentic trading workflow through Robinhood's dedicated
Agentic account.

## Files

- `CLAUDE.md` — master trading-agent playbook and hard rules.
- `AGENTIC_WORKFLOW.md` — operational guide for safe MCP usage.
- `trade-log.md` — accountability log for every placed trade.

## Current Boundaries

- Robinhood MCP may read accounts, positions, portfolio, quotes, watchlists, and
  orders for context.
- Trading is allowed only in the dedicated Agentic account.
- Default behavior is always to ask before any order placement.
- No options, margin trades, or trades in the main Robinhood account.
- Every equity position must have a stop-loss plan.

## Recommended First Workflow

Ask Cursor:

```text
Run the read-only Robinhood agentic research workflow.
Inspect my Agentic account, current buying power, positions, orders, and watchlists.
Do not review, place, cancel, or modify any orders.
Summarize current state and suggest what to monitor next.
```

When you are ready to evaluate a ticker:

```text
Research [TICKER] using Robinhood read-only tools and public market context.
Build the bull case, bear case, catalyst, technical setup, and whether this is
better than simply holding SPY. Do not review or place an order.
```

Only after a candidate passes research should an order preview be considered.
Order placement requires a separate explicit approval.
