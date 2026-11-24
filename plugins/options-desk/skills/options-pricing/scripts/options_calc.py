#!/usr/bin/env python3
"""Option prices, Greeks and implied volatility (Black-Scholes-Merton and Black-76).

Part of claude-options-trading-skills by Viprasol Tech Private Limited.

European options only. American options with dividends need a tree or
finite-difference model; this tool says so instead of returning a wrong number.

  python options_calc.py price --spot 100 --strike 100 --vol 20 --rate 5 --days 365 --type call
  python options_calc.py price --future 24500 --strike 24600 --vol 13 --rate 6.5 --days 7 --type put   # Black-76
  python options_calc.py iv --spot 100 --strike 105 --rate 5 --days 30 --type call --price 1.25
  python options_calc.py parity --spot 100 --strike 100 --rate 5 --days 90 --call 4.6 --put 3.37
  python options_calc.py --self-test

Units: vol and rates in percent per year (continuous compounding), --days in
calendar days (or --years). Greeks: delta per 1.00 move in the underlying,
gamma per 1.00 move, vega per 1 vol point, theta per calendar day, rho per
1 rate point.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass

SQRT2PI = math.sqrt(2 * math.pi)


def ncdf(x: float) -> float:
    return 0.5 * math.erfc(-x / math.sqrt(2))


def npdf(x: float) -> float:
    return math.exp(-0.5 * x * x) / SQRT2PI


@dataclass(frozen=True)
class Result:
    price: float
    delta: float
    gamma: float
    vega: float   # per 1 vol point
    theta: float  # per calendar day
    rho: float    # per 1 rate point


def bsm(s: float, k: float, t: float, r: float, sigma: float, q: float = 0.0, call: bool = True) -> Result:
    """Black-Scholes-Merton on spot with continuous dividend yield q. Rates/vol as decimals, t in years."""
    if not all(math.isfinite(x) for x in (s, k, t, r, sigma, q)):
        raise ValueError("inputs must be finite numbers")
    if s <= 0 or k <= 0:
        raise ValueError("spot and strike must be positive")
    if t < 0 or sigma < 0:
        raise ValueError("time to expiry and volatility cannot be negative")
    if t == 0 or sigma == 0:
        # Deterministic limit: the option is worth its discounted forward intrinsic value.
        fwd_s, pv_k = s * math.exp(-q * t), k * math.exp(-r * t)
        itm = fwd_s > pv_k if call else pv_k > fwd_s
        price = max(0.0, (fwd_s - pv_k) if call else (pv_k - fwd_s))
        delta = (math.exp(-q * t) if call else -math.exp(-q * t)) if itm else 0.0
        return Result(price, delta, 0.0, 0.0, 0.0, 0.0)
    st = sigma * math.sqrt(t)
    d1 = (math.log(s / k) + (r - q + 0.5 * sigma * sigma) * t) / st
    d2 = d1 - st
    dq, dr = math.exp(-q * t), math.exp(-r * t)
    if call:
        price = s * dq * ncdf(d1) - k * dr * ncdf(d2)
        delta = dq * ncdf(d1)
        theta = (-s * dq * npdf(d1) * sigma / (2 * math.sqrt(t)) - r * k * dr * ncdf(d2) + q * s * dq * ncdf(d1))
        rho = k * t * dr * ncdf(d2)
    else:
        price = k * dr * ncdf(-d2) - s * dq * ncdf(-d1)
        delta = -dq * ncdf(-d1)
        theta = (-s * dq * npdf(d1) * sigma / (2 * math.sqrt(t)) + r * k * dr * ncdf(-d2) - q * s * dq * ncdf(-d1))
        rho = -k * t * dr * ncdf(-d2)
    gamma = dq * npdf(d1) / (s * st)
    vega = s * dq * npdf(d1) * math.sqrt(t)
    return Result(price, delta, gamma, vega / 100, theta / 365, rho / 100)


def black76(f: float, k: float, t: float, r: float, sigma: float, call: bool = True) -> Result:
    """Black-76 on a futures/forward price: BSM with q = r and spot = F.

    Rho is recomputed holding F fixed (only discounting moves): -T * V.
    Delta and gamma are per 1.00 move in the futures price.
    """
    res = bsm(f, k, t, r, sigma, q=r, call=call)
    return Result(res.price, res.delta, res.gamma, res.vega, res.theta, -t * res.price / 100)


def bounds(s: float, k: float, t: float, r: float, q: float, call: bool) -> tuple[float, float]:
    """No-arbitrage bounds for a European option price."""
    fs, pk = s * math.exp(-q * t), k * math.exp(-r * t)
    return (max(0.0, fs - pk), fs) if call else (max(0.0, pk - fs), pk)


def implied_vol(price: float, s: float, k: float, t: float, r: float, q: float = 0.0, call: bool = True,
                tol: float = 1e-8) -> float:
    """Newton from the Brenner-Subrahmanyam guess, falling back to bisection. Raises if price is outside bounds."""
    lo_b, hi_b = bounds(s, k, t, r, q, call)
    if t <= 0:
        raise ValueError("no implied volatility at or after expiry")
    if not (lo_b < price < hi_b):
        raise ValueError(f"price {price:g} outside no-arbitrage bounds ({lo_b:.6g}, {hi_b:.6g}): "
                         "stale quote, wrong rate/dividend, or American early-exercise premium")
    lo, hi = 1e-9, 10.0
    while bsm(s, k, t, r, hi, q, call).price < price:   # widen the bracket for very high vols
        hi *= 4
        if hi > 1e4:
            raise ValueError("implied volatility above 1,000,000%: the quote is not usable")
    sigma = max(lo * 10, min(hi / 2, math.sqrt(2 * math.pi / t) * price / s))
    for _ in range(200):
        res = bsm(s, k, t, r, sigma, q, call)
        diff = res.price - price
        if diff > 0:
            hi = min(hi, sigma)
        else:
            lo = max(lo, sigma)
        vega = res.vega * 100
        step = diff / vega if vega > 1e-300 else float("inf")
        if abs(diff) < tol and abs(step) < 1e-9:       # price matched AND vol pinned down
            return sigma
        nxt = sigma - step
        sigma = nxt if lo < nxt < hi else 0.5 * (lo + hi)   # bisection when Newton leaves the bracket
        if hi - lo < 1e-12 * max(1.0, sigma):
            break
    if abs(bsm(s, k, t, r, sigma, q, call).price - price) > max(tol, 1e-9 * price) * 1e3:
        raise ValueError("implied volatility did not converge to the quoted price")
    return sigma


def parity_gap(call: float, put: float, s: float, k: float, t: float, r: float, q: float = 0.0) -> float:
    """C - P - (S e^-qT - K e^-rT); near zero for European options with correct inputs."""
    return call - put - (s * math.exp(-q * t) - k * math.exp(-r * t))


def _self_test() -> None:
    def close(a: float, b: float, tol: float = 1e-4) -> bool:
        return abs(a - b) <= tol
    c = bsm(100, 100, 1, 0.05, 0.2, call=True)
    p = bsm(100, 100, 1, 0.05, 0.2, call=False)
    assert close(c.price, 10.4506, 1e-4) and close(p.price, 5.5735, 1e-4), (c, p)  # textbook values
    h = bsm(42, 40, 0.5, 0.10, 0.20)                                                  # Hull, Example 15.6
    assert close(h.price, 4.76, 5e-3) and close(bsm(42, 40, 0.5, 0.10, 0.20, call=False).price, 0.81, 5e-3)
    assert close(parity_gap(c.price, p.price, 100, 100, 1, 0.05), 0.0, 1e-10)
    assert close(c.delta - p.delta, 1.0, 1e-12)                                        # q = 0
    # Greeks vs finite differences
    e = 1e-4
    assert close(c.delta, (bsm(100 + e, 100, 1, .05, .2).price - bsm(100 - e, 100, 1, .05, .2).price) / (2 * e), 1e-6)
    assert close(c.vega, (bsm(100, 100, 1, .05, .2 + e).price - bsm(100, 100, 1, .05, .2 - e).price) / (2 * e) / 100, 1e-6)
    assert close(c.theta, -(bsm(100, 100, 1 + e, .05, .2).price - bsm(100, 100, 1 - e, .05, .2).price) / (2 * e) / 365, 1e-6)
    assert close(c.gamma, (bsm(100 + e, 100, 1, .05, .2).delta - bsm(100 - e, 100, 1, .05, .2).delta) / (2 * e), 1e-5)
    # Black-76 equals BSM on the forward
    f = 100 * math.exp(0.05)
    assert close(black76(f, 100, 1, 0.05, 0.2).price, c.price, 1e-9)
    # IV round trips, deep ITM/OTM, short dated
    for k, t, v, cp in [(100, 1, .2, True), (130, .1, .45, True), (70, .02, .8, False), (100, 2 / 365, .12, False)]:
        px = bsm(100, k, t, .05, v, .01, cp).price
        assert close(implied_vol(px, 100, k, t, .05, .01, cp), v, 1e-6), (k, t, v)
    try:
        implied_vol(0.001, 100, 50, 1, .05)     # below intrinsic
    except ValueError:
        pass
    else:
        raise AssertionError("IV below intrinsic accepted")
    assert bsm(100, 90, 0, .05, .2).price == 10
    # sigma = 0: discounted forward intrinsic, not spot intrinsic
    assert close(bsm(100, 90, 1, .05, 0).price, 100 - 90 * math.exp(-.05), 1e-12)
    for bad in ((100, 90, -0.1, .05, .2), (float("nan"), 90, 1, .05, .2)):
        try:
            bsm(*bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    # Black-76 Greeks by finite differences holding F fixed (rho = -T V)
    b = black76(100, 100, 1, .05, .2)
    assert close(b.rho, (black76(100, 100, 1, .05 + e, .2).price - black76(100, 100, 1, .05 - e, .2).price) / (2 * e) / 100, 1e-6)
    assert close(b.rho, -b.price / 100, 1e-12)
    assert close(b.delta, (black76(100 + e, 100, 1, .05, .2).price - black76(100 - e, 100, 1, .05, .2).price) / (2 * e), 1e-6)
    assert close(b.vega, (black76(100, 100, 1, .05, .2 + e).price - black76(100, 100, 1, .05, .2 - e).price) / (2 * e) / 100, 1e-6)
    # Very high and badly conditioned IVs: solved or rejected, never clamped
    px = bsm(24500, 24500, 0.0000095, 0.065, 25.0, 0.065).price
    assert close(implied_vol(px, 24500, 24500, 0.0000095, 0.065, 0.065), 25.0, 1e-6)
    for k, t in ((99.9, 1e-6), (101, 1 / (365 * 24))):
        px = bsm(100, k, t, .05, .2).price
        assert close(implied_vol(px, 100, k, t, .05), .2, 1e-4), (k, t, implied_vol(px, 100, k, t, .05))
    print("options_calc self-test passed")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="European option prices, Greeks, IV and parity")
    ap.add_argument("--self-test", action="store_true")
    sub = ap.add_subparsers(dest="cmd")

    def common(p: argparse.ArgumentParser) -> None:
        g = p.add_mutually_exclusive_group()
        g.add_argument("--spot", type=float)
        g.add_argument("--future", type=float, help="Use Black-76 on this futures price")
        p.add_argument("--strike", type=float, required=True)
        p.add_argument("--rate", type=float, default=0.0, help="Risk-free rate, %% per year")
        p.add_argument("--div", type=float, default=0.0, help="Dividend yield, %% per year (spot only)")
        tg = p.add_mutually_exclusive_group(required=True)
        tg.add_argument("--days", type=float, help="Calendar days to expiry")
        tg.add_argument("--years", type=float)

    p1 = sub.add_parser("price")
    common(p1)
    p1.add_argument("--vol", type=float, required=True, help="Volatility, %% per year")
    p1.add_argument("--type", choices=["call", "put"], required=True)
    p2 = sub.add_parser("iv")
    common(p2)
    p2.add_argument("--price", type=float, required=True)
    p2.add_argument("--type", choices=["call", "put"], required=True)
    p3 = sub.add_parser("parity")
    common(p3)
    p3.add_argument("--call", type=float, required=True)
    p3.add_argument("--put", type=float, required=True)
    a = ap.parse_args(argv)
    if a.self_test:
        _self_test()
        return 0
    if a.cmd is None:
        ap.print_help()
        return 2
    if a.spot is None and a.future is None:
        print("error: give --spot or --future", file=sys.stderr)
        return 2
    nums = [v for v in (a.spot, a.future, a.strike, a.rate, a.div, a.days, a.years,
                        getattr(a, "vol", None), getattr(a, "price", None),
                        getattr(a, "call", None), getattr(a, "put", None)) if v is not None]
    if not all(math.isfinite(v) for v in nums):
        print("error: inputs must be finite numbers", file=sys.stderr)
        return 2
    if abs(a.rate) > 100 or abs(a.div) > 100:
        print("error: --rate and --div are percent per year; values beyond +/-100 are almost certainly a unit mistake", file=sys.stderr)
        return 2
    t = a.years if a.years is not None else a.days / 365
    r = a.rate / 100
    q = r if a.future is not None else a.div / 100
    s = a.future if a.future is not None else a.spot
    model = "Black-76 (futures)" if a.future is not None else "Black-Scholes-Merton"
    try:
        if a.cmd == "price":
            res = (black76(s, a.strike, t, r, a.vol / 100, a.type == "call") if a.future is not None
                   else bsm(s, a.strike, t, r, a.vol / 100, q, a.type == "call"))
            print(f"model    {model}, European")
            for k in ("price", "delta", "gamma", "vega", "theta", "rho"):
                print(f"{k:8} {getattr(res, k):.6f}")
        elif a.cmd == "iv":
            iv = implied_vol(a.price, s, a.strike, t, r, q, a.type == "call")
            print(f"model    {model}, European\niv       {iv * 100:.4f}%")
        else:
            gap = parity_gap(a.call, a.put, s, a.strike, t, r, q)
            print(f"C - P - (S e^-qT - K e^-rT) = {gap:+.6f}")
            print("consistent" if abs(gap) < 0.01 * s / 100 + 0.01 else
                  "parity gap: stale/wide quotes, wrong rate or dividend, or American options")
    except (ValueError, OverflowError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
