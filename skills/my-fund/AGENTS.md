# AGENTS.md

## Scope

These instructions apply to the `my-fund` Agent Skill under `skills/my-fund/`.

## Skill Development

- Keep `SKILL.md` concise and operational; move detailed API contracts, analysis rules, and edge cases into `references/`.
- Do not add `README.md`, changelogs, setup guides, or other auxiliary docs inside the skill directory.
- Scripts must be deterministic, non-interactive, support `--help`, emit JSON to stdout for data output, and send diagnostics to stderr.
- Use the canonical helper scripts for live API access. Do not duplicate API-fetch logic in prompts or docs.
- Keep `agents/openai.yaml` aligned with `SKILL.md`; it is UI metadata, not agent instruction content.

## Runtime Configuration

- Required secrets: `MYFUND_API_KEY`, `MYFUND_PORTFEL`.
- Optional alias: `MYFUND_PORTFOLIO`.
- Optional base URL controls: `MYFUND_API_BASE_URL`, `MYFUND_ALLOW_CUSTOM_API_BASE_URL`.
- The upstream API request parameter remains `apiKey`; the local environment variable is `MYFUND_API_KEY`.
- Do not commit `.env`, generated JSON, HTML reports, portfolio snapshots, or rendered outputs.

## Checks

Run from the repo root after skill changes:

```bash
python3 scripts/validate_release.py
python3 skills/my-fund/scripts/fetch_portfolio.py --help
python3 skills/my-fund/scripts/inspect_portfolio_response.py --help
```

If script behavior changes, update both the MCP implementation or references only when the behavior is intentionally shared.
