# Order Preview Prompt

```text
Prepare an order preview for [TICKER] in the Robinhood Agentic account.

Hard rules:
- Confirm Agentic account buying power first.
- If buying power is $0, stop and do not call review_equity_order.
- Use review_equity_order only if the trade passes the checklist.
- Do not call place_equity_order.
- Stop after showing the reviewed order.
- Wait for my separate explicit "go ahead" before any placement.

Sizing:
- No single stock position above 10% of Agentic account value.
- Enter at 50% of intended size first.
- Use cash account discipline only.
- No options.

Required output before any order preview:
"I am proposing to buy [X shares / $Y] of [TICKER] at [price]. The thesis is
[2 sentences]. The main risk is [1 sentence]. My stop-loss will be set at
[price], which is [Z%] below current price. This represents [%] of the Agentic
account."
```
