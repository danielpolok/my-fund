from __future__ import annotations

import os
from collections import deque
from enum import Enum
from importlib import resources
from threading import Lock
from time import monotonic
from typing import Any

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, ConfigDict, Field

from .api import (
    MyFundError,
    RuntimeConfig,
    fetch_portfolio_payload,
    inspect_payload,
    normalize_payload,
    require_success,
    resolve_config,
)


RESOURCE_MIME_TYPE = "text/html;profile=mcp-app"
DASHBOARD_RESOURCE_URI = "ui://my-fund-app/portfolio-dashboard.html"
RATE_LIMIT_WINDOW_SECONDS = 60.0
DEFAULT_MAX_REQUESTS_PER_MINUTE = 30
MAX_REQUEST_TIMESTAMPS: deque[float] = deque()
RATE_LIMIT_LOCK = Lock()

READ_ONLY_OPEN_WORLD_ANNOTATIONS = {
    "readOnlyHint": True,
    "destructiveHint": False,
    "idempotentHint": True,
    "openWorldHint": True,
}

SERVER_INSTRUCTIONS = (
    "Read-only myFund.pl portfolio analysis and dashboard app. Check returned status fields "
    "before analysis, treat upstream API failures as tool execution errors, avoid exposing "
    "credentials, and do not execute trades, rebalance, or mutate account data."
)

mcp = FastMCP(
    "my-fund-app-mcp",
    instructions=SERVER_INSTRUCTIONS,
    website_url="https://github.com/danielpolok/my-fund",
    json_response=True,
    stateless_http=True,
)


class PortfolioInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    portfolio: str | None = Field(
        default=None,
        description="Optional myFund portfolio selector. Defaults to MYFUND_PORTFEL or MYFUND_PORTFOLIO.",
        min_length=1,
    )
    timeout: float = Field(
        default=20.0,
        description="HTTP timeout in seconds for the myFund API request.",
        ge=1.0,
        le=120.0,
    )


class FetchPortfolioInput(PortfolioInput):
    raw: bool = Field(
        default=False,
        description="Return the original myFund API payload instead of normalized portfolio data.",
    )


class HoldingSort(str, Enum):
    VALUE = "value"
    WEIGHT = "weight"
    PROFIT = "profit"
    LOSS = "loss"
    RETURN = "return"
    NAME = "name"


class ListHoldingsInput(PortfolioInput):
    sort_by: HoldingSort = Field(
        default=HoldingSort.VALUE,
        description="Sort order for holdings.",
    )
    limit: int = Field(
        default=20,
        description="Maximum holdings to return.",
        ge=1,
        le=200,
    )


class AllocationScope(str, Enum):
    BOTH = "both"
    TYPE = "type"
    SECURITY = "security"


class AllocationInput(PortfolioInput):
    scope: AllocationScope = Field(
        default=AllocationScope.BOTH,
        description="Allocation section to return: both, type, or security.",
    )


class PerformanceWindow(str, Enum):
    FULL = "full"
    MONTH_TO_DATE = "month_to_date"


class PerformanceInput(PortfolioInput):
    window: PerformanceWindow = Field(
        default=PerformanceWindow.FULL,
        description="Time-series window to return.",
    )


class DashboardInput(PortfolioInput):
    window: PerformanceWindow = Field(
        default=PerformanceWindow.FULL,
        description="Performance window to visualize: full or month_to_date.",
    )
    holdings_limit: int = Field(
        default=12,
        description="Maximum number of holdings to include in dashboard tables and bars.",
        ge=1,
        le=50,
    )
    allocation_security_limit: int = Field(
        default=12,
        description="Maximum number of security-allocation slices before grouping the remainder as Other.",
        ge=1,
        le=50,
    )


def _portfolio_snapshot(params: PortfolioInput) -> dict[str, Any]:
    config = resolve_config(params.portfolio)
    payload = _fetch_rate_limited_portfolio_payload(config, timeout=params.timeout)
    require_success(payload)
    return normalize_payload(payload, config)


def _fetch_rate_limited_portfolio_payload(config: RuntimeConfig, *, timeout: float) -> dict[str, Any]:
    _enforce_rate_limit()
    return fetch_portfolio_payload(config, timeout=timeout)


def _enforce_rate_limit() -> None:
    limit = _max_requests_per_minute()
    now = monotonic()
    window_start = now - RATE_LIMIT_WINDOW_SECONDS

    with RATE_LIMIT_LOCK:
        while MAX_REQUEST_TIMESTAMPS and MAX_REQUEST_TIMESTAMPS[0] < window_start:
            MAX_REQUEST_TIMESTAMPS.popleft()
        if len(MAX_REQUEST_TIMESTAMPS) >= limit:
            raise MyFundError(
                "Rate limit exceeded for myFund API calls. Retry later or set "
                "MY_FUND_MCP_MAX_REQUESTS_PER_MINUTE to a controlled higher value."
            )
        MAX_REQUEST_TIMESTAMPS.append(now)


