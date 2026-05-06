# my-fund MCP

Read-only MCP server for myFund.pl portfolio analysis, based on the repository's `skills/my-fund` workflow.

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

- `API_KEY`
- `MYFUND_PORTFEL`

Optional:

- `MYFUND_PORTFOLIO`: compatibility alias for `MYFUND_PORTFEL`
- `MYFUND_API_BASE_URL`: defaults to `https://myfund.pl/API/v1`

Environment variables take precedence. If not exported, the server also checks:

1. `mcp/.env`
2. `skills/my-fund/.env`

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
