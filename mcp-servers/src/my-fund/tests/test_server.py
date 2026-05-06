from __future__ import annotations

import asyncio
import re
import unittest
from unittest.mock import patch

from my_fund_mcp.api import MyFundError
from my_fund_mcp.server import (
    MAX_REQUEST_TIMESTAMPS,
    PortfolioInput,
    _enforce_rate_limit,
    _portfolio_snapshot,
    mcp,
)


TOOL_NAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


class ServerContractTests(unittest.TestCase):
    def test_tools_have_publishable_contract_metadata(self) -> None:
        tools = asyncio.run(mcp.list_tools())

        self.assertGreaterEqual(len(tools), 6)
        for tool in tools:
            self.assertRegex(tool.name, TOOL_NAME_RE)
            self.assertTrue(tool.title)
            self.assertTrue(tool.description)
            self.assertEqual(tool.inputSchema.get("type"), "object")
            self.assertIsNotNone(tool.outputSchema)
            self.assertIsNotNone(tool.annotations)
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.destructiveHint)
            self.assertTrue(tool.annotations.idempotentHint)
            self.assertTrue(tool.annotations.openWorldHint)

    def test_snapshot_propagates_configuration_errors_as_tool_errors(self) -> None:
        with patch(
            "my_fund_mcp.server.resolve_config",
            side_effect=MyFundError("Missing MYFUND_API_KEY."),
        ):
            with self.assertRaisesRegex(MyFundError, "Missing MYFUND_API_KEY"):
                _portfolio_snapshot(PortfolioInput())

    def test_rate_limit_rejects_excess_calls(self) -> None:
        MAX_REQUEST_TIMESTAMPS.clear()
        try:
            with patch.dict("os.environ", {"MY_FUND_MCP_MAX_REQUESTS_PER_MINUTE": "1"}):
                _enforce_rate_limit()
                with self.assertRaisesRegex(MyFundError, "Rate limit exceeded"):
                    _enforce_rate_limit()
        finally:
            MAX_REQUEST_TIMESTAMPS.clear()


if __name__ == "__main__":
    unittest.main()