def _max_requests_per_minute() -> int:
    raw_limit = os.environ.get(
        "MY_FUND_MCP_MAX_REQUESTS_PER_MINUTE",
        str(DEFAULT_MAX_REQUESTS_PER_MINUTE),
    )
    try:
        limit = int(raw_limit)
    except ValueError as exc:
        raise MyFundError("MY_FUND_MCP_MAX_REQUESTS_PER_MINUTE must be an integer.") from exc
    if not 1 <= limit <= 600:
        raise MyFundError("MY_FUND_MCP_MAX_REQUESTS_PER_MINUTE must be between 1 and 600.")
    return limit


@mcp.tool(
    name="myfund_fetch_portfolio",
    title="Fetch myFund Portfolio",
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    structured_output=True,
)
def myfund_fetch_portfolio(params: FetchPortfolioInput) -> dict[str, Any]:
    """Fetch live myFund portfolio data as normalized JSON or the raw API payload."""
    config = resolve_config(params.portfolio)
    payload = _fetch_rate_limited_portfolio_payload(config, timeout=params.timeout)
    if params.raw:
        return payload
    require_success(payload)
    return normalize_payload(payload, config)


@mcp.tool(
    name="myfund_inspect_portfolio",
    title="Inspect myFund Portfolio Response",
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    structured_output=True,
)
def myfund_inspect_portfolio(params: PortfolioInput) -> dict[str, Any]:
    """Inspect live myFund response shape, section presence, counts, and type samples."""
    config = resolve_config(params.portfolio)
    payload = _fetch_rate_limited_portfolio_payload(config, timeout=params.timeout)
    return inspect_payload(payload, config)


@mcp.tool(
    name="myfund_get_portfolio_summary",
    title="Get myFund Portfolio Summary",
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    structured_output=True,
)
def myfund_get_portfolio_summary(params: PortfolioInput) -> dict[str, Any]:
    """Return API status, metadata, portfolio summary fields, and latest derived metrics."""
    snapshot = _portfolio_snapshot(params)
    return {
        "meta": snapshot["meta"],
        "status": snapshot["status"],
        "portfolio": snapshot["portfolio"],
        "latest": snapshot["derived"]["latest"],
        "raw_presence": snapshot["raw_presence"],
    }


@mcp.tool(
    name="myfund_list_holdings",
    title="List myFund Holdings",
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    structured_output=True,
)
def myfund_list_holdings(params: ListHoldingsInput) -> dict[str, Any]:
    """List holdings sorted by value, weight, profit, loss, return, or name."""
    snapshot = _portfolio_snapshot(params)

    holdings = list(snapshot["holdings"])
    if params.sort_by == HoldingSort.VALUE:
        holdings.sort(key=lambda item: _number(item.get("wartosc")), reverse=True)
    elif params.sort_by == HoldingSort.WEIGHT:
        holdings.sort(key=lambda item: _number(item.get("udzial")), reverse=True)
    elif params.sort_by == HoldingSort.PROFIT:
        holdings.sort(key=lambda item: _number(item.get("zysk")), reverse=True)
    elif params.sort_by == HoldingSort.LOSS:
        holdings.sort(key=lambda item: _number(item.get("zysk")))
    elif params.sort_by == HoldingSort.RETURN:
        holdings.sort(key=lambda item: _number(item.get("zmiana")), reverse=True)
    elif params.sort_by == HoldingSort.NAME:
        holdings.sort(key=lambda item: str(item.get("nazwa") or item.get("tickerClear") or ""))

    return {
        "meta": snapshot["meta"],
        "status": snapshot["status"],
        "sort_by": params.sort_by.value,
        "count": min(len(holdings), params.limit),
        "total_holdings": len(holdings),
        "holdings": holdings[: params.limit],
    }


@mcp.tool(
    name="myfund_get_allocations",
    title="Get myFund Allocations",
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    structured_output=True,
)
def myfund_get_allocations(params: AllocationInput) -> dict[str, Any]:
    """Return portfolio allocation by asset type, security, or both."""
    snapshot = _portfolio_snapshot(params)

    derived = snapshot["derived"]
    response: dict[str, Any] = {
        "meta": snapshot["meta"],
        "status": snapshot["status"],
    }
    if params.scope in {AllocationScope.BOTH, AllocationScope.TYPE}:
        response["allocation_by_type"] = derived["allocation_by_type"]
    if params.scope in {AllocationScope.BOTH, AllocationScope.SECURITY}:
        response["allocation_by_security"] = derived["allocation_by_security"]
    return response


