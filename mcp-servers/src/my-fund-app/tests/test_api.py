from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from my_fund_app_mcp.api import (
    MyFundError,
    RuntimeEnv,
    build_request_url,
    config_source_hint,
    load_runtime_env,
    validate_api_base_url,
)


class AppApiStandaloneTests(unittest.TestCase):
    def test_load_runtime_env_checks_app_dotenv_not_basic_mcp_dotenv(self) -> None:
        runtime_env = load_runtime_env()
        checked = [str(path) for path in runtime_env.dotenv_paths]

        self.assertTrue(any("mcp-servers/src/my-fund-app/.env" in path for path in checked))
        self.assertFalse(any("mcp-servers/src/my-fund/.env" in path for path in checked))

    def test_request_url_keeps_myfund_api_key_parameter_name(self) -> None:
        url = build_request_url("https://myfund.pl/API/v1", "portfolio", "secret")

        self.assertIn("apiKey=secret", url)
        self.assertIn("portfel=portfolio", url)

    def test_api_base_url_validation_matches_security_boundary(self) -> None:
        self.assertEqual(
            validate_api_base_url("https://myfund.pl/API/v1/"),
            "https://myfund.pl/API/v1",
        )
        with self.assertRaisesRegex(MyFundError, "https"):
            validate_api_base_url("http://myfund.pl/API/v1")
        with self.assertRaisesRegex(MyFundError, "myfund.pl"):
            validate_api_base_url("https://example.com/API/v1")

    def test_config_hint_mentions_checked_app_dotenv_paths(self) -> None:
        hint = config_source_hint(
            RuntimeEnv(
                values={},
                dotenv_paths=[Path("mcp-servers/src/my-fund-app/.env")],
                found_dotenv_paths=[],
            )
        )

        self.assertIn("mcp-servers/src/my-fund-app/.env", hint)


if __name__ == "__main__":
    unittest.main()
