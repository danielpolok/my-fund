from __future__ import annotations

import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from my_fund_app_mcp.server import (
    AllocationInput,
    DASHBOARD_RESOURCE_URI,
    DIVIDEND_CALENDAR_RESOURCE_URI,
    DividendCalendarInput,
    DashboardName,
    HoldingSort,
    ListHoldingsInput,
    MyFundError,
    PerformanceInput,
    PortfolioInput,
    RESOURCE_MIME_TYPE,
    DashboardInput,
    _dashboard_payload,
    _dividend_calendar_payload,
    mcp,
    myfund_get_allocations,
    myfund_get_performance,
    myfund_get_portfolio_summary,
    myfund_list_holdings,
    myfund_dividend_calendar_beta_widget,
    myfund_portfolio_dashboard_widget,
)


class AppServerContractTests(unittest.TestCase):
    def test_app_exposes_basic_mcp_tools_plus_widget_tools(self) -> None:
        tools = {tool.name: tool for tool in asyncio.run(mcp.list_tools())}
        expected_tools = {
            "myfund_fetch_portfolio",
            "myfund_inspect_portfolio",
            "myfund_get_portfolio_summary",
            "myfund_list_holdings",
            "myfund_get_allocations",
            "myfund_get_performance",
            "myfund_show_portfolio_dashboard",
            "myfund_app_get_dashboard_data",
            "myfund_show_dividend_calendar",
            "myfund_app_get_dividend_calendar_data",
        }

        self.assertEqual(set(tools), expected_tools)
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
        self.assertEqual(
            tools["myfund_show_dividend_calendar"].title,
            "Show myFund Dividend Calendar Beta",
        )
        self.assertEqual(
            tools["myfund_show_dividend_calendar"].meta["ui"]["resourceUri"],
            DIVIDEND_CALENDAR_RESOURCE_URI,
        )
        self.assertEqual(
            tools["myfund_app_get_dividend_calendar_data"].meta["ui"]["visibility"],
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

    def test_app_exposes_basic_analysis_prompt(self) -> None:
        prompts = {prompt.name: prompt for prompt in asyncio.run(mcp.list_prompts())}

        self.assertIn("myfund_portfolio_analysis", prompts)

    def test_dashboard_resource_is_mcp_app_html(self) -> None:
        resources = {str(resource.uri): resource for resource in asyncio.run(mcp.list_resources())}

        self.assertIn(DASHBOARD_RESOURCE_URI, resources)
        self.assertIn(DIVIDEND_CALENDAR_RESOURCE_URI, resources)
        resource = resources[DASHBOARD_RESOURCE_URI]
        self.assertEqual(resource.mimeType, RESOURCE_MIME_TYPE)
        self.assertFalse(resource.meta["ui"]["prefersBorder"])
        self.assertEqual(resource.meta["ui"]["csp"]["connectDomains"], [])
        dividend_resource = resources[DIVIDEND_CALENDAR_RESOURCE_URI]
        self.assertEqual(dividend_resource.mimeType, RESOURCE_MIME_TYPE)
        self.assertFalse(dividend_resource.meta["ui"]["prefersBorder"])
        self.assertEqual(dividend_resource.meta["ui"]["csp"]["connectDomains"], [])

    def test_widget_html_uses_mcp_app_lifecycle_without_external_assets(self) -> None:
        html = myfund_portfolio_dashboard_widget()

        self.assertIn("ui/initialize", html)
        self.assertIn("ui/notifications/tool-result", html)
        self.assertIn("myfund_app_get_dashboard_data", html)
        self.assertIn('data-dashboard="portfolio"', html)
        self.assertIn('data-dashboard="holdings"', html)
        self.assertIn('data-dashboard="allocation"', html)
        self.assertIn('data-dashboard="performance"', html)
        self.assertIn('data-dashboard="risk"', html)
        self.assertIn('data-dashboard="sectors"', html)
        self.assertIn('data-dashboard="concentration"', html)
        self.assertIn("Visible myFund dashboard: dashboard=", html)
        self.assertIn("dashboard: state.activeDashboard", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    def test_dividend_calendar_widget_html_uses_mcp_app_lifecycle_without_external_assets(self) -> None:
        html = myfund_dividend_calendar_beta_widget()

        self.assertIn("Dividend Calendar", html)
        self.assertIn("Beta", html)
        self.assertIn("ui/initialize", html)
        self.assertIn("ui/notifications/tool-result", html)
        self.assertIn("myfund_app_get_dividend_calendar_data", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    def test_dashboard_payload_catalogs_visualizable_sections(self) -> None:
        with patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_snapshot()):
            payload = _dashboard_payload(DashboardInput(holdings_limit=1, allocation_security_limit=1))

        dashboard = payload["dashboard"]
        self.assertEqual(payload["status"]["code"], "0")
        self.assertEqual(payload["inputs"]["dashboard"], "portfolio")
        self.assertEqual(payload["active_dashboard"], "portfolio")
        self.assertEqual(
            [(item["id"], item["name"]) for item in payload["dashboards"]],
            [
                ("portfolio", "Portfolio"),
                ("holdings", "Holdings"),
                ("allocation", "Allocation"),
                ("performance", "Performance"),
                ("risk", "Risk"),
                ("sectors", "Sectors"),
                ("concentration", "Concentration"),
            ],
        )
        self.assertEqual(dashboard["holdings"][0]["name"], "Alpha")
        self.assertEqual(dashboard["holdings"][0]["risk"], "High")
        self.assertEqual(dashboard["holdings"][0]["sector"], "Technology")
        self.assertEqual(dashboard["allocation_by_security"][-1]["label"], "Other")
        self.assertEqual(dashboard["views"]["holdings"]["holdings"][0]["name"], "Alpha")
        self.assertEqual(dashboard["views"]["performance"]["benchmark_name"], "Benchmark")
        self.assertEqual(dashboard["views"]["risk"]["holdings"][0]["risk"], "High")
        self.assertEqual(dashboard["views"]["sectors"]["holdings"][0]["sector"], "Technology")
        self.assertEqual(dashboard["views"]["concentration"]["holdings"][0]["weight_pct"], 70)
        chart_ids = {item["id"] for item in dashboard["visualizations"]}
        self.assertIn("portfolio_value_history", chart_ids)
        self.assertIn("return_vs_benchmark", chart_ids)
        self.assertIn("allocation_by_security", chart_ids)

    def test_dashboard_input_accepts_named_dashboard_selection(self) -> None:
        params = DashboardInput(dashboard=DashboardName.HOLDINGS)

        self.assertEqual(params.dashboard, DashboardName.HOLDINGS)

        with patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_snapshot()):
            payload = _dashboard_payload(params)

        self.assertEqual(payload["inputs"]["dashboard"], "holdings")
        self.assertEqual(payload["active_dashboard"], "holdings")

        risk_params = DashboardInput(dashboard=DashboardName.RISK)
        with patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_snapshot()):
            risk_payload = _dashboard_payload(risk_params)

        self.assertEqual(risk_payload["inputs"]["dashboard"], "risk")
        self.assertEqual(risk_payload["active_dashboard"], "risk")

    def test_dividend_calendar_payload_joins_events_to_holdings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dividend_file = Path(tmp) / "dividends.json"
            dividend_file.write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "ticker": "AAPL",
                                "name": "Apple Inc.",
                                "instrument_type": "stock",
                                "ex_dividend_date": "2026-05-10",
                                "payment_date": "2026-05-21",
                                "dividend_per_share": 0.26,
                                "currency": "USD",
                                "status": "confirmed",
                                "source": "mock-beta",
                            },
                            {
                                "ticker": "MSFT",
                                "payment_date": "2027-06-11",
                                "dividend_per_share": 0.83,
                                "currency": "USD",
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_dividend_snapshot()),
                patch(
                    "my_fund_app_mcp.server.load_runtime_env",
                    return_value=SimpleNamespace(values={"MYFUND_DIVIDENDS_FILE": str(dividend_file)}),
                ),
            ):
                payload = _dividend_calendar_payload(DividendCalendarInput(year=2026, month=5))

        calendar = payload["calendar"]
        self.assertEqual(payload["meta"]["feature_label"], "Dividend Calendar Beta")
        self.assertTrue(payload["meta"]["dividends_file_found"])
        self.assertEqual(len(calendar["events"]), 1)
        self.assertEqual(calendar["events"][0]["ticker"], "AAPL")
        self.assertEqual(calendar["events"][0]["units"], 10)
        self.assertEqual(calendar["events"][0]["estimated_gross_amount"], 2.6)
        self.assertEqual(calendar["monthly_totals"][4]["totals_by_currency"], {"USD": 2.6})
        missing_tickers = {item["ticker"] for item in calendar["missing_dividend_data"]}
        self.assertIn("MSFT", missing_tickers)

    def test_dividend_calendar_payload_without_file_returns_missing_data(self) -> None:
        with (
            patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_dividend_snapshot()),
            patch(
                "my_fund_app_mcp.server.load_runtime_env",
                return_value=SimpleNamespace(values={}),
            ),
        ):
            payload = _dividend_calendar_payload(DividendCalendarInput(year=2026))

        self.assertFalse(payload["meta"]["dividends_file_configured"])
        self.assertEqual(payload["calendar"]["events"], [])
        self.assertGreaterEqual(len(payload["calendar"]["missing_dividend_data"]), 2)

    def test_dividend_calendar_rejects_invalid_event_data(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            dividend_file = Path(tmp) / "dividends.json"
            dividend_file.write_text(
                json.dumps(
                    {
                        "events": [
                            {
                                "ticker": "AAPL",
                                "payment_date": "2026/05/21",
                                "dividend_per_share": "0.26",
                                "currency": "USD",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            with (
                patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_dividend_snapshot()),
                patch(
                    "my_fund_app_mcp.server.load_runtime_env",
                    return_value=SimpleNamespace(values={"MYFUND_DIVIDENDS_FILE": str(dividend_file)}),
                ),
            ):
                with self.assertRaises(MyFundError):
                    _dividend_calendar_payload(DividendCalendarInput(year=2026))

    def test_basic_summary_tool_matches_myfund_mcp_capability(self) -> None:
        with patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_snapshot()):
            summary = myfund_get_portfolio_summary(PortfolioInput())

        self.assertEqual(summary["status"]["code"], "0")
        self.assertEqual(summary["latest"]["portfolio_value"], 1000)
        self.assertEqual(summary["portfolio"]["benchName"], "Benchmark")

    def test_basic_holdings_tool_sorts_and_limits_like_myfund_mcp(self) -> None:
        with patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_snapshot()):
            holdings = myfund_list_holdings(
                ListHoldingsInput(sort_by=HoldingSort.NAME, limit=1)
            )

        self.assertEqual(holdings["sort_by"], "name")
        self.assertEqual(holdings["count"], 1)
        self.assertEqual(holdings["total_holdings"], 2)
        self.assertEqual(holdings["holdings"][0]["nazwa"], "Alpha")

    def test_basic_allocation_and_performance_tools_match_myfund_mcp_capability(self) -> None:
        with patch("my_fund_app_mcp.server._portfolio_snapshot", return_value=_sample_snapshot()):
            allocations = myfund_get_allocations(AllocationInput())
            performance = myfund_get_performance(PerformanceInput())

        self.assertIn("allocation_by_type", allocations)
        self.assertIn("allocation_by_security", allocations)
        self.assertEqual(performance["benchmark_name"], "Benchmark")
        self.assertEqual(performance["history"]["benchmark_delta"], [0.2, 0.4])


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
        "raw_presence": {
            "present": ["status", "portfel", "tickers"],
            "missing": [],
        },
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
        "holdings": [
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
                    "ryzyko": "High",
                    "sektor": "Technology",
                    "typ": "Stock",
                },
                {
                    "id": "beta",
                    "nazwa": "Beta",
                    "tickerClear": "BET",
                    "wartosc": 300,
                    "udzial": 30,
                    "zysk": 10,
                    "zmiana": 3,
                    "ryzyko": "Medium",
                    "sektor": "Healthcare",
                    "typ": "ETF",
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


def _sample_dividend_snapshot() -> dict[str, object]:
    snapshot = _sample_snapshot()
    snapshot["holdings"] = [
        {
            "id": "apple",
            "nazwa": "Apple Inc.",
            "tickerClear": "AAPL",
            "wartosc": 700,
            "udzial": 70,
            "zysk": 90,
            "zmiana": 12,
            "liczbaJednostek": 10,
        },
        {
            "id": "microsoft",
            "nazwa": "Microsoft Corporation",
            "tickerClear": "MSFT",
            "wartosc": 300,
            "udzial": 30,
            "zysk": 0,
            "zmiana": 0,
            "liczbaJednostek": 5,
            "typ": "stock",
        },
        {
            "id": "cash",
            "nazwa": "Cash Holding",
            "tickerClear": "CASH",
            "wartosc": 25,
            "udzial": 2.5,
            "typ": "cash",
        },
    ]
    snapshot["derived"]["holdings_sorted"] = list(snapshot["holdings"])
    return snapshot


if __name__ == "__main__":
    unittest.main()
