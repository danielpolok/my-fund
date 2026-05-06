# my-fund

Shared agent resources for working with myFund.pl portfolio data.

This repository contains myFund-related Agent Skills and MCP servers. Each artifact is read-only and helps an agent fetch or analyze myFund API data for portfolio-analysis questions.

## Repository Layout

- `skills/*/` contains provider-neutral skill sources.
- `mcp-servers/src/*/` contains Python FastMCP server packages backed by the official `mcp` SDK package.

Current artifacts:

- `skills/my-fund/`: portable myFund portfolio analysis skill.
- `mcp-servers/src/my-fund/`: Python FastMCP server distributed as `my-fund-mcp`.

Local discovery links and source API documents can be kept outside version control when needed.

## my-fund Skill

The `my-fund` skill is for data analysis only. It does not render UI elements, dashboards, charts, diagrams, HTML reports, or Mermaid output.

Capabilities:

- Fetch live portfolio data from the myFund API.
- Normalize API responses into JSON for downstream reasoning.
- Answer portfolio overview questions such as total value, currency, daily change, total return, and profit or loss.
- Analyze holdings by value, weight, profit, loss, return, sector, account, risk bucket, or asset type.
- Analyze allocation by asset type or security.
- Compare portfolio performance with the configured benchmark when benchmark data is present.
- Inspect response shape and surface missing or unexpected sections.
- Clearly report API status failures before doing analysis.

Unsupported:

- Transaction history analysis when it is not present in the returned payload.
- Trade execution, rebalancing, deposits, withdrawals, or account-management actions.
- UI, dashboard, chart, HTML, diagram, or Mermaid rendering.

## Required Credentials

The skill needs myFund API access credentials and a portfolio selector.

Required:

- `MYFUND_API_KEY`: your myFund API key.
- `MYFUND_PORTFEL`: the myFund portfolio name or selector to pass as the API `portfel` parameter.

Optional:

- `MYFUND_API_BASE_URL`: defaults to `https://myfund.pl/API/v1`.
- `MYFUND_PORTFOLIO`: compatibility alias for `MYFUND_PORTFEL`.
- `MYFUND_ALLOW_CUSTOM_API_BASE_URL`: set to `true` only for a controlled test or staging endpoint outside `myfund.pl`.

Credential precedence:

1. Exported environment variables.
2. The skill-local `.env` file.
3. Built-in default only for `MYFUND_API_BASE_URL`.

## Local Setup

Copy the template and fill in local values:

```bash
cp skills/my-fund/.env.example skills/my-fund/.env
```

Example `.env` shape:

```bash
MYFUND_API_KEY=
MYFUND_PORTFEL=
MYFUND_API_BASE_URL=https://myfund.pl/API/v1
MYFUND_ALLOW_CUSTOM_API_BASE_URL=false
```

Alternatively, export values in your shell:

```bash
export MYFUND_API_KEY=...
export MYFUND_PORTFEL=...
export MYFUND_API_BASE_URL=https://myfund.pl/API/v1
```

Local `.env` files are ignored by git. Do not commit real API keys, portfolio names, exported snapshots, generated reports, or portfolio JSON.

## Quick Checks

Verify the helper can read config without printing secrets:

```bash
PYTHONPATH=skills/my-fund/scripts python3 -c 'from myfund_api import resolve_config; c = resolve_config(None); print(bool(c.api_key), bool(c.portfolio), c.api_base_url)'
```

Fetch normalized portfolio JSON:

```bash
python3 skills/my-fund/scripts/fetch_portfolio.py
```

Inspect response shape:

```bash
python3 skills/my-fund/scripts/inspect_portfolio_response.py
```

Run the MCP server over stdio:

```bash
cd mcp-servers/src/my-fund
uv run my-fund-mcp
```

## Publishing Standards

Release and publishing checks live in `PUBLISHING.md`. Each MCP Registry manifest lives at `mcp-servers/src/<name>/server.json`; keep its `name` and `version` aligned with that MCP's `README.md`, `pyproject.toml`, and package `__init__.py`.

Before publishing a skill or MCP release, run:

```bash
python3 scripts/validate_release.py
cd mcp-servers/src/my-fund
uv run python -m unittest discover -s tests
```

## License

MIT. See `LICENSE`.
