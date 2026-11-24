---
name: india-fno-rules
description: Encode NSE and SEBI index and stock options rules correctly in trading software - NIFTY weekly and Tuesday expiries (BANKNIFTY, FINNIFTY, MIDCPNIFTY monthly only), lot sizes from the instrument master (NIFTY 65, BANKNIFTY 30 in 2026), contract value rules, European cash-settled index options vs physically settled stock options, SEBI's 2024 F&O measures (upfront premium, no calendar-spread benefit on expiry day, extra 2% ELM on expiring shorts, intraday position-limit snapshots), delta-based futures-equivalent limits, STT from 1 April 2026 (0.15% on option sales and exercised options), freeze quantities and the F&O pre-open. Use when building Indian options trading, margin, P&L, tax or risk software, a NIFTY/BANKNIFTY strategy or backtest, or when orders fail for lot, freeze or margin reasons.
---

# NSE and SEBI options rules for code

Facts checked November 2026; sources and open points are in `reference.md`.
NSE revises contract parameters often: **read lot size, tick size, strikes,
expiry and freeze quantity from the exchange or broker files every day**;
hard-code none of them.

## Contracts

| Item | Rule (November 2026) |
|---|---|
| Weekly options | **NIFTY only** on NSE (one weekly benchmark per exchange since 20 Nov 2024). BANKNIFTY, FINNIFTY and MIDCPNIFTY weeklies ended in November 2024. BSE's weekly is SENSEX. |
| Expiry day | NSE: **Tuesday**. NIFTY weekly every Tuesday; all NSE monthly index and stock derivatives on the month's **last Tuesday** (expiries from 1 Sep 2025). Holiday: the previous trading day. BSE: Thursday. |
| Lot sizes | NIFTY **65**, BANKNIFTY **30**, FINNIFTY 60, MIDCPNIFTY 120, NIFTYNXT50 25 (NSE/FAOP/70616). The 30 Dec 2025 expiry was the last on the old lots (NIFTY 75, BANKNIFTY 35); the first on the new lots were the 6 Jan 2026 NIFTY weekly and the 27 Jan 2026 monthly. Lots are reviewed so contract value stays at Rs 15-20 lakh. |
| Exercise style | **European** for index and stock options |
| Settlement | index options: **cash**, at the index closing value on expiry day (T+1). Stock options and futures: **physical delivery** of ITM positions. |
| Tick size | ₹0.05 for NIFTY options; check `tick_size` per instrument |
| Strikes | NIFTY monthly at 50-point intervals; schemes change, take strikes from the instrument master |

Engineering consequences: an expiry calendar is data (`nse_symbols.py` in
claude-tradingview-automation-skills computes Tuesdays with holiday
roll-back); quantity must be a multiple of `lot_size`; a stock option held ITM
into expiry turns into a delivery obligation, so warn or exit before the
broker's physical-settlement cut-off.

## SEBI's F&O measures (circular of 1 Oct 2024) and later changes

| Measure | Effective | What your code must do |
|---|---|---|
| Upfront collection of option premium from buyers | 1 Feb 2025 | buying needs the full premium in the account; no intraday leverage on long options |
| No calendar-spread benefit on expiry day for the expiring leg | 1 Feb 2025 | margin for spreads that include the expiring contract jumps on expiry day; recompute before the day starts |
| Extra 2% ELM on short options expiring that day | 20 Nov 2024 | expiry-day short positions need more margin, also when opened intraday |
| Intraday monitoring of position limits (at least 4 random snapshots) | 1 Apr 2025 | end-of-day checks are not enough |
| Delta-based limits per entity per index (FutEq: call `N(d1)`, put `N(d1) - 1`, future 1): net Rs 5,000 crore intraday (Rs 1,500 crore end of day), gross Rs 10,000 crore per side | 1 Oct 2025 (NSE) | large traders run their own delta monitoring with these definitions |
| Minimum contract value Rs 15 lakh at introduction | new contracts after 20 Nov 2024 | lot sizes change at reviews; never cache them |

Ask the broker's margin API before every order and every expiry morning:
Kite `POST /margins/basket?consider_positions=true` returns `initial` and
`final` (with spread benefit) margins and per-order charges.

## STT and charges (from 1 April 2026)

| Event | STT | Paid by |
|---|---|---|
| Sale of an option | **0.15%** of premium | seller |
| Exercise of an option (ITM at expiry) | **0.15%** of intrinsic value | buyer |
| Sale of a future | 0.05% of price | seller |

Rates from 1 October 2024 to 31 March 2026 were 0.1% (option sale), 0.125%
(exercise) and 0.02% (futures sale). Store the rate by date so P&L and backtests across the
change stay correct. Add exchange transaction charges, SEBI fees, GST on
brokerage and charges, and stamp duty on the buy side; the broker's charges
API (Kite `POST /charges/orders`) returns the breakdown per order. Tax
treatment of F&O income is a matter for a tax adviser.

## Orders

- **Freeze quantity**: orders above the per-instrument freeze limit are
  rejected. NSE revises the limits by circular (for indices, the method
  changed in October 2026). Fetch them on each revision and slice below the
  limit; slices you send count towards SEBI's 10 orders-per-second retail
  algo threshold (see `indian-broker-apis` in
  claude-tradingview-automation-skills).
- **Pre-open**: the F&O call auction (09:00-09:15) covers current-month
  futures (and next month in the last 5 trading days); **options are not in
  the pre-open**. Option orders before 09:15 are queued or rejected by the
  broker.
- MARKET orders need market protection for API orders; on wide option
  spreads use limit orders priced from the best bid/ask.
- Product types: `NRML` to carry positions, `MIS` for intraday (auto
  square-off by the broker before the close).

## Expiry-day checklist for software

1. Margin recomputed with no calendar benefit for the expiring leg and the
   extra 2% ELM on expiring shorts.
2. ITM stock options flagged for physical settlement; exit or arrange funds
   and shares before the broker's cut-off.
3. Short options near the money flagged for pin risk; index options settle on
   the index close, not on the last option trade.
4. Exercised long ITM options charged STT on intrinsic value.
5. Delta and position limits checked intraday, not only at the close.
