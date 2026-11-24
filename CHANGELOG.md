# Changelog

All notable changes are listed here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-11-24

### Added
- `options-desk` Claude Code plugin with 6 skills: `options-pricing`,
  `options-strategies`, `options-data`, `options-orders`, `india-fno-rules`,
  `options-backtesting`.
- `options_calc.py`: Black-Scholes-Merton (dividend yield) and Black-76
  prices, Greeks with explicit units, implied volatility with no-arbitrage
  bound checks, and put-call parity.
- `options_strategy.py`: exact expiry payoff, breakevens and max profit/loss
  for multi-leg positions with lot or contract multipliers.
- Facts checked against SEBI, NSE, OCC, Cboe, FINRA, IBKR, Alpaca, Tradier
  and Zerodha documentation in November 2026.
