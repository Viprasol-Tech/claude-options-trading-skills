---
name: options-orders
description: Place and manage options orders safely through broker APIs - single-leg and multi-leg (spread/combo) orders on Interactive Brokers (OPT and BAG contracts, tradingClass), Alpaca (options levels, mleg orders, position_intent), Tradier (multileg debit/credit, OCC symbols, 200-but-rejected responses) and Zerodha Kite (no native multi-leg: hedge-first legging, basket margin), open/close intents, limit pricing from bid/ask, partial fills and legging risk, exercise-by-exception, assignment handling, and the US pattern day trader rule change (FINRA 4210, June 2026). Use when writing or reviewing options execution code, a spread order router, or a bot that sells options, or when an order is rejected for level, margin, intent or leg-ratio reasons.
---

# Options orders through broker APIs

Execution code for options fails in ways equity code does not: four legs
that must fill together, a "sell" that opens instead of closes, an assignment
that turns a spread into a stock position overnight. Facts checked November
2026; sources in `reference.md`.

## Rules for every broker

1. **Send spreads as one multi-leg order** when the broker supports it, with
   a net limit price (debit or credit). Never send legs as separate market
   orders.
2. **Price from the book**: start at the mid of the combo's natural bid/ask
   and walk towards the natural price in small steps with a timeout; never a
   market order on an options spread.
3. **Say whether each leg opens or closes** (`buy_to_open`, `sell_to_close`,
   `position_intent`) where the API asks; a wrong intent opens a naked short
   or is rejected.
4. **Idempotency**: set a client order ID; on timeout, query by it before any
   resend (same as `signal-to-order` in claude-tradingview-automation-skills).
5. **Re-read positions after every fill and every morning**: assignment and
   exercise change positions without an order from you.
6. **Pre-trade margin check** through the broker's margin/what-if API, not
   from the payoff (`options-strategies`).

## Interactive Brokers (TWS API / IB Gateway)

- Single option: `Contract(secType="OPT", symbol, exchange="SMART",
  currency, lastTradeDateOrContractMonth="YYYYMMDD", strike, right="C"|"P",
  multiplier="100")`, plus `tradingClass` (or `localSymbol` / `conId`) when
  several classes exist (index weeklies vs monthlies, adjusted contracts).
  Resolve with `reqContractDetails` and keep the `conId`.
- Spread: `secType="BAG"` with `comboLegs` (each `conId`, `ratio`, `action`,
  `exchange`); one limit price for the whole combo. The sign convention for
  combo debits and credits is easy to invert: test it on a paper account.
- Check margin first with a what-if order (`order.whatIf = True`).

## Alpaca

- Options trading levels: 1 covered calls and cash-secured puts; 2 adds
  buying calls and puts; 3 adds spreads. An order beyond the account's level
  is rejected.
- Orders: market, limit, stop, stop_limit (stops single-leg only); time in
  force `day` or `gtc`; whole-number quantities; no extended hours.
- Multi-leg: `order_class="mleg"` with `legs[]` (symbol, side, `ratio_qty`,
  `position_intent`); leg ratios must have a greatest common divisor of 1,
  and every leg must be covered within the order.
- Contracts ITM by $0.01 or more are auto-exercised at expiry; poll
  non-trade activities to see assignments.

## Tradier

- `class=option` with the OCC `option_symbol` and side `buy_to_open`,
  `sell_to_open`, `buy_to_close` or `sell_to_close`.
- `class=multileg` (up to 4 legs) with type `market`, `debit`, `credit` or
  `even`; `class=combo` for stock plus one or two options.
- An HTTP 200 can still be a rejected order: always re-query the order
  status.

## Zerodha Kite and other Indian brokers

- No native multi-leg order. Place the **long (hedge) leg first**, wait for
  its fill, then the short leg: the hedge lowers the margin for the short and
  never leaves you naked short. Exit in reverse: short leg first.
- Check `POST /margins/basket?consider_positions=true` for the whole spread
  before the first leg; `final` includes the spread benefit.
- If the second leg does not fill within your timeout, decide in code:
  re-price, or close the first leg. Never leave a half-built spread silently.
- Quantities in multiples of `lot_size`; slice above the freeze quantity;
  limit orders or market protection only; respect the 10 orders-per-second
  retail algo threshold (`india-fno-rules`).

## Exercise and assignment (US)

- **Exercise by exception**: at expiry, OCC auto-exercises equity and index
  options ITM by $0.01 or more unless the holder instructs otherwise; brokers
  may set their own thresholds. The exercise
  cut-off for customers is 5:30 pm ET on expiry day (firms set earlier
  deadlines).
- Short American options can be assigned any day; short ITM calls are most
  at risk before an ex-dividend date when their time value is below the
  dividend. Code should flag those legs the day before the ex-date.
- After assignment, an option becomes stock: an assigned short put becomes
  long shares, an assigned short call becomes short shares (or delivers the
  shares of a covered call). A spread with one leg assigned is no longer
  defined risk overnight. Detect it from positions, not from your order log.

## US pattern day trader rule (2026)

The SEC approved FINRA's replacement of the pattern day trader designation
and its $25,000 minimum with intraday margin standards in Rule 4210 (approved
14 April 2026, effective 4 June 2026, with firms allowed to phase in until
20 October 2027). During the phase-in, brokers may still enforce the old
rule: read the account's day-trade count and buying power from the broker
API instead of assuming either regime.

## Review checklist

- [ ] Spreads sent as one multi-leg order, or hedge-first legging with a
      timeout and an explicit unwind.
- [ ] Limit prices from the live bid/ask; no market orders on spreads.
- [ ] Open/close intent per leg; leg ratios reduced.
- [ ] Client order IDs and query-before-resend.
- [ ] Margin checked before sending; positions reconciled after fills and
      each morning (assignment).
- [ ] Expiry and ex-dividend checks for short ITM legs.
