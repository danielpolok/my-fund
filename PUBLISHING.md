# Publishing Standards

This repository publishes two agent-facing artifacts:

- `mcp/`: a read-only Python FastMCP server.
- `skills/my-fund/`: a portable Agent Skill with helper scripts and references.

These standards are based on the MCP specification and registry docs current on 2026-05-06, plus the Agent Skills specification and skill-creator guidance.

## MCP Release Standard

Use `mcp/server.json` as the MCP Registry metadata source.

Required release gates:

- Keep the package version aligned across `mcp/pyproject.toml`, `mcp/src/my_fund_mcp/__init__.py`, and `mcp/server.json`.
- Keep the registry name aligned between `mcp/server.json` and the PyPI verification marker in `mcp/README.md`.
- Publish the package artifact first; the MCP Registry hosts metadata, not package files.
- For PyPI registry ownership verification, keep `<!-- mcp-name: io.github.danielpolok/my-fund-mcp -->` in the package README.
- Keep every tool read-only unless a future release explicitly adds a write path and a review gate for destructive operations.
- Define constrained input schemas, output schemas where possible, and tool annotations (`readOnlyHint`, `destructiveHint`, `idempotentHint`, `openWorldHint`).
- Return upstream/API failures as MCP tool execution errors for analysis tools; diagnostic/raw tools must make upstream failure status explicit and must not hide it in an ambiguous `error` key.
- Keep a conservative per-process rate limit enabled for local transports and add deployment-layer rate limiting for any remote transport.
- Default local transport to `stdio`; use Streamable HTTP only with localhost binding, Origin/DNS rebinding protection, authentication, and deployment-layer rate limiting when exposed remotely.
- Sanitize upstream output and error messages so API keys, portfolio selectors, and local paths are not leaked unnecessarily.

Validation:

```bash
python3 scripts/validate_release.py
cd mcp
uv run python -m unittest discover -s tests
uv run python -m compileall src tests
```

Publishing:

```bash
cd mcp
python -m build
twine upload dist/*
mcp-publisher login github
mcp-publisher publish
```

## Skill Release Standard

The skill must remain lean and operational.

Required release gates:

- `skills/my-fund/SKILL.md` frontmatter must include `name`, `description`, `license`, and compatibility notes when runtime assumptions matter.
- The `name` must match the directory name and use lowercase letters, numbers, and hyphens only.
- Keep `SKILL.md` under 500 lines and use `references/` for detailed API contracts, analysis rules, and edge cases.
- List runnable scripts in `SKILL.md`; scripts must be non-interactive, support `--help`, emit structured JSON to stdout, and send diagnostics to stderr.
- Do not place README/changelog/setup docs inside the skill directory. Put publishing and operator documentation at repo root.
- Keep `agents/openai.yaml` aligned with the skill purpose; it is UI metadata, not agent instruction content.
- Never commit real `.env` files, portfolio snapshots, rendered reports, or generated output.

Validation:

```bash
python3 scripts/validate_release.py
python3 skills/my-fund/scripts/fetch_portfolio.py --help
python3 skills/my-fund/scripts/inspect_portfolio_response.py --help
```

## Source References

- MCP tools, output schemas, error handling, and security considerations: https://modelcontextprotocol.io/specification/2025-11-25/server/tools
- MCP transports and Streamable HTTP security requirements: https://modelcontextprotocol.io/specification/2025-11-25/basic/transports
- MCP Registry overview and trust model: https://modelcontextprotocol.io/registry/about
- MCP Registry package types and PyPI verification: https://modelcontextprotocol.io/registry/package-types
- MCP Registry publishing quickstart: https://modelcontextprotocol.io/registry/quickstart
- MCP Registry versioning guidance: https://modelcontextprotocol.io/registry/versioning
- Agent Skills specification: https://agentskills.io/specification
- Agent Skills best practices: https://agentskills.io/skill-creation/best-practices
- Agent Skills script guidance: https://agentskills.io/skill-creation/using-scripts
