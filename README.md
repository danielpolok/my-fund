# my-fund

Shared agent resources for working with myFund portfolio data.

## Layout

- `skills/` contains provider-neutral skill source folders.
- `.agents/skills/` contains discovery links for agents that scan that location.
- `resources/` contains shared reference inputs.
- `mcp/` is reserved for future MCP server definitions and helpers.

## Local setup

Copy the skill config template and fill in local values:

```bash
cp skills/my-fund/.env.example skills/my-fund/.env
```

Alternatively, export the required variables in your shell:

```bash
export API_KEY=...
export MYFUND_PORTFEL=...
```

Local `.env` files are ignored by git.