@mcp.tool(
    name="myfund_get_performance",
    title="Get myFund Performance",
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    structured_output=True,
)
def myfund_get_performance(params: PerformanceInput) -> dict[str, Any]:
    """Return latest performance metrics, benchmark name, and time-series performance data."""
    snapshot = _portfolio_snapshot(params)
    portfolio = snapshot["portfolio"] or {}
    history = snapshot["derived"]["history"][params.window.value]
    return {
        "meta": snapshot["meta"],
        "status": snapshot["status"],
        "period_returns": _period_returns(portfolio),
        "benchmark_name": portfolio.get("benchName"),
        "window": params.window.value,
        "history": history,
    }


@mcp.resource(
    DASHBOARD_RESOURCE_URI,
    name="myfund_portfolio_dashboard_widget",
    title="myFund Portfolio Dashboard Widget",
    description="Interactive MCP App dashboard for read-only myFund portfolio visualization.",
    mime_type=RESOURCE_MIME_TYPE,
    meta={
        "ui": {
            "prefersBorder": False,
            "csp": {
                "connectDomains": [],
                "resourceDomains": [],
                "baseUriDomains": [],
            },
        }
    },
)
def myfund_portfolio_dashboard_widget() -> str:
    """Return the self-contained HTML dashboard widget."""
    return (
        resources.files("my_fund_app_mcp.widgets")
        .joinpath("portfolio_dashboard.html")
        .read_text(encoding="utf-8")
    )


@mcp.tool(
    name="myfund_show_portfolio_dashboard",
    title="Show myFund Portfolio Dashboard",
    description=(
        "Open an interactive read-only dashboard for myFund portfolio value, capital, profit, "
        "returns versus benchmark, allocation, holdings, and top movers."
    ),
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    meta={"ui": {"resourceUri": DASHBOARD_RESOURCE_URI}},
    structured_output=True,
)
def myfund_show_portfolio_dashboard(params: DashboardInput) -> dict[str, Any]:
    """Return dashboard data and attach the interactive MCP App UI resource."""
    return _dashboard_payload(params)


@mcp.tool(
    name="myfund_app_get_dashboard_data",
    title="Refresh myFund Portfolio Dashboard Data",
    description="Refresh the dashboard data from the myFund API for the interactive app.",
    annotations=READ_ONLY_OPEN_WORLD_ANNOTATIONS,
    meta={"ui": {"visibility": ["app"]}},
    structured_output=True,
)
def myfund_app_get_dashboard_data(params: DashboardInput) -> dict[str, Any]:
    """Return dashboard data for app-side refreshes."""
    return _dashboard_payload(params)


def _dashboard_payload(params: DashboardInput) -> dict[str, Any]:
    snapshot = _portfolio_snapshot(params)
    portfolio = snapshot["portfolio"] or {}
    derived = snapshot["derived"]
    history = derived["history"][params.window.value]
    holdings = [
        _holding_view(holding)
        for holding in (derived["holdings_sorted"] or [])[: params.holdings_limit]
    ]

    payload = {
        "meta": snapshot["meta"],
        "status": snapshot["status"],
        "inputs": {
            "window": params.window.value,
            "holdings_limit": params.holdings_limit,
            "allocation_security_limit": params.allocation_security_limit,
        },
        "summary_text": _summary_text(portfolio, derived),
        "dashboard": {
            "latest": derived["latest"],
            "period_returns": _period_returns(portfolio),
            "benchmark_name": portfolio.get("benchName"),
            "history": history,
            "allocation_by_type": _collapse_allocation(
                derived["allocation_by_type"],
                params.allocation_security_limit,
                value_key="value",
            ),
            "allocation_by_security": _collapse_allocation(
                derived["allocation_by_security"],
                params.allocation_security_limit,
                value_key="share_pct",
            ),
            "holdings": holdings,
            "top_gainers": [_holding_view(item) for item in derived["top_gainers"]],
            "top_losers": [_holding_view(item) for item in derived["top_losers"]],
            "visualizations": _visualization_catalog(),
        },
        "analysis_boundary": {
            "read_only": True,
            "no_trade_execution": True,
            "note": "This MCP app visualizes myFund data only; it does not trade, rebalance, or mutate account data.",
        },
    }
    return payload


def _summary_text(portfolio: dict[str, Any], derived: dict[str, Any]) -> str:
    latest = derived["latest"]
    value = latest.get("portfolio_value")
    profit = latest.get("profit")
    daily = latest.get("daily_change_pct")
    holdings_count = latest.get("holdings_count")
    benchmark = portfolio.get("benchName") or "no benchmark"
    return (
        "Read-only dashboard data for myFund portfolio: "
        f"value={value!r}, profit={profit!r}, daily_change_pct={daily!r}, "
        f"holdings_count={holdings_count!r}, benchmark={benchmark!r}."
    )


