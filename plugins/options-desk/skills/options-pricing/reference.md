# Sources (checked November 2026)

- Black-Scholes-Merton with dividend yield, Black-76 and put-call parity: standard results (Hull, *Options, Futures, and Other Derivatives*; Black 1976).
- NSE India VIX white paper (uses the NIFTY future of each expiry as the forward): https://nsearchives.nseindia.com/web/sites/default/files/inline-files/white_paper_IndiaVIX.pdf
- Jäckel, "Let's Be Rational" (implied volatility to machine precision in two iterations): http://www.jaeckel.org/LetsBeRational.7z (mirror of the paper: https://rust-digger.code-maven.com/src/black76-0.24.2/lib/LetsBeRational.pdf)
- `py_vollib`: https://github.com/vollib/py_vollib
- Cboe SPX/SPXW specifications (AM vs PM settlement): https://www.cboe.com/tradable_products/sp_500/spx_options/specifications/

The Brenner-Subrahmanyam (1988) at-the-money approximation is used only as a
starting point; the solver's result does not depend on it.
