---
name: options-backtesting
description: Backtest options strategies without fooling yourself - point-in-time option chains (not today's strikes), fills at bid/ask with slippage instead of mid or last, expired and delisted contracts, lot-size and expiry-calendar changes, exercise, assignment and settlement at expiry, margin and capital usage, fees and taxes, and the classic biases (lookahead in IV or close prices, survivorship, theoretical prices from a model used as fills). Use when building or reviewing an options backtest, a short-premium or 0DTE strategy test, a wheel/covered-call simulator, or when a backtest's Sharpe looks too good.
---

# Options backtesting

An options backtest has every equity-backtest bias plus several of its own.
The common failure: a short-premium strategy that looks smooth in a backtest
filled at mid, with no early assignment and no expiry-day margin, then loses
in its first fast market.

## Data you need (point in time)

- **The chain as it existed**: strikes listed that day, with bid, ask, last,
  volume, open interest and a timestamp. New strikes are added as the
  underlying moves; a backtest that picks from today's strike list trades
  contracts that did not exist.
- **Expired contracts**, including the final settlement price. Free sources
  usually drop them; without them every expiry is guessed.
- **The underlying at the same timestamp** as the option quote (and the
  future for index options priced off futures).
- **Contract terms by date**: lot size or multiplier, tick size, expiry
  weekday and calendar. NSE changed the expiry weekday in September 2025 and
  index lot sizes from January 2026 expiries; a NIFTY backtest across those dates must use the terms of each date.
- **Corporate actions** for stock options: splits and special dividends
  adjust strikes and multipliers.
- Rates and dividends, or forwards implied from put-call parity, if the test
  computes IV or Greeks.

## Fills

| Shortcut | Problem | Do instead |
|---|---|---|
| Fill at last traded price | last can be minutes or days old | use the quote at the decision time |
| Fill at mid | you rarely get mid on 4-leg spreads, never on illiquid strikes | buy at ask, sell at bid, or mid + a fraction of the spread calibrated on your real fills |
| Model price as fill | you test the model against itself | fills come from quotes only; use models for signals and risk |
| Ignore size | large orders walk the book and hit freeze limits | cap size by displayed size or a fraction of volume; slice above freeze quantity |
| Same-bar decision and fill | lookahead | decide on bar t, fill on bar t+1 quote |

Add brokerage, exchange charges, taxes (in India, STT on option sales and on
exercised ITM options, plus GST and stamp duty) per leg. They matter most for
strategies that trade cheap options often.

## Expiry, exercise and assignment

- Cash-settled index options: settle at the official settlement price, not at
  the last traded option price.
- Physically settled stock options (India) and US equity options: model
  exercise into shares and the margin or capital that requires.
- American options: model early assignment of short ITM options at least
  before ex-dividend dates, and when extrinsic value falls below a threshold.
- Expiry-day behaviour (0DTE, NSE expiry Tuesdays): use intraday data; daily
  bars cannot show a short strike breached at 11:00 and recovered by 15:30.

## Capital and risk

- Deduct margin, not just premium, from available capital; margin rises near
  expiry and in volatile markets, and can force exits in a real account.
- Report the worst day, worst week and largest single-trade loss next to the
  Sharpe; short-option P&L is skewed and Sharpe hides tails.
- Count the parameter sets tried and deflate the Sharpe (see
  `backtest-auditor` in claude-trading-skills).

## Review checklist

- [ ] Chains are point in time, including expired contracts.
- [ ] Fills use bid/ask (or calibrated slippage), next-bar, size-capped.
- [ ] Contract terms (lot size, expiry weekday, multiplier) vary by date.
- [ ] Settlement, exercise and early assignment are modelled.
- [ ] Fees and taxes per leg; margin deducted from capital.
- [ ] Intraday data for expiry-day and 0DTE strategies.
- [ ] Out-of-sample period untouched until the end; trials counted.
