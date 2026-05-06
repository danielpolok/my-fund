# my-fund MCP servers

This directory contains myFund-related MCP server packages.

## Layout

- `src/my-fund/`: read-only portfolio analysis MCP server distributed as `my-fund-mcp`.

Each server under `src/` is a standalone package with its own `pyproject.toml`, `server.json`, README, source package, tests, and lockfile.

## Checks

Run release validation from the repository root:

```bash
python3 scripts/validate_release.py
```

Run server-specific checks from the changed server directory:

```bash
cd mcp-servers/src/my-fund
uv sync --locked
uv run python -m unittest discover -s tests
uv run python -m compileall src tests
```
