# Analysis Rules

Use these rules when answering from the fetched myFund payload.

## Direct Facts First

- Prefer exact values returned by the API over paraphrase-heavy summaries.
- Quote the metric or section used when it materially improves clarity.
- If the relevant section is missing, say so explicitly.

## Allowed Derived Analysis

- Rank holdings by value, weight, gain, loss, or return.
- Summarize concentration using the largest holdings or allocation weights.
- Compare portfolio return to benchmark return across available windows or time series.
- Describe trends from `wartoscWCzasie`, `wkladWCzasie`, `zyskWCzasie`, and `stopaZwrotuWCzasie`.
- Compute simple deltas and ordering from normalized numeric fields.

## Boundaries

- Do not invent transaction history or cash-flow events that are not present in the payload.
- Do not claim the API supports trading, edits, or rebalancing actions.
- Do not overstate freshness; identical requests may be cached for 5 minutes.
- Do not assume that absent top-level sections imply zero values.
- Do not render UI elements, dashboards, charts, diagrams, HTML reports, or Mermaid output.

## Answer Framing

- Separate API facts from computed interpretation when both appear in the answer.
- When comparing current data to benchmark or time series, state the basis of comparison.
- When `status.code` is not `"0"`, stop the analysis and report the API status instead.
