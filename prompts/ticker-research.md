# Ticker Research Prompt

```text
Research [TICKER] for the Robinhood Agentic account.

Use Robinhood MCP read-only tools and public market context. Do not review,
place, cancel, or modify any orders.

Work through:
1. Agentic account context: buying power, existing exposure, current positions.
2. Current quote and recent price context for [TICKER].
3. Benchmark comparison: why might [TICKER] beat SPY on a risk-adjusted basis?
4. Bull case: what has to be true for this to work?
5. Bear case: what goes wrong, and what is realistic downside?
6. Catalyst: why now rather than later?
7. Technical check: 200-day trend, distance from highs, RSI/overbought risk if available.
8. Risk fit: position sizing, sector concentration, and whether a hedge is needed.

End with one of:
- Ignore
- Watch
- Research further
- Prepare order preview

Do not place trades.
```
