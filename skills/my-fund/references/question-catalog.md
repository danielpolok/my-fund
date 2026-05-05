# Supported Question Catalog

Use this map to decide whether the API can answer a user question and which response sections are required.

## Portfolio Overview

- "What is my portfolio worth?"
  - Use `portfel.wartosc`, `portfel.waluta`, `portfel.data`
- "What is my total profit or loss?"
  - Use `portfel.zysk`, `portfel.zmiana`
- "What changed today?"
  - Use `portfel.zyskDzienny`, `portfel.zmianaDzienna`
- "How many holdings do I have?"
  - Use `portfel.tickersCount` or count `tickers`

## Holdings Analysis

- "What do I own?"
  - Use `tickers`
- "What are my largest positions?"
  - Rank by `tickers[*].wartosc` or `tickers[*].udzial`
- "Which holdings are winning or losing?"
  - Use `tickers[*].zysk`, `tickers[*].zmiana`
- "What is the return on each holding?"
  - Use `tickers[*].zmiana`

## Allocation and Classification

- "What is my allocation by asset class?"
  - Use `struktura`
- "What is my allocation by security?"
  - Use `strukturaWalory`
- "How concentrated is the portfolio?"
  - Use `strukturaWalory` or holding weights from `tickers`
- "Which holdings are in each sector, risk bucket, or account?"
  - Use `tickers[*].sektor`, `tickers[*].ryzyko`, `tickers[*].kontoInvName`

## Performance and Benchmarking

- "What is my 1M, 1Y, or YTD return?"
  - Use `portfel.zmianaM`, `portfel.zmianaR`, `portfel.zmianaRdD`, and related period fields
- "Did I beat the benchmark?"
  - Use `benchWCzasie`, `stopaZwrotuWCzasie`, and `portfel.benchName`
- "How did performance evolve over time?"
  - Use `wartoscWCzasie`, `zyskWCzasie`, `wkladWCzasie`, `stopaZwrotuWCzasie`

## Freshness and Status

- "Did the API request succeed?"
  - Use `status`
- "Is this data fresh?"
  - Use the documented 5-minute cache rule and the most recent available `data` field
- "Why is the portfolio missing?"
  - Use `status.code`, `status.text`

## Unsupported Questions

Decline or narrow questions about:

- transaction history,
- order placement,
- write or update operations,
- rebalancing execution,
- deposit or withdrawal event logs,
- UI dashboards, charts, diagrams, HTML reports, or Mermaid output,
- any user/account management action outside the returned portfolio snapshot.
