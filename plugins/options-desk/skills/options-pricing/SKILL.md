---
name: options-pricing
description: Price options and compute Greeks and implied volatility correctly in code - Black-Scholes-Merton with dividend yield, Black-76 for options on futures and index options priced off the future, Greek units (vega per vol point, theta per day), time to expiry to the minute, put-call parity checks, and an implied-volatility solver that never returns garbage (Brenner-Subrahmanyam start, Newton with a bisection fallback, no-arbitrage bounds). Includes a tested standard-library calculator. Use when writing or reviewing option pricing, Greeks, IV or option-chain analytics code in Python, JS or any language, or when IV comes out NaN, negative, 0 or 500%.
allowed-tools: Bash(python ${CLAUDE_SKILL_DIR}/scripts/options_calc.py *)
---

# Option pricing, Greeks and IV

Most options bugs are not in the formula; they are in the inputs: the wrong
underlying, time in the wrong unit, a stale quote, or a Greek in different
units from the screen it is compared with.

## Tool

```bash
python ${CLAUDE_SKILL_DIR}/scripts/options_calc.py price --spot 100 --strike 100 --vol 20 --rate 5 --days 365 --type call
python ${CLAUDE_SKILL_DIR}/scripts/options_calc.py price --future 24500 --strike 24600 --vol 13 --rate 6.5 --days 7 --type put   # Black-76
python ${CLAUDE_SKILL_DIR}/scripts/options_calc.py iv --spot 182.4 --strike 190 --rate 4.3 --div 0.5 --days 23 --type call --price 1.37
python ${CLAUDE_SKILL_DIR}/scripts/options_calc.py parity --spot 100 --strike 100 --rate 5 --days 90 --call 4.6 --put 3.37
```

Its self-test checks textbook prices, Greeks against finite differences, IV
round trips from deep ITM to 2-day options, and that a price outside the
no-arbitrage bounds is rejected instead of turned into a fake IV.

## Pick the model by the underlying

| Contract | Model |
|---|---|
| European option on a stock or index, priced off **spot** | Black-Scholes-Merton with continuous dividend yield `q` |
| Option on a **future** (commodity options, options priced off the index future) | Black-76: BSM with spot = futures price and `q = r`; delta and gamma are per 1.00 move in the future, and rho holds the future fixed (`-T x price`) |
| Index options (NIFTY, SPX) | either BSM on spot with an implied dividend/carry, or Black-76 on the matching future or synthetic forward. The forward form avoids guessing dividends and rates. |
| American options (US single stocks) | binomial/trinomial tree or finite differences; BSM undervalues calls before dividends and puts deep ITM |

Get the forward from the market: `F = K + e^{rT}(C - P)` from the at-the-money
call and put (put-call parity). Then use Black-76 for the whole strip; this
removes dividend and rate errors from every IV.

## Units (state them in code)

- Volatility and rates as decimals per year inside the maths; print percent.
- **Time to expiry in years from the exact expiry timestamp**, not whole days:
  `(expiry - now).total_seconds() / (365 * 86400)`. Use the market's close
  time on expiry day (NSE 15:30 IST, US equity options 16:00 ET; AM-settled
  index options settle on the opening print). On expiry day, whole-day maths
  makes T zero hours too early or late, and theta and IV explode.
- Calendar-day vs trading-day years (365 vs 252) change theta and IV; pick one
  and label it.
- Greeks per unit of the underlying; multiply by the lot or contract size
  (65 for NIFTY in 2026, 100 for US equity options) for position Greeks.
  Vega per 1 vol point, theta per calendar day, rho per 1 rate point.

## Implied volatility solver

1. Check the price is inside the bounds (and widen the volatility bracket
   for very short-dated quotes instead of capping it): call between
   `max(0, S e^{-qT} - K e^{-rT})` and `S e^{-qT}`. Outside means a stale or
   crossed quote, a wrong rate/dividend, or American early-exercise value.
   Return "no IV", never a clamped number.
2. Start from Brenner-Subrahmanyam: `sigma0 = sqrt(2 pi / T) * price / S`.
3. Newton steps using vega, inside a bracket `[lo, hi]`; when vega is tiny or
   the step leaves the bracket, bisect.
4. Stop on price error, not on sigma change.
5. For production volumes, Jäckel's "Let's Be Rational" gives machine
   precision in two iterations; `py_vollib` implements it.

Feed the solver the **mid** of a two-sided quote, and skip quotes where the
spread is wide relative to the price, either side is zero, or the quote is
older than a few seconds. Deep OTM options with a 0.05 bid and 0.10 ask have
an IV range of tens of points; do not fit a smile through them unweighted.

## Formulas (BSM with dividend yield)

```text
d1 = (ln(S/K) + (r - q + sigma^2/2) T) / (sigma sqrt T),   d2 = d1 - sigma sqrt T
call = S e^{-qT} N(d1) - K e^{-rT} N(d2)
put  = K e^{-rT} N(-d2) - S e^{-qT} N(-d1)
delta_call = e^{-qT} N(d1)            delta_put = -e^{-qT} N(-d1)
gamma = e^{-qT} n(d1) / (S sigma sqrt T)
vega  = S e^{-qT} n(d1) sqrt T        (divide by 100 for per vol point)
```

Use `math.erfc` (or `scipy.special.ndtr`) for `N(x)`; a hand-rolled
polynomial approximation loses accuracy in the tails exactly where deep OTM
options live.

## Review checklist

- [ ] The underlying price matches the option's (future vs spot, same
      timestamp).
- [ ] T in years from a timestamp, with the right settlement time.
- [ ] Dividends or a forward are handled; no IV for American calls before
      ex-dividend from a European formula without a note.
- [ ] IV solver rejects out-of-bounds prices and wide quotes.
- [ ] Greeks are labelled with units and scaled by the multiplier for
      position risk.
- [ ] Results tested against a reference (this tool, QuantLib, or a broker's
      published Greeks) on a few strikes, including expiry day.
