from __future__ import annotations

import asyncio
import unittest
from unittest.mock import patch

from my_fund_app_mcp.server import (
    DASHBOARD_RESOURCE_URI,
    RESOURCE_MIME_TYPE,
    DashboardInput,
    _dashboard_payload,
    mcp,
    myfund_portfolio_dashboard_widget,
)


class AppServerContractTests(unittest.TestCase):
    def test_dashboard_tool_and_hidden_helper_have_app_metadata(self) -> None:
        tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}

        self.assertIn("myfund_show_portfolio_dashboard", tools)
        self.assertIn("myfund_app_get_dashboard_data", tools)
        self.assertEqual(
            tools["myfund_show_portfolio_dashboard"].meta["ui"]["resourceUri"],
            DASHBOARD_RESOURCE_URI,
        )
        self.assertNotIn(
            "visibility",
            tools["myfund_show_portfolio_dashboard"].meta["ui"],
        )
        self.assertEqual(
            tools["myfund_app_get_dashboard_data"].meta["ui"]["visibility"],
            ["app"],
        )
        for tool in tools.values():
            self.assertTrue(tool.name.startswith("myfund_"))
            self.assertTrue(tool.title)
            self.assertTrue(tool.description)
            self.assertEqual(tool.inputSchema.get("type"), "object")
            self.assertIsNotNone(tool.outputSchema)
            self.assertTrue(tool.annotations.readOnlyHint)
            self.assertFalse(tool.annotations.destructiveHint)

    def test_dashboard_resource_is_mcp_app_html(self) -> None:
        resources = {str(resource.uri): resource for resource in asyncio.run(mcp.list_resources())}

        self.assertIn(DASHBOARD_RESOURCE_URI, resources)
        resource = resources[DASHBOARD_RESOURCE_URI]
        self.assertEqual(resource.mimeType, RESOURCE_MIME_TYPE)
        self.assertFalse(resource.meta["ui"]["prefersBorder"])
        self.assertEqual(resource.meta["ui"]["csp"]["connectDomains"], [])

    def test_widget_html_uses_mcp_app_lifecycle_without_external_assets(self) -> None:
        html = myfund_portfolio_dashboard_widget()

        self.assertIn("ui/initialize", html)
        self.assertIn("ui/notifications/tool-result", html)
        self.assertIn("myfund_app_get_dashboard_data", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    def test_dashboard_payload_catalogs_visualizable_sections(self) -> None:
        with patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_snapshot()):
            payload = _dashboard_payload(DashboardInput(holdings_limit=1, allocation_security_limit=1))

        dashboard = payload["dashboard"]
        self.assertEqual(payload["status"]["code"], "0")
        self.assertEqual(dashboard["holdings"][0]["name"], "Alpha")
        self.assertEqual(dashboard["allocation_by_security"][-1]["label"], "Other")
        chart_ids = {item["id"] for item in dashboard["visualizations"]}
        self.assertIn("portfolio_value_history", chart_ids)
        self.assertIn("return_vs_benchmark", chart_ids)
        self.assertIn("allocation_by_security", chart_ids)


def _sample_snapshot() -> dict[str, object]:
    return {
        "meta": {
            "portfolio": "sample",
            "api_base_url": "https://myfund.pl/API/v1",
            "fetched_at_utc": "2026-05-06T20:00:00+00:00",
            "cache_note": "cache",
            "top_level_keys": [],
        },
        "status": {"code": "0", "ok": True, "text": "OK"},
        "portfolio": {
            "wartosc": 1000,
            "zysk": 100,
            "zmianaDzienna": 1.5,
            "zyskDzienny": 15,
            "zmianaW": 1,
            "zmiana2W": 2,
            "zmianaM": 3,
            "zmiana3M": 4,
            "zmiana6M": 5,
            "zmianaR": 6,
            "zmiana3R": 7,
            "zmiana5R": 8,
            "zmianaMdD": 3,
            "zmianaRdD": 6,
            "benchName": "Benchmark",
        },
        "derived": {
            "latest": {
                "portfolio_value": 1000,
                "invested_capital": 900,
                "profit": 100,
                "daily_change_pct": 1.5,
                "daily_change_pl": 15,
                "mtd_return_pct": 3,
                "ytd_return_pct": 6,
                "benchmark_name": "Benchmark",
                "holdings_count": 2,
            },
            "allocation_by_type": [
                {"label": "Stocks", "value": 1000, "share_pct": 100, "color": "#0f8b6f"}
            ],
            "allocation_by_security": [
                {"label": "Alpha", "share_pct": 70, "color": "#0f8b6f"},
                {"label": "Beta", "share_pct": 30, "color": "#c64e5d"},
            ],
            "holdings_sorted": [
                {
                    "id": "alpha",
                    "nazwa": "Alpha",
                    "tickerClear": "ALP",
                    "wartosc": 700,
                    "udzial": 70,
                    "zysk": 90,
                    "zmiana": 12,
                },
                {
                    "id": "beta",
                    "nazwa": "Beta",
                    "tickerClear": "BET",
                    "wartosc": 300,
                    "udzial": 30,
                    "zysk": 10,
                    "zmiana": 3,
                },
            ],
            "top_gainers": [
                {"id": "alpha", "nazwa": "Alpha", "wartosc": 700, "zysk": 90, "zmiana": 12}
            ],
            "top_losers": [
                {"id": "beta", "nazwa": "Beta", "wartosc": 300, "zysk": 10, "zmiana": 3}
            ],
            "history": {
                "full": {
                    "dates": ["2026-05-01", "2026-05-02"],
                    "value": [950, 1000],
                    "capital": [900, 900],
                    "profit": [50, 100],
                    "return_dates": ["2026-05-01", "2026-05-02"],
                    "portfolio_return": [1.2, 2.4],
                    "benchmark_return": [1, 2],
                    "benchmark_delta": [0.2, 0.4],
                },
                "month_to_date": {
                    "dates": ["2026-05-02"],
                    "value": [1000],
                    "capital": [900],
                    "profit": [100],
                    "return_dates": ["2026-05-02"],
                    "portfolio_return": [2.4],
                    "benchmark_return": [2],
                    "benchmark_delta": [0.4],
                },
            },
            "benchmark_delta": [0.2, 0.4],
        },
    }


if __name__ == "__main__":
    unittest.main()
