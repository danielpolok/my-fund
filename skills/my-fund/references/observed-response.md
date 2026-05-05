# Observed Response Notes

This file records what was actually observed from the live endpoint during implementation.

## Investigation Date

- 2026-03-24

## Request Used

The live probe used the documented endpoint with a deliberately missing portfolio selector:

```http
GET /API/v1/getPortfel.php?portfel=__codex_missing__&apiKey=<redacted>&format=json
```

## Observed Error Payload

The live endpoint returned:

```json
{
  "status": {
    "code": "7",
    "text": "Portfel nie został znaleziony! Prawdopodobnie go usunąłeś."
  }
}
```

The success probe used the configured default portfolio from `.env` through the helper script.

## Confirmed Runtime Behavior

- The endpoint is reachable at `https://myfund.pl/API/v1/getPortfel.php`.
- A missing or invalid portfolio can return a payload containing only `status`.
- `status.code = "7"` is confirmed in practice for portfolio-not-found.
- A successful request returns all documented top-level sections:
  - `status`
  - `portfel`
  - `tickers`
  - `struktura`
  - `strukturaKolor`
  - `strukturaWalory`
  - `strukturaWaloryKolor`
  - `zyskWCzasie`
  - `wartoscWCzasie`
  - `wkladWCzasie`
  - `benchWCzasie`
  - `stopaZwrotuWCzasie`
  - `zmianaDzienna`
- The inspected success payload contained:
  - 10 holdings
  - 3 asset-allocation categories
  - 10 security-allocation entries
  - 335 points in `zyskWCzasie`, `wartoscWCzasie`, `wkladWCzasie`, `benchWCzasie`, and `stopaZwrotuWCzasie`
  - 1 point in `zmianaDzienna`
- Mixed typing is confirmed in practice:
  - `portfel.close` is a native float
  - `portfel.wartosc` is a numeric string such as `"56853.84"`
  - period returns such as `portfel.zmiana3M` can be signed strings such as `"+2.56"`
  - holding fields such as `tickers[6].liczbaJednostek`, `tickers[6].wartosc`, and `tickers[6].zysk` are numeric strings
  - time-series values such as `wartoscWCzasie[2025-04-24]` and `benchWCzasie[2025-04-24]` are numeric strings
- `status.code = "0"` and `status.text = "OK!"` are confirmed in practice for success.

## Operational Implications

- The skill must not assume any section besides `status` is present.
- The fetch script should always inspect `status.code` before deeper analysis.
- The inspection script should report missing sections explicitly.
- The runtime helper accepts `MYFUND_PORTFEL` as the preferred default portfolio variable and `MYFUND_PORTFOLIO` as a compatibility alias.
- Even on success, time-series density can vary by field; `zmianaDzienna` should not be assumed to have the same history length as the other series.
- The fetch helper's normalization step is required for reliable downstream analysis because many numeric-looking values arrive as strings.
