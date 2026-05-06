# AGENTS.md

## Scope

These instructions apply to every MCP server package under `mcp-servers/src/*/`.

## MCP Development

- Keep servers read-only. New tools must not mutate myFund.pl state.
- Prefer FastMCP patterns already present in `mcp-servers/src/my-fund/src/my_fund_mcp/server.py`.
- Tool names should keep the `myfund_` prefix and match MCP tool-name constraints.
- Every tool must have a title, concise description, constrained input model, structured output where possible, and read-only annotations.
- Upstream API or config failures should surface as MCP tool execution errors for analysis tools.
- Keep rate limiting, secret redaction, and API base URL validation intact when touching request code.

## Runtime Configuration

- Required secrets: `MYFUND_API_KEY`, `MYFUND_PORTFEL`.
- Optional alias: `MYFUND_PORTFOLIO`.
- Optional controls: `MYFUND_API_BASE_URL`, `MYFUND_ALLOW_CUSTOM_API_BASE_URL`, `MY_FUND_MCP_TRANSPORT`, `MY_FUND_MCP_MAX_REQUESTS_PER_MINUTE`.
- Keep runtime configuration names aligned in code, `README.md`, `.env.example`, `server.json`, and tests.
- The upstream myFund query parameter is still named `apiKey`; do not rename it.

## Checks

Run from the changed server directory, for example `mcp-servers/src/my-fund/`, after MCP code or metadata changes:

```bash
uv sync --locked
uv run python -m unittest discover -s tests
uv run python -m compileall src tests
uv build
```

Run from the repo root before finishing:

```bash
python3 scripts/validate_release.py
```

`uv build` creates ignored `dist/` files under the server directory; do not add them to git.
