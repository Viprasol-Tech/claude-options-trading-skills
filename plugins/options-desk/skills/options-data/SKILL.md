---
name: options-data
description: Handle option chain data correctly in code - contract identifiers (OCC/OSI 21-character symbols, broker tradingsymbols, instrument tokens), building and refreshing a chain from instrument dumps, expiry timestamps and time zones, choosing bid/ask/mid/mark/last, filtering stale and wide quotes, open interest vs volume timing, the underlying or future to pair with each option, and storing chains point in time. Use when ingesting option chains from a broker or data vendor, building an options screener or dashboard, or debugging wrong Greeks, missing strikes or mismatched expiries.
---

# Option chain data

Pricing code is only as good as the chain it receives. Get identifiers,
timestamps and quote choice right before touching Greeks.

## Identify contracts exactly

- **US (OCC / OSI symbology):** 21 characters: root padded to 6, expiry
  `YYMMDD`, `C`/`P`, strike x 1000 padded to 8 digits.
  `AAPL  261218C00190000` is the AAPL 190 call expiring 18 Dec 2026.
  Store the components (root, expiry, right, strike, multiplier) as fields;
  parse the string only at the boundary.
- **Adjusted contracts** after splits or special dividends get a new root
  (`AAPL1`) and a non-standard deliverable; never assume 100 shares.
- **India:** use the broker's instrument dump (`instrument_token`,
  `tradingsymbol`, `expiry`, `strike`, `lot_size`, `tick_size`) refreshed
  every morning, and key on exchange + tradingsymbol. Do not compose
  tradingsymbols by string formatting (weekly and monthly formats differ).
- **IBKR TWS API:** `secType="OPT"`, `symbol`, `lastTradeDateOrContractMonth`
  (`YYYYMMDD`), `strike`, `right`, `multiplier`, `exchange="SMART"` and
  `tradingClass` to tell weekly from monthly (`SPXW` vs `SPX`). Resolve with
  `reqContractDetails` and store the `conId`.

## Expiry and time

- Store expiry as a timestamp with time zone: the last trading or settlement
  moment, not a date. NSE options stop trading at 15:30 IST on expiry day;
  US equity options at 16:00 ET; AM-settled index options (standard SPX)
  settle on the next morning's opening prices while PM-settled weeklies
  (SPXW) settle at the close.
- Compute time to expiry from that timestamp in UTC; convert for display only.
- Holidays move expiries (NSE: to the previous trading day). Take expiries
  from the instrument dump or exchange calendar, never from "every Tuesday".

## Which price

| Field | Use for | Watch out |
|---|---|---|
| Bid / ask | fills, liquidity, IV range | zero or missing bid on deep OTM strikes |
| Mid | IV and Greeks when the spread is tight | meaningless when the spread is wide relative to price |
| Mark (broker) | margin and P&L display | each broker computes it differently |
| Last | almost nothing | can be stale by minutes or days on illiquid strikes |
| Settlement / close price | end-of-day valuation, expiry settlement | exchange's official price, not your last quote |

Filter before computing IV: both sides present, spread under a set
percentage of mid (for example 10-20%), quote age under a few seconds
intraday, and price inside no-arbitrage bounds (`options-pricing`).

## Underlying pairing

- Take the underlying (or future) quote at the **same timestamp** as the
  option quote. A 2-second lag on a fast index moves ATM delta and IV.
- Index options: pair with the matching future or an implied forward from
  put-call parity rather than the spot index.
- Record which underlying price you used next to every computed IV.

## Open interest and volume

Exchanges publish OI after the session (sometimes intraday snapshots);
volume is live. A "highest OI strike" signal computed intraday may use
yesterday's OI. Store the timestamp of each field.

## Storage

- Append-only snapshots: (timestamp, contract id, bid, ask, bid size, ask
  size, last, volume, OI, underlying price), partitioned by date and
  underlying. Parquet or a columnar database works well.
- Keep expired contracts and their final settlement prices; backtests need
  them (`options-backtesting`).
- Store contract terms (lot size, multiplier, tick size) per date; they
  change.

## Checklist

- [ ] Contracts stored as structured fields plus the broker/exchange id.
- [ ] Expiry stored as a zoned timestamp; holidays from the exchange calendar.
- [ ] IV computed from filtered mids with a same-time underlying.
- [ ] Each field carries its own timestamp (quote, OI, underlying).
- [ ] Instrument dumps refreshed daily; unknown contracts fail closed.
