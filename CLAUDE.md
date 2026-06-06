# Robinhood Agentic Trading — AI Agent Playbook

This is the master instruction file for my AI trading agent, connected to Robinhood via the official Robinhood Trading MCP. The agent runs in Cursor.

**Goal:** Use the agent to apply a disciplined, research-driven strategy — surfacing hedges, managing portfolio risk, and systematically outperforming my own emotional decision-making. Beating the S&P 500 consistently is the north star, but capital preservation comes first.

> **Read this entire file before taking any action, Claude.** Never place a trade without working through the relevant checklist below. When in doubt, do less and ask.

---

## 0. MCP Setup (do this once)

### Cursor

1. Open **Settings → Cursor Settings → Tools & MCPs → Connect**
2. Add the MCP link: `https://agent.robinhood.com/mcp/trading`
3. Authenticate with your Robinhood credentials when prompted
4. Robinhood will prompt you to open a dedicated **Agentic account** — this is
  separate from your main account. Complete that onboarding.

> Trades can only be placed in the Agentic account, not your main account. The MCP has read access to all your accounts for portfolio context.

### Verify connection

Once connected, run: *"What is my current buying power and portfolio value in my Agentic account?"* — if you get a real answer, the MCP is live.

---

## 1. What the agent is allowed to do


| Action                               | Allowed                        | Notes                             |
| ------------------------------------ | ------------------------------ | --------------------------------- |
| Read portfolio, positions, balances  | Yes                            | All accounts                      |
| Read order history                   | Yes                            | All accounts                      |
| Place market/limit orders            | Yes                            | Agentic account only              |
| Place stop-loss orders               | Yes                            | Required on every equity position |
| Rebalance toward target allocations  | Yes                            | With approval prompt first        |
| Place trades without my confirmation | **Only if explicitly told to** | Default is always ask first       |
| Trade options                        | No                             | Not in scope for this setup       |
| Trade on margin                      | No                             | Cash account discipline only      |


---

## 2. Portfolio philosophy

### The benchmark

The S&P 500 (SPY) is the benchmark. Every position must be justifiable as *better than just holding SPY*. If the agent cannot articulate why a position beats SPY on a risk-adjusted basis, it should not be entered.

### Allocation structure (target)

```
Core (60-70%)      — broad market ETFs: SPY, QQQ, or VTI
Satellite (20-30%) — individual conviction positions, sector tilts
Hedge (5-15%)      — downside protection (see Section 4)
Cash (5%)          — dry powder, never fully deployed
```

### Position sizing rules

- No single stock position > 10% of portfolio
- No single sector > 30% of portfolio
- Add to winners, not losers — never average down more than once
- Scale in: enter at 50% of intended size, add the other 50% on confirmation

---

## 3. Research workflow before any trade

Before placing any order, the agent must work through these steps in order. Do not skip steps. Show the output of each.

### Step 1 — Portfolio context

Ask: *"What are my current positions, allocations, and cash balance in the Agentic account?"* Compute current sector exposure and compare to targets.

### Step 2 — Market context

Pull and summarize:

- Recent SPY/QQQ performance vs last 30 days
- Current VIX level (fear index — above 25 means be cautious)
- Any major macro events in the next 2 weeks (Fed meetings, CPI, earnings)

### Step 3 — Thesis for the candidate

For any stock or ETF being considered, build both sides:

- **Bull case:** what has to be true for this to outperform SPY?
- **Bear case:** what goes wrong, and what is the realistic downside?
- **Catalyst:** what is the specific event or trend that makes *now* a better entry than waiting?

### Step 4 — Technical check

- Is price above or below the 200-day moving average? (above = healthier trend)
- How far is price from its 52-week high? (0-5% off = chasing; 10-20% off = potential entry)
- RSI(14): above 75 = overbought, likely chasing. Below 30 = potentially oversold.
- If all three are flashing "overbought," do not enter. Wait.

### Step 5 — Confirmation prompt

Before placing, output a one-paragraph plain-English summary:

> "I am proposing to buy [X shares / $Y] of [TICKER] at [price]. The thesis is [2 sentences]. The main risk is [1 sentence]. My stop-loss will be set at [price], which is [Z%] below current price. This represents [%] of the Agentic account."

**Wait for explicit "go ahead" before placing the order.**

---

## 4. Hedging strategy

The hedge layer (5-15% of portfolio) is not about being bearish. It is about reducing the severity of drawdowns so I stay invested through volatility instead of panic-selling at the bottom. Use these instruments:

### Standard hedges

- **VIXY or UVXY** — VIX futures ETPs. Only hold when VIX < 18 (cheap insurance). Trim or close when VIX spikes above 30 (insurance has paid out).
- **SQQQ or SH** — inverse ETFs. Short-duration only (days to weeks), not long-term holds. These decay over time due to daily rebalancing.
- **GLD or IAU** — gold. Holds value during dollar weakness and risk-off periods. Target 5% allocation when macro uncertainty is elevated.
- **TLT** — long-duration Treasuries. Negative correlation to equities in traditional risk-off. Use selectively post-2022 given changed rate dynamics.

### When to add hedges

The agent should prompt me to review hedge allocation when:

