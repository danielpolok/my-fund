# my-fund MCP app

<!-- mcp-name: io.github.danielpolok/my-fund-app-mcp -->

Read-only MCP app for visualizing myFund.pl portfolio data in an interactive dashboard widget.

This package is a standalone MCP app: it includes its own read-only live API fetch and normalization path, then attaches a `ui://` HTML resource to dashboard tool results. It does not execute trades, rebalance accounts, mutate upstream state, or expose credentials.

## Visualizations

The app can visualize the chartable parts of the normalized myFund payload:

- Portfolio value, invested capital, and profit over time.
- Portfolio return versus the configured benchmark.
- Benchmark delta, calculated as portfolio return minus benchmark return.
- Allocation by asset type and by security.
- Largest holdings by market value and portfolio weight.
- Top gainers and losers by profit.
- Summary KPI tiles for value, profit, daily change, MTD return, YTD return, and holding count.

## Tools

- `myfund_fetch_portfolio`: fetch the raw or normalized live portfolio snapshot.
- `myfund_inspect_portfolio`: inspect response shape, section counts, and type samples.
- `myfund_get_portfolio_summary`: return status, latest metrics, and portfolio-level summary.
- `myfund_list_holdings`: list holdings sorted by value, weight, profit, loss, return, or name.
- `myfund_get_allocations`: return allocation by asset type, security, or both.
- `myfund_get_performance`: return period return metrics and time-series performance data.
- `myfund_show_portfolio_dashboard`: opens the interactive dashboard and returns the dashboard JSON payload.
- `myfund_app_get_dashboard_data`: app-only helper used by the widget to refresh or switch time windows.

All tools are read-only. The myFund API may cache identical requests for 5 minutes.

The app also provides the `myfund_portfolio_analysis` prompt, grounded in the same read-only analysis boundary.

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

Environment variables take precedence. If not exported, the app also checks:

1. `mcp-servers/src/my-fund-app/.env`
2. `skills/my-fund/.env`

`MYFUND_API_BASE_URL` must use `https://` and point to `myfund.pl` unless `MYFUND_ALLOW_CUSTOM_API_BASE_URL=true` is explicitly set.

## Run

```bash
cd mcp-servers/src/my-fund-app
uv run my-fund-app-mcp
```

To run the streamable HTTP transport for local app testing:

```bash
cd mcp-servers/src/my-fund-app
MY_FUND_MCP_TRANSPORT=streamable-http uv run my-fund-app-mcp
```

Streamable HTTP is local-development only unless authentication, network controls, and deployment rate limiting are added.

## Publishing

`server.json` is the MCP Registry metadata source for this app. For a public registry release:

1. Keep `pyproject.toml`, `src/my_fund_app_mcp/__init__.py`, and `server.json` versions aligned.
2. Publish the `my-fund-app-mcp` package to PyPI.
3. Keep the `mcp-name` marker in this README aligned with `server.json`.
4. Run repository validation from the repo root:

```bash
python3 scripts/validate_release.py
```

Then authenticate and publish with `mcp-publisher` from this directory.
