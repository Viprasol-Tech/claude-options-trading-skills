#!/usr/bin/env python3
"""Expiry payoff, breakevens and max profit/loss for a multi-leg options position.

Part of claude-options-trading-skills by Viprasol Tech Private Limited.

Each leg is "QTY TYPE STRIKE PRICE": QTY signed (+ long, - short), TYPE C, P or
F (future/stock, STRIKE ignored, PRICE = entry), PRICE = premium per unit paid
or received. --multiplier is the lot or contract size (NIFTY 65, US equity 100).

  python options_strategy.py --multiplier 65 "-1 C 26000 120" "+1 C 26200 55" "-1 P 25500 95" "+1 P 25300 40"
  python options_strategy.py --multiplier 100 "+1 F 0 182.5" "-1 C 190 2.10"        # covered call
  python options_strategy.py --self-test

Payoff at expiry is piecewise linear, so breakevens and extremes are exact,
not read off a grid. Excludes fees, taxes, slippage and early assignment.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class Leg:
    qty: Decimal
    kind: str        # C, P, F
    strike: Decimal
    price: Decimal

    def value(self, s: Decimal) -> Decimal:
        if self.kind == "C":
            intrinsic = max(Decimal(0), s - self.strike)
        elif self.kind == "P":
            intrinsic = max(Decimal(0), self.strike - s)
        else:
            intrinsic = s
        return self.qty * (intrinsic - self.price)


def parse_leg(text: str) -> Leg:
    parts = text.split()
    if len(parts) != 4:
        raise ValueError(f"leg {text!r}: expected 'QTY TYPE STRIKE PRICE'")
    qty, kind, strike, price = parts
    kind = kind.upper()
    if kind not in {"C", "P", "F"}:
        raise ValueError(f"leg {text!r}: TYPE must be C, P or F")
    try:
        leg = Leg(Decimal(qty), kind, Decimal(strike), Decimal(price))
    except ArithmeticError:
        raise ValueError(f"leg {text!r}: QTY, STRIKE and PRICE must be numbers") from None
    if not all(x.is_finite() for x in (leg.qty, leg.strike, leg.price)):
        raise ValueError(f"leg {text!r}: numbers must be finite")
    if leg.qty == 0 or leg.price < 0 or (kind != "F" and leg.strike <= 0):
        raise ValueError(f"leg {text!r}: qty must be non-zero, price >= 0, strike > 0")
    return leg


def pnl(legs: list[Leg], s: Decimal, mult: Decimal) -> Decimal:
    return sum((leg.value(s) for leg in legs), Decimal(0)) * mult


def analyse(legs: list[Leg], mult: Decimal) -> dict:
    kinks = sorted({leg.strike for leg in legs if leg.kind != "F"})
    points = [Decimal(0)] + [k for k in kinks if k > 0]
    top = (points[-1] if len(points) > 1 else max((leg.price for leg in legs), default=Decimal(1))) * 2 + 1
    points.append(top)
    values = [pnl(legs, p, mult) for p in points]
    slope_right = (pnl(legs, top + 1, mult) - values[-1])           # P&L change per 1.00 above the last kink
    breakevens: list[Decimal] = []
    flat: list[list] = []                       # [start, end or None] ranges where P&L is exactly 0
    segs = list(zip(points, values, points[1:], values[1:]))
    segs.append((points[-1], values[-1], None, None))   # the tail above the last point
    for x0, y0, x1, y1 in segs:
        tail = x1 is None
        if y0 == 0 and ((tail and slope_right == 0) or (not tail and y1 == 0)):
            if flat and flat[-1][1] == x0:
                flat[-1][1] = None if tail else x1
            else:
                flat.append([x0, None if tail else x1])
            continue
        if not tail and ((y0 < 0 < y1) or (y1 < 0 < y0)):
            breakevens.append(x0 + (x1 - x0) * (-y0) / (y1 - y0))
        if tail and slope_right and (y0 < 0 < slope_right or slope_right < 0 < y0):
            breakevens.append(x0 + (-y0) / slope_right)
    # isolated zeros (P&L touches or crosses 0 exactly at a strike), not inside a flat range
    for x, y in zip(points, values):
        if y == 0 and not any(a <= x and (b is None or x <= b) for a, b in flat):
            breakevens.append(x)
    net = -sum((leg.qty * leg.price for leg in legs if leg.kind != "F"), Decimal(0)) * mult
    max_profit = "unlimited" if slope_right > 0 else max(values)
    max_loss = "unlimited" if slope_right < 0 else min(values)
    return {"net_premium": net, "max_profit": max_profit, "max_loss": max_loss,
            "breakevens": sorted(set(b.quantize(Decimal("0.01")) for b in breakevens)),
            "zero_ranges": [(a, b) for a, b in flat], "table": list(zip(points[:-1], values[:-1]))}


def _self_test() -> None:
    D = Decimal
    # Long call: unlimited profit, max loss = premium, breakeven = K + premium
    r = analyse([parse_leg("+1 C 100 5")], D(100))
    assert r["max_profit"] == "unlimited" and r["max_loss"] == D(-500) and r["breakevens"] == [D(105)], r
    # Short put: max profit premium, max loss at S=0, breakeven K - premium
    r = analyse([parse_leg("-1 P 100 4")], D(100))
    assert r["max_profit"] == D(400) and r["max_loss"] == D(-9600) and r["breakevens"] == [D(96)], r
    # Iron condor (NIFTY lot 65)
    legs = [parse_leg(x) for x in ("-1 C 26000 120", "+1 C 26200 55", "-1 P 25500 95", "+1 P 25300 40")]
    r = analyse(legs, D(65))
    credit = (120 - 55 + 95 - 40) * 65
    assert r["net_premium"] == D(credit) and r["max_profit"] == D(credit), r
    assert r["max_loss"] == D((200 - 120) * -65), r
    assert r["breakevens"] == [D(25380), D(26120)], r
    # Covered call: unlimited loss? no - capped upside, loss to zero
    r = analyse([parse_leg("+1 F 0 182.5"), parse_leg("-1 C 190 2.10")], D(100))
    assert r["max_profit"] == D("960.00") and r["max_loss"] == D("-18040.00") and r["breakevens"] == [D("180.4")], r
    # Short straddle: unlimited loss both... right side unlimited
    r = analyse([parse_leg("-1 C 100 6"), parse_leg("-1 P 100 5")], D(1))
    assert r["max_loss"] == "unlimited" and r["breakevens"] == [D(89), D(111)], r
    # Short future: unlimited loss
    r = analyse([parse_leg("-1 F 0 50")], D(1))
    assert r["max_loss"] == "unlimited" and r["max_profit"] == D(50) and r["breakevens"] == [D(50)], r
    # Flat zero P&L is a range, not two breakevens
    r = analyse([parse_leg("+1 C 100 0"), parse_leg("-1 C 110 0")], D(1))
    assert r["breakevens"] == [] and r["zero_ranges"] == [(D(0), D(100))], r
    r = analyse([parse_leg("+1 F 0 100"), parse_leg("-1 F 0 100")], D(1))
    assert r["breakevens"] == [] and r["zero_ranges"] == [(D(0), None)], r
    r = analyse([parse_leg("+1 C 100 5"), parse_leg("-1 C 100 5")], D(1))
    assert r["breakevens"] == [] and r["zero_ranges"] == [(D(0), None)], r
    # Breakeven exactly at a strike: long put 100 @ 0 + short put 90 @ 10 ... P&L 0 at 100? check a crossing at a kink
    r = analyse([parse_leg("+1 C 100 10"), parse_leg("+1 P 100 0")], D(1))   # straddle with all premium on call
    assert r["breakevens"] == [D(90), D(110)], r
    for bad in ("1 X 100 5", "0 C 100 5", "+1 C 100", "+1 C inf 5", "nan C 100 5", "+1 C 100 abc"):
        try:
            parse_leg(bad)
        except ValueError:
            continue
        raise AssertionError(bad)
    print("options_strategy self-test passed")


def _multiplier(text: str) -> Decimal:
    try:
        v = Decimal(text)
    except ArithmeticError:
        v = Decimal("NaN")
    if not v.is_finite() or v <= 0:
        raise argparse.ArgumentTypeError("multiplier must be a positive number")
    return v


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Expiry payoff of a multi-leg options position")
    ap.add_argument("legs", nargs="*", help='"QTY TYPE STRIKE PRICE", e.g. "-1 C 26000 120"')
    ap.add_argument("--multiplier", type=_multiplier, default=Decimal(1), help="Lot / contract size (> 0)")
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args(argv)
    if a.self_test:
        _self_test()
        return 0
    if not a.legs:
        ap.print_help()
        return 2
    try:
        legs = [parse_leg(x) for x in a.legs]
        r = analyse(legs, a.multiplier)
    except (ValueError, ArithmeticError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    net = r["net_premium"]
    print(f"net premium   " + ("even" if net == 0 else f"{abs(net)} {'credit' if net > 0 else 'debit'}"))
    print(f"max profit    {r['max_profit']}")
    print(f"max loss      {r['max_loss']}")
    print("breakevens    " + (", ".join(str(b) for b in r["breakevens"]) or "none"))
    for lo, hi in r["zero_ranges"]:
        print(f"zero P&L      from {lo} " + (f"to {hi}" if hi is not None else "upwards"))
    print("P&L at expiry by underlying price:")
    for x, y in r["table"]:
        print(f"  {x:>12}  {y:>14}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
