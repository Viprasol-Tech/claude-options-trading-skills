---
name: options-strategies
description: Model multi-leg options positions exactly - verticals, iron condors, butterflies, straddles, strangles, calendars, covered calls and ratio spreads - with expiry payoff, breakevens, max profit and max loss computed from the piecewise-linear payoff (never read off a coarse grid), position Greeks, and the risks a payoff chart hides: early assignment, pin risk, expiry-day gamma, margin vs. defined risk, and legging. Includes a tested payoff tool with lot/contract multipliers. Use when building a strategy builder, risk graph, option scanner or position-risk report, or when checking whether a spread really is "defined risk".
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/options_strategy.py *)
---

# Multi-leg options strategies

Engineering guidance, not trade recommendations. The payoff at expiry is a
straight-line function between strikes, so every number below can be exact.

## Tool

```bash
python ${CLAUDE_SKILL_DIR}/scripts/options_strategy.py --multiplier 65 "-1 C 26000 120" "+1 C 26200 55" "-1 P 25500 95" "+1 P 25300 40"   # iron condor, NIFTY lot
python ${CLAUDE_SKILL_DIR}/scripts/options_strategy.py --multiplier 100 "+1 F 0 182.5" "-1 C 190 2.10"                                     # covered call
python ${CLAUDE_SKILL_DIR}/scripts/options_strategy.py --multiplier 100 "-1 C 100 6" "-1 P 100 5"                                           # short straddle
```

Legs are `QTY TYPE STRIKE PRICE` (`+` long, `-` short; `F` = stock or future
at PRICE). Output: net credit/debit, max profit, max loss (or "unlimited"),
exact breakevens and P&L at every strike.

## How to compute it in your own code

- Evaluate P&L at 0, at every strike, and the slope above the highest strike.
  Max/min over those points are the exact extremes; a positive slope means
  unlimited profit, negative means unlimited loss. Breakevens are the zero
  crossings between consecutive points (linear interpolation is exact).
- Never find breakevens on a 1-point or 50-point price grid: you will miss or
  shift them.
- Use Decimal or integer paise/cents for premiums and P&L; multiply by the
  lot size or contract multiplier once, at the end.
- Before expiry, value each leg with a pricing model (`options-pricing`) at
  the chosen date and IV to draw the "T+n" curve; it differs from the expiry
  curve most near the short strikes.

## Position Greeks

Sum `qty x multiplier x greek` per leg. A delta-neutral iron condor still has
large negative gamma near expiry: a small move costs much more on expiry day
than a week out. Show gamma and theta per day next to the payoff, not only
delta.

## What the payoff chart does not show

| Risk | What happens | What code should do |
|---|---|---|
| Early assignment (American options, e.g. US single stocks) | short ITM calls get assigned before ex-dividend when the remaining extrinsic value is below the dividend; deep ITM short puts can be assigned any day | flag short ITM legs with extrinsic < dividend before ex-date; show the post-assignment stock position |
| Pin risk | underlying closes near a short strike; you do not know if you will be assigned | close or roll short legs near the strike before expiry; never leave a spread half-exercised |
| Physical settlement (Indian stock options) | ITM stock options settle by delivery; the margin for delivery rises in the last days before expiry | warn on open ITM stock option positions as expiry approaches; index options are cash-settled |
| Exercise by exception | brokers/clearing houses auto-exercise options ITM at expiry above a threshold | model auto-exercise for long ITM legs and the resulting stock/future position |
| Legging | entering a spread one leg at a time leaves a naked leg if the second fails | send the combo as one order where the broker supports it (`options-orders`); otherwise buy the long leg first, then sell |
| Margin vs. max loss | exchanges' SPAN plus exposure margin can exceed the spread's max loss, and the hedge benefit can be lost on expiry day | get margin from the broker's basket-margin API before placing, not from the payoff |
| Liquidity | wide spreads make the theoretical P&L unreachable | price entries and exits at bid/ask, not mid |

## Strategy reference (per unit, before multiplier)

| Strategy | Max profit | Max loss | Breakevens |
|---|---|---|---|
| Long call | unlimited | premium | K + premium |
| Short put | premium | K - premium | K - premium |
| Bull call spread (K1 < K2) | K2 - K1 - debit | debit | K1 + debit |
| Bear put spread (K1 < K2) | K2 - K1 - debit | debit | K2 - debit |
| Iron condor (credit C) | C | wider wing width - C | short put - C, short call + C |
| Long straddle | unlimited | debit | K ± debit |
| Short strangle | credit | unlimited (call side), large (put side) | put K - credit, call K + credit |
| Covered call | K - S0 + premium | S0 - premium (to zero) | S0 - premium |

The tool's self-test checks the long call, short put, iron condor, covered
call, short straddle and short future against these formulas.
