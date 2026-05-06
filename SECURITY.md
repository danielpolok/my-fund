# Security

## Supported Artifacts

Security fixes apply to the current `main` branch until tagged releases are introduced.

## Reporting

Report suspected credential leaks, unsafe tool behavior, or API exposure issues through GitHub issues if no private advisory channel is configured for the repository.

Do not include real API keys, portfolio selectors, exported snapshots, or account data in reports.

## Security Boundaries

- The MCP server and skill are read-only wrappers around the myFund.pl API.
- `MYFUND_API_KEY` and `MYFUND_PORTFEL` are secrets and must stay in local environment variables or ignored `.env` files.
- `MYFUND_API_BASE_URL` must use `https://` and defaults to `https://myfund.pl/API/v1`.
- Custom API hosts require `MYFUND_ALLOW_CUSTOM_API_BASE_URL=true` and should only be used for controlled test or staging endpoints.
- Streamable HTTP is intended for localhost development unless authentication, network controls, and deployment rate limits are added.
