---
name: my-fund
description: Use when analyzing a myFund.pl investment portfolio through the live API, answering portfolio questions, comparing performance to benchmark, or investigating holdings, allocation, and time series data. This skill provides data analysis only and must not render UI, dashboards, charts, diagrams, HTML reports, or Mermaid output.
license: MIT
compatibility: Requires Python 3.11+ and network access to https://myfund.pl.
---

# my-fund

Use this skill for myFund portfolio analysis. This skill is operational: fetch live data through the helper script instead of reasoning only from static docs.

## Workflow

1. Resolve the portfolio selector.
   - If the user clearly names a portfolio in the prompt, use that exact value.
   - Otherwise use `MYFUND_PORTFEL` from exported environment variables or the skill-local `.env`.
   - If `MYFUND_PORTFEL` is absent, `MYFUND_PORTFOLIO` is also accepted as a compatibility alias.
   - If neither is available, ask the user which portfolio to use.
2. Load credentials from exported environment variables or the skill-local `.env`.
   - `MYFUND_API_KEY` is required.
   - `MYFUND_API_BASE_URL` is optional and defaults to `https://myfund.pl/API/v1`.
   - `MYFUND_API_BASE_URL` must use `https://` and point to `myfund.pl` unless `MYFUND_ALLOW_CUSTOM_API_BASE_URL=true` is set for a controlled test or staging endpoint.
   - Exported environment variables override values from `.env`.
   - Use `.env.example` as a template for local setup, but do not load it as runtime config.
   - If required config is missing, clearly tell the user whether the skill-local `.env` file was not found or the file exists but lacks the required value.
   - Do not expose credential values in answers.
3. Fetch live data with `scripts/fetch_portfolio.py`.
   - Run scripts from the skill directory or with an absolute path to the script.
   - The scripts load exported environment variables and the skill-local `.env`.
   - Do not hand-build ad hoc API calls unless you are debugging the helper itself.
4. Check `status.code` before analyzing the payload.
   - `"0"` means success.
   - `"7"` means the portfolio was not found.
   - Other values should be treated as API failure and surfaced to the user.
5. Answer using direct API facts first, then derived analysis if needed.
   - Distinguish clearly between returned values and computed inferences.
   - Mention the 5-minute API cache when freshness matters.

## Scripts

- `scripts/fetch_portfolio.py`
  - Canonical fetcher for live portfolio data.
  - Default output is normalized JSON intended for downstream reasoning.
  - Use `--raw` only when you need the original payload.
- `scripts/inspect_portfolio_response.py`
  - Structural inspector for live responses.
  - Use when validating shape changes, type inconsistencies, or sparse fields.

## References

- `references/api-reference.md`
  - Documented API contract from the OpenAPI file.
- `references/observed-response.md`
  - Notes from live endpoint investigation and known spec/runtime differences.
- `references/question-catalog.md`
  - Supported question families and the data needed to answer them.
- `references/analysis-rules.md`
  - Boundaries for allowed derivations and unsupported asks.

## Answering Rules

- Prefer the normalized fetch output for analysis.
- Quote the relevant metric names in the answer when helpful.
- Surface missing sections explicitly instead of guessing.
- Do not render UI elements, dashboards, charts, diagrams, HTML reports, or Mermaid output from this skill.
- Decline unsupported asks such as transaction history, trade execution, write actions, or rebalancing operations.
