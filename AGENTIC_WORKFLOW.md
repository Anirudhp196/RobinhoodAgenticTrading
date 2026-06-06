# Agentic Workflow

This project is now focused on the official Robinhood Trading MCP.

There is no local trading app and no local order-execution code. Cursor connects
to Robinhood's MCP server, uses the playbook in `CLAUDE.md`, and records any
approved trades in `trade-log.md`.

## Current MCP State

- Robinhood Trading MCP is connected in Cursor as `robinhood-trading`.
- Agentic account is visible and enabled for agent-driven trading.
- Agentic account currently has no funded buying power, no positions, and no agentic orders.

## Safe Operating Modes

### 1. Research Only

Use this when evaluating a screener candidate.

- Allowed MCP tools: accounts, portfolio, positions, orders, quotes, watchlists.
- Disallowed MCP tools: `review_equity_order`, `place_equity_order`, `cancel_equity_order`, watchlist writes.
- Output should end with one of: ignore, watch, research further, or prepare an order preview.

### 2. Order Preview

Use this only after research makes a candidate look reasonable.

- Check Agentic account buying power first.
- If buying power is $0, stop and do not review an order.
- If funded, `review_equity_order` may be used to preview an order.
- Stop after the preview. Do not call `place_equity_order`.

### 3. Trade Placement

Only after the user explicitly says "go ahead" for a specific reviewed order.

- Agentic account only.
- Market/limit equity orders only.
- Stop-loss required for every equity position.
- Log the trade in `trade-log.md`.

## Standard Flow

1. Start with a read-only account snapshot.
2. Research any candidate using portfolio context, quotes, thesis, technicals,
   and comparison against SPY.
3. If the candidate survives research, ask for an order preview.
4. If the preview looks right, give a separate explicit approval to place.
5. Log any executed trade in `trade-log.md`.

## Starter Prompts

### Read-only account snapshot

```text
Run the read-only Robinhood agentic research workflow.
Inspect my Agentic account, current buying power, positions, orders, and watchlists.
Do not review, place, cancel, or modify any orders.
Summarize current state and suggest what to monitor next.
```

### Ticker research

```text
Research [TICKER] using Robinhood read-only tools and public market context.
Build the bull case, bear case, catalyst, technical setup, and whether this is
better than simply holding SPY. Do not review or place an order.
```

### Order preview only

```text
Prepare, but do not place, a Robinhood order-review workflow for [TICKER].
Confirm the Agentic account has buying power first. If buying power is $0, stop.
If funded and the trade passes the checklist, use review_equity_order only.
Do not call place_equity_order.
```

## Hard Stops

- No options.
- No margin.
- No trades in the main Robinhood account.
- No silent rebalancing.
- No orders during the first 15 minutes of market open or final 30 minutes, except stop-loss handling.
- No new trade if the thesis cannot explain why it is better than just holding SPY.
