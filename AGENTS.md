# AGENTS.md

## Scope

These instructions apply to the whole repository. More specific `AGENTS.md` files under subdirectories take precedence for files in those trees.

## Project Overview

This repository publishes multiple agent-facing artifacts for read-only myFund.pl portfolio analysis:

- `mcp-servers/src/*/`: Python FastMCP servers and their MCP Registry metadata.
- `skills/*/`: portable Agent Skills with helper scripts and references.

The project never executes trades, rebalances portfolios, mutates myFund account data, or renders dashboards/charts from the skill.

## Required Commands

Run the checks relevant to the files you change:

```bash
python3 scripts/validate_release.py
cd mcp-servers/src/my-fund && uv run python -m unittest discover -s tests
cd mcp-servers/src/my-fund && uv run python -m compileall src tests
python3 skills/my-fund/scripts/fetch_portfolio.py --help
python3 skills/my-fund/scripts/inspect_portfolio_response.py --help
```

Use `uv` for MCP package commands. If sandboxing blocks `uv` from reading its cache, rerun the same command with approval rather than replacing the workflow.

## Repository Rules

- Keep changes narrow and preserve the read-only data-analysis boundary.
- Prefer `rg`/`rg --files` for search.
- Do not commit `.env`, `.venv`, `dist`, `output`, `__pycache__`, portfolio snapshots, generated reports, or real account data.
- Keep environment variable names aligned across code, docs, examples, MCP `server.json` files, tests, and `scripts/validate_release.py`.
- The myFund upstream query parameter remains `apiKey`; the local secret environment variable is `MYFUND_API_KEY`.
- Update tests or validation when changing MCP tool contracts, runtime configuration, packaging metadata, or skill metadata.

## Security

- Treat `MYFUND_API_KEY` and `MYFUND_PORTFEL` as secrets.
- Do not print, log, or include real credentials or portfolio selectors in docs, tests, or examples.
- `MYFUND_API_BASE_URL` must default to `https://myfund.pl/API/v1`; custom hosts require explicit opt-in for controlled test/staging use.
- Streamable HTTP is local-development only unless authentication, network controls, and deployment rate limiting are added.

## Publishing

Before publishing an artifact, follow `PUBLISHING.md` and keep each artifact's metadata aligned:

- `mcp-servers/src/<name>/pyproject.toml`
- `mcp-servers/src/<name>/src/<package>/__init__.py`
- `mcp-servers/src/<name>/server.json`
- `mcp-servers/src/<name>/README.md`
- `skills/<name>/SKILL.md`
- `skills/<name>/agents/openai.yaml`