def _period_returns(portfolio: dict[str, Any]) -> dict[str, Any]:
    return {
        "1w_pct": portfolio.get("zmianaW"),
        "2w_pct": portfolio.get("zmiana2W"),
        "1m_pct": portfolio.get("zmianaM"),
        "3m_pct": portfolio.get("zmiana3M"),
        "6m_pct": portfolio.get("zmiana6M"),
        "1y_pct": portfolio.get("zmianaR"),
        "3y_pct": portfolio.get("zmiana3R"),
        "5y_pct": portfolio.get("zmiana5R"),
        "mtd_pct": portfolio.get("zmianaMdD"),
        "ytd_pct": portfolio.get("zmianaRdD"),
    }


def _holding_view(holding: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": holding.get("id"),
        "name": holding.get("nazwa") or holding.get("tickerClear") or holding.get("id"),
        "ticker": holding.get("tickerClear"),
        "value": holding.get("wartosc"),
        "weight_pct": holding.get("udzial"),
        "profit": holding.get("zysk"),
        "return_pct": holding.get("zmiana"),
        "daily_change_pct": holding.get("zmianaDzienna"),
        "units": holding.get("liczbaJednostek"),
        "purchase_price": holding.get("cenaZakupu"),
        "current_price": holding.get("close"),
        "investment_days": holding.get("okresInwestycji"),
    }


def _collapse_allocation(
    items: list[dict[str, Any]],
    limit: int,
    *,
    value_key: str,
) -> list[dict[str, Any]]:
    if len(items) <= limit:
        return items

    visible = list(items[:limit])
    remainder = items[limit:]
    remainder_value = sum(
        item.get(value_key)
        for item in remainder
        if isinstance(item.get(value_key), (int, float))
    )
    if not remainder_value:
        return visible

    other: dict[str, Any] = {
        "label": "Other",
        value_key: round(remainder_value, 2),
        "color": "#7c8797",
    }
    if value_key == "value":
        other["share_pct"] = round(
            sum(
                item.get("share_pct")
                for item in remainder
                if isinstance(item.get("share_pct"), (int, float))
            ),
            2,
        )
    return [*visible, other]


def _visualization_catalog() -> list[dict[str, Any]]:
    return [
        {
            "id": "portfolio_value_history",
            "title": "Portfolio value, capital, and profit over time",
            "chart_type": "multi_line",
            "fields": ["history.dates", "history.value", "history.capital", "history.profit"],
        },
        {
            "id": "return_vs_benchmark",
            "title": "Portfolio return versus configured benchmark",
            "chart_type": "multi_line",
            "fields": [
                "history.return_dates",
                "history.portfolio_return",
                "history.benchmark_return",
            ],
        },
        {
            "id": "benchmark_delta",
            "title": "Return spread versus benchmark",
            "chart_type": "diverging_bar",
            "fields": ["history.return_dates", "history.benchmark_delta"],
        },
        {
            "id": "allocation_by_type",
            "title": "Allocation by asset type",
            "chart_type": "bar_or_donut",
            "fields": ["allocation_by_type.label", "allocation_by_type.share_pct"],
        },
        {
            "id": "allocation_by_security",
            "title": "Allocation by security",
            "chart_type": "bar_or_donut",
            "fields": ["allocation_by_security.label", "allocation_by_security.share_pct"],
        },
        {
            "id": "holdings_exposure",
            "title": "Largest holdings by value and portfolio weight",
            "chart_type": "table_and_bar",
            "fields": ["holdings.name", "holdings.value", "holdings.weight_pct"],
        },
        {
            "id": "top_movers",
            "title": "Top gainers and losers by profit",
            "chart_type": "ranked_bar",
            "fields": ["top_gainers.profit", "top_losers.profit"],
        },
    ]


@mcp.prompt(name="myfund_portfolio_analysis")
def myfund_portfolio_analysis(question: str) -> str:
    """Create an analysis prompt grounded in the read-only myFund MCP app tools."""
    return (
        "Answer the user's myFund portfolio question using the myFund MCP app tools. "
        "Check status.code before analysis; status.code='0' means success and '7' means portfolio not found. "
        "Use direct API facts first, distinguish computed interpretation, and mention the documented 5-minute cache "
        "when freshness matters. Use the dashboard widget when the user asks for a visual portfolio view. "
        "Do not invent transaction history, trade actions, or account mutations.\n\n"
        f"Question: {question}"
    )


def _number(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return 0.0


def main() -> None:
    transport = os.environ.get("MY_FUND_MCP_TRANSPORT", "stdio").strip() or "stdio"
    if transport not in {"stdio", "streamable-http", "sse"}:
        raise SystemExit(
            "Unsupported MY_FUND_MCP_TRANSPORT. Use one of: stdio, streamable-http, sse."
        )
    mcp.run(transport=transport)


if __name__ == "__main__":
    main()
