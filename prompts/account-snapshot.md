# Account Snapshot Prompt

```text
Run the read-only Robinhood agentic account snapshot.

Use only read-only Robinhood MCP tools:
- get_accounts
- get_portfolio
- get_equity_positions
- get_equity_orders
- get_watchlists
- get_equity_quotes if needed for position values

Do not call:
- review_equity_order
- place_equity_order
- cancel_equity_order
- any watchlist write tool

Report:
1. Which account is the Agentic account.
2. Agentic buying power, cash, and total value.
3. Open positions and approximate current value.
4. Open/recent agentic orders.
5. Watchlists that might be relevant.
6. One thing to monitor next.
```
