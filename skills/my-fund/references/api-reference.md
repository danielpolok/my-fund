# myFund API Reference

This skill uses the documented myFund API endpoint:

```http
GET https://myfund.pl/API/v1/getPortfel.php?portfel=<PORTFOLIO_NAME>&apiKey=<API_KEY>&format=json
```

## Request Parameters

- `portfel`
  - Required.
  - Portfolio name or selector string as displayed in the myFund account.
- `apiKey`
  - Required.
  - Loaded from `.env` as `API_KEY`.
- `format`
  - Required.
  - Only `json` is documented.

## Status Handling

The response always includes a `status` object.

- `status.code = "0"`
  - Success.
- `status.code = "1"`
  - Logical or API error. Use `status.text` for the message.
- `status.code = "7"`
  - Portfolio not found.

## Top-Level Response Sections

- `status`
  - API result code and text.
- `portfel`
  - Portfolio-level summary row.
- `tickers`
  - Holdings keyed by internal numeric ID strings.
- `struktura`
  - Allocation by asset category.
- `strukturaKolor`
  - Hex colors matching `struktura`.
- `strukturaWalory`
  - Allocation by security.
- `strukturaWaloryKolor`
  - Hex colors matching `strukturaWalory`.
- `zyskWCzasie`
  - Profit and loss over time.
- `wartoscWCzasie`
  - Total portfolio value over time.
- `wkladWCzasie`
  - Invested capital over time.
- `benchWCzasie`
  - Benchmark return over time.
- `stopaZwrotuWCzasie`
  - Portfolio return over time.
- `zmianaDzienna`
  - Daily portfolio changes over time.

## Summary Fields in `portfel`

The documented summary object can include:

- Identity: `nazwa`, `waluta`, `data`, `benchName`, `tickersCount`
- Value and P/L: `wartosc`, `zmiana`, `zysk`, `zmianaDzienna`, `zyskDzienny`
- Exposure: `udzial`, `typ`, `typOrg`
- Quantity and pricing: `close`, `liczbaJednostek`
- Classification and grouping: `kontoInvName`, `sektor`, `grupowanieKonto`, `grupowanieSektor`, `grupowanieWalor`, `grupowanieRyzyko`, `grupowaniePortfel`
- Period returns: `zmianaW`, `zmiana2W`, `zmianaM`, `zmiana3M`, `zmiana6M`, `zmianaR`, `zmiana3R`, `zmiana5R`, `zmianaMdD`, `zmianaRdD`

## Holding Fields in `tickers`

Each holding may include:

- Identity: `tickerClear`, `nazwa`, `portfelOrg`
- Price and quantity: `close`, `cenaZakupu`, `liczbaJednostek`
- P/L and exposure: `wartosc`, `udzial`, `zmiana`, `zmianaDzienna`, `zysk`
- Classification: `typ`, `typOrg`, `kontoInvName`, `sektor`, `ryzyko`
- Timing: `data`, `dataInvStart`, `okresInwestycji`

## Type Notes

The documented API mixes native numbers and numeric strings.

- Many return values are strings and may include a leading `+`.
- Time-series maps are documented as date-keyed objects with string values.
- Some numeric-looking fields may appear as numbers for one asset type and strings for another.

The helper scripts normalize these fields into numeric types where safe.
