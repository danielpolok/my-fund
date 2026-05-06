# my-fund MCP

<!-- mcp-name: io.github.danielpolok/my-fund-mcp -->

Read-only MCP server for myFund.pl portfolio analysis, based on the repository's `skills/my-fund` workflow.

The server is intentionally read-only. It fetches portfolio data, normalizes response shapes, and returns structured JSON for agent analysis. It does not execute trades, rebalance accounts, mutate upstream state, or render dashboards.

## Tools

- `myfund_fetch_portfolio`: fetch the raw or normalized live portfolio snapshot.
- `myfund_inspect_portfolio`: inspect response shape, section counts, and type samples.
- `myfund_get_portfolio_summary`: return status, latest metrics, and portfolio-level summary.
- `myfund_list_holdings`: list holdings sorted by value, weight, profit, loss, return, or name.
- `myfund_get_allocations`: return allocation by asset type, security, or both.
- `myfund_get_performance`: return period return metrics and time-series performance data.

All tools are read-only. The myFund API may cache identical requests for 5 minutes.

## Configuration

Required:

- `MYFUND_API_KEY`: myFund.pl API key.
- `MYFUND_PORTFEL`: portfolio selector passed as the API `portfel` parameter.

Optional:

- `MYFUND_PORTFOLIO`: compatibility alias for `MYFUND_PORTFEL`
- `MYFUND_API_BASE_URL`: defaults to `https://myfund.pl/API/v1`
- `MYFUND_ALLOW_CUSTOM_API_BASE_URL`: set to `true` only for a controlled test or staging endpoint outside `myfund.pl`
- `MY_FUND_MCP_TRANSPORT`: `stdio`, `streamable-http`, or `sse`; defaults to `stdio`
- `MY_FUND_MCP_MAX_REQUESTS_PER_MINUTE`: per-process myFund API call limit; defaults to `30`

Environment variables take precedence. If not exported, the server also checks:

1. `mcp/.env`
2. `skills/my-fund/.env`

`MYFUND_API_BASE_URL` must use `https://` and point to `myfund.pl` unless `MYFUND_ALLOW_CUSTOM_API_BASE_URL=true` is explicitly set.

## Run

```bash
cd mcp
uv run --with "mcp[cli]" my-fund-mcp
```

To run the streamable HTTP transport:

```bash
cd mcp
MY_FUND_MCP_TRANSPORT=streamable-http uv run --with "mcp[cli]" my-fund-mcp
```

The default transport is `stdio`, which is usually the right choice for local MCP clients.

Streamable HTTP runs on FastMCP's localhost defaults with DNS rebinding protection. Do not expose it publicly without adding authentication, network access controls, and deployment-layer rate limiting.

## Publishing

`server.json` is the MCP Registry metadata source for this server. For a public registry release:

1. Keep `pyproject.toml`, `src/my_fund_mcp/__init__.py`, and `server.json` versions aligned.
2. Publish the `my-fund-mcp` package to PyPI.
3. Keep the `mcp-name` marker in this README aligned with `server.json`.
4. Run repository validation from the repo root:

```bash
python3 scripts/validate_release.py
```

Then authenticate and publish with `mcp-publisher` from this directory.