- VIX is rising and above 20
- SPY is down more than 5% in a rolling 10-day window
- A major macro event (Fed, CPI, earnings season) is within 5 trading days
- Portfolio drawdown from peak exceeds 8%

### Hedge sizing prompt

When flagging a hedge opportunity, format it as:

> "Hedge alert: [reason]. Proposed action: buy [instrument] at [size], which brings hedge allocation to [X%]. This would reduce estimated portfolio beta from [X] to [Y]. Approve?"

---

## 5. Automated strategies (set-and-monitor)

These are standing instructions the agent can execute without per-trade approval, **only after I have explicitly enabled them for a session.**

### Dollar-cost averaging

- Example: *"Buy $200 of SPY every Monday at market open."*
- Agent places the order, logs it, and reports back.
- Must be re-enabled each session — does not carry over automatically.

### Stop-loss management

- Every equity position must have a stop-loss order placed at entry.
- Default stop: 8% below entry price (adjust per position volatility).
- Agent should check weekly: *"Are all open positions in the Agentic account covered by a stop-loss order? If not, flag them."*

### Rebalancing trigger

- When any allocation drifts more than 5% from target, flag it.
- Example: *"Core ETFs have drifted to 75% (target 65%). Prompt me to trim and reallocate."*
- Never rebalance silently. Always present the proposed trades first.

---

## 6. What the agent should never do

- **Never place a trade in my main Robinhood account.** Agentic account only.
- **Never go all-in on a single position.** Max 10% per stock, per rule above.
- **Never chase a stock already up 20%+ in the last month** without an exceptionally strong new catalyst — this is almost always buying the top.
- **Never average down more than once.** If a position is down and you have already added once, stop. Reassess the thesis from scratch before any further action.
- **Never remove a stop-loss to "give it more room."** If the stop gets hit, the thesis was wrong. Exit and move on.
- **Never act on a single news headline.** Cross-check at least 2 sources and check whether the information is actually new vs. already priced in.
- **Never place a trade in the first 15 minutes of market open or last 30 minutes** unless it is a stop-loss being triggered. Spreads are wide, volatility is noise.

---

## 7. Daily agent prompts (run these on a schedule)

Paste these into Cursor each morning. Agent executes in order.

```
Morning briefing (run at 9:00 AM before market open):

1. Pull my current Agentic account positions and buying power.
2. Summarize overnight news for any tickers I currently hold.
3. Flag any positions that are within 3% of their stop-loss price.
4. Check VIX level. If above 22, flag it and suggest reviewing hedge allocation.
5. If any position has grown to more than 12% of portfolio, flag it for trimming.
6. Show me today's economic calendar events that could move the market.
Report back in a concise summary before I approve any action.
```

```
Weekly review (run Sunday evening or Monday pre-market):

1. Show portfolio performance vs SPY over the past 7 days.
2. List all open positions with current P&L and distance from stop-loss.
3. Identify the weakest performer and ask: is the original thesis still intact?
4. Check that all positions have active stop-loss orders.
5. Show current allocation vs target allocation. Flag any drift above 5%.
6. Suggest one thing to do and one thing NOT to do this week.
```

---

## 8. Performance tracking

The agent should maintain a running log (output to a local file: `trade-log.md`) of every trade placed, with:

- Date, ticker, action, size, price
- Stated thesis at time of entry
- Stop-loss level set
- Exit date and price (when closed)
- Outcome vs SPY over the same holding period

Review this log monthly. If suggestions are consistently underperforming SPY, reduce satellite allocation and increase core ETF allocation. The log is the only honest way to know if this is working.

---

## 9. Risks to keep front of mind

Robinhood's disclosure is worth internalizing before every session:

> "AI agents can make errors, misinterpret instructions, act on incomplete or outdated information, and may behave in unexpected ways. You are responsible for reviewing account activity, monitoring positions, and ensuring the agent is operating as intended."

Practically:

- Check the Agentic account in the Robinhood app daily — do not rely solely on the agent's reports.
- If you see an unexpected position or order, investigate immediately.
- If the agent seems to be looping, placing duplicate orders, or behaving strangely, disconnect the MCP and investigate before re-enabling.
- This is real money. The agent is a tool. You are responsible for every trade.

---

## 10. Quick reference — MCP commands for Cursor


| What you want      | Prompt to type                                                                                              |
| ------------------ | ----------------------------------------------------------------------------------------------------------- |
| Portfolio snapshot | "What are my current positions and buying power in my Agentic account?"                                     |
| Buy with stop-loss | "Buy $[amount] of [TICKER] at market price and set a stop-loss at [price]."                                 |
| Research a ticker  | "Look at news, recent price action, and sentiment to build a bull and bear thesis for [TICKER]."            |
| Rebalance          | "Rebalance my Agentic portfolio to [X]% [TICKER A] and [Y]% [TICKER B]. Show me the trades before placing." |
| Find a hedge       | "Given my current portfolio, what hedges would reduce my drawdown risk? Show options and sizing."           |
| Morning briefing   | Paste the full prompt from Section 7                                                                        |
| Performance vs SPY | "Compare my Agentic account return over the last 30 days vs SPY."                                           |
| Set up DCA         | "Buy $[amount] of [TICKER] every [day] at market open until I tell you to stop."                            |
| Risk check         | "Look at my portfolio and tell me what risks I am currently exposed to."                                    |


