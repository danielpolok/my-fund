from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

from . import __version__


DEFAULT_API_BASE_URL = "https://myfund.pl/API/v1"
MYFUND_HOST_SUFFIX = ".myfund.pl"
SUMMARY_NUMERIC_FIELDS = {
    "close",
    "zmianaDzienna",
    "liczbaJednostek",
    "wartosc",
    "udzial",
    "zmiana",
    "zysk",
    "zyskDzienny",
    "zmianaW",
    "zmiana2W",
    "zmianaM",
    "zmiana3M",
    "zmiana6M",
    "zmianaR",
    "zmiana3R",
    "zmiana5R",
    "zmianaMdD",
    "zmianaRdD",
}
TICKER_NUMERIC_FIELDS = {
    "close",
    "zmianaDzienna",
    "liczbaJednostek",
    "wartosc",
    "udzial",
    "zmiana",
    "cenaZakupu",
    "zysk",
    "okresInwestycji",
}
TIMESERIES_FIELDS = {
    "zyskWCzasie",
    "wartoscWCzasie",
    "wkladWCzasie",
    "benchWCzasie",
    "stopaZwrotuWCzasie",
    "zmianaDzienna",
}
EXPECTED_TOP_LEVEL_FIELDS = {
    "status",
    "portfel",
    "tickers",
    "struktura",
    "strukturaKolor",
    "strukturaWalory",
    "strukturaWaloryKolor",
    "zyskWCzasie",
    "wartoscWCzasie",
    "wkladWCzasie",
    "benchWCzasie",
    "stopaZwrotuWCzasie",
    "zmianaDzienna",
}


class MyFundError(Exception):
    """Raised for configuration and myFund API failures."""


@dataclass
class RuntimeConfig:
    api_key: str
    portfolio: str | None
    api_base_url: str


@dataclass
class RuntimeEnv:
    values: dict[str, str]
    dotenv_paths: list[Path]
    found_dotenv_paths: list[Path]


def project_root() -> Path:
    return Path(__file__).resolve().parents[5]


def load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if value and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def load_runtime_env() -> RuntimeEnv:
    root = project_root()
    dotenv_paths = [
        root / "mcp-servers" / "src" / "my-fund" / ".env",
        root / "skills" / "my-fund" / ".env",
    ]
    values: dict[str, str] = {}
    found_dotenv_paths: list[Path] = []
    for path in dotenv_paths:
        if path.exists():
            found_dotenv_paths.append(path)
        values.update(load_dotenv(path))
    values.update({key: value for key, value in os.environ.items() if value})
    return RuntimeEnv(
        values=values,
        dotenv_paths=dotenv_paths,
        found_dotenv_paths=found_dotenv_paths,
    )


def config_source_hint(runtime_env: RuntimeEnv) -> str:
    checked = ", ".join(str(path) for path in runtime_env.dotenv_paths)
    if runtime_env.found_dotenv_paths:
        found = ", ".join(str(path) for path in runtime_env.found_dotenv_paths)
        return (
            f"Checked dotenv files: {checked}. Found dotenv file(s): {found}, "
            "but the required value is missing. Export the value or add it to one of those files."
        )
    return (
        f"No dotenv file was found. Checked: {checked}. Export the value or create one of those files."
    )


def resolve_config(portfolio_override: str | None = None) -> RuntimeConfig:
    runtime_env = load_runtime_env()
    env = runtime_env.values
    api_key = env.get("MYFUND_API_KEY")
    if not api_key:
        raise MyFundError(f"Missing MYFUND_API_KEY. {config_source_hint(runtime_env)}")

    portfolio = portfolio_override or env.get("MYFUND_PORTFEL") or env.get("MYFUND_PORTFOLIO")
    if not portfolio:
        raise MyFundError(
            "Missing portfolio. Pass a portfolio argument, export MYFUND_PORTFEL, or define "
            f"MYFUND_PORTFEL in a dotenv file. {config_source_hint(runtime_env)}"
        )
    api_base_url = validate_api_base_url(
        env.get("MYFUND_API_BASE_URL", DEFAULT_API_BASE_URL),
        allow_custom=_truthy(env.get("MYFUND_ALLOW_CUSTOM_API_BASE_URL")),
    )
    return RuntimeConfig(api_key=api_key, portfolio=portfolio, api_base_url=api_base_url)


def validate_api_base_url(api_base_url: str, *, allow_custom: bool = False) -> str:
    base_url = api_base_url.strip().rstrip("/")
    parsed = urlparse(base_url)
    if parsed.scheme != "https":
        raise MyFundError("MYFUND_API_BASE_URL must use https://.")
    if not parsed.netloc or not parsed.hostname:
        raise MyFundError("MYFUND_API_BASE_URL must include a hostname.")
    if parsed.params or parsed.query or parsed.fragment:
        raise MyFundError("MYFUND_API_BASE_URL must not include params, query strings, or fragments.")

    hostname = parsed.hostname.lower()
    is_myfund_host = hostname == "myfund.pl" or hostname.endswith(MYFUND_HOST_SUFFIX)
    if not is_myfund_host and not allow_custom:
        raise MyFundError(
            "MYFUND_API_BASE_URL must point to myfund.pl. Set "
            "MYFUND_ALLOW_CUSTOM_API_BASE_URL=true only for a controlled test or staging endpoint."
        )
    return base_url


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def build_request_url(api_base_url: str, portfolio: str, api_key: str) -> str:
    query = urlencode(
        {
            "portfel": portfolio,
            "apiKey": api_key,
            "format": "json",
        }
    )
    return f"{api_base_url}/getPortfel.php?{query}"


def fetch_portfolio_payload(config: RuntimeConfig, timeout: float = 20.0) -> dict[str, Any]:
    if not config.portfolio:
        raise MyFundError("Missing portfolio selector.")
    request = Request(
        build_request_url(config.api_base_url, config.portfolio, config.api_key),
        headers={"Accept": "application/json", "User-Agent": f"my-fund-mcp/{__version__}"},
        method="GET",
    )

    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8")
    except HTTPError as exc:
        message = _redact_secret(exc.read().decode("utf-8", errors="replace"), config.api_key)
        raise MyFundError(f"HTTP {exc.code} from myFund API: {message}") from exc
    except URLError as exc:
        raise MyFundError(f"Could not reach myFund API: {exc.reason}") from exc

    try:
        data = json.loads(body)
    except json.JSONDecodeError as exc:
        raise MyFundError(f"myFund API returned invalid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise MyFundError("myFund API returned a non-object JSON payload.")
    return data


def _redact_secret(message: str, secret: str) -> str:
    if not secret:
        return message
    return message.replace(secret, "<redacted>")


def status_code(payload: dict[str, Any]) -> str:
    status = payload.get("status")
    if not isinstance(status, dict):
        return ""
    return str(status.get("code", ""))


def require_success(payload: dict[str, Any]) -> None:
    code = status_code(payload)
    if code == "0":
        return
    status = payload.get("status") if isinstance(payload.get("status"), dict) else {}
    text = status.get("text") if isinstance(status, dict) else None
    if code == "7":
        raise MyFundError(f"Portfolio was not found by the myFund API. status.code=7, status.text={text!r}")
    raise MyFundError(f"myFund API returned failure status.code={code!r}, status.text={text!r}")


def _coerce_number(value: Any) -> Any:
    if isinstance(value, (int, float)) or value is None:
        return value
    if not isinstance(value, str):
        return value

    stripped = value.strip()
    if not stripped or stripped in {"---", "&nbsp;"} or stripped.startswith("#"):
        return value

    compact = stripped.replace("\xa0", "").replace(" ", "")
    if not re.fullmatch(r"[+-]?\d+(?:[.,]\d+)?", compact):
        return value

    normalized = compact.replace(",", ".")
    if "." in normalized:
        return float(normalized)
    return int(normalized)


def _normalize_named_numeric_fields(source: dict[str, Any], numeric_fields: set[str]) -> dict[str, Any]:
    return {
        key: _coerce_number(value) if key in numeric_fields else value
        for key, value in source.items()
    }


def normalize_payload(payload: dict[str, Any], config: RuntimeConfig) -> dict[str, Any]:
    summary = payload.get("portfel")
    tickers = payload.get("tickers") or {}
    by_type = payload.get("struktura") or {}
    by_security = payload.get("strukturaWalory") or {}

    normalized_tickers: list[dict[str, Any]] = []
    if isinstance(tickers, dict):
        for ticker_id, ticker_data in tickers.items():
            if isinstance(ticker_data, dict):
                item = _normalize_named_numeric_fields(ticker_data, TICKER_NUMERIC_FIELDS)
                item["id"] = ticker_id
                normalized_tickers.append(item)

    normalized_payload: dict[str, Any] = {
        "meta": {
            "portfolio": config.portfolio,
            "api_base_url": config.api_base_url,
            "fetched_at_utc": datetime.now(timezone.utc).isoformat(),
            "cache_note": "myFund documents a 5-minute cache window for identical requests.",
            "top_level_keys": sorted(payload.keys()),
        },
        "status": {
            "code": status_code(payload),
            "ok": status_code(payload) == "0",
            "text": (payload.get("status") or {}).get("text") if isinstance(payload.get("status"), dict) else None,
        },
        "portfolio": _normalize_named_numeric_fields(summary, SUMMARY_NUMERIC_FIELDS)
        if isinstance(summary, dict)
        else None,
        "holdings": normalized_tickers,
        "allocations": {
            "by_type": {
                key: _coerce_number(value)
                for key, value in by_type.items()
            }
            if isinstance(by_type, dict)
            else {},
            "by_type_colors": payload.get("strukturaKolor") or {},
            "by_security": {
                key: _coerce_number(value)
                for key, value in by_security.items()
            }
            if isinstance(by_security, dict)
            else {},
            "by_security_colors": payload.get("strukturaWaloryKolor") or {},
        },
        "timeseries": {
            field: {
                key: _coerce_number(value)
                for key, value in (payload.get(field) or {}).items()
            }
            for field in TIMESERIES_FIELDS
            if isinstance(payload.get(field), dict)
        },
        "raw_presence": {
            "present": sorted(set(payload.keys()) & EXPECTED_TOP_LEVEL_FIELDS),
            "missing": sorted(EXPECTED_TOP_LEVEL_FIELDS - set(payload.keys())),
        },
    }
    normalized_payload["derived"] = build_derived_payload(normalized_payload)
    return normalized_payload


def build_derived_payload(normalized_payload: dict[str, Any]) -> dict[str, Any]:
    portfolio = normalized_payload.get("portfolio") or {}
    holdings = normalized_payload.get("holdings") or []
    allocations = normalized_payload.get("allocations") or {}
    timeseries = normalized_payload.get("timeseries") or {}
    total_value = portfolio.get("wartosc") if isinstance(portfolio.get("wartosc"), (int, float)) else 0.0

    holdings_sorted = sorted(
        [holding for holding in holdings if isinstance(holding, dict)],
        key=lambda item: item.get("wartosc") if isinstance(item.get("wartosc"), (int, float)) else 0.0,
        reverse=True,
    )

    def share_of_total(value: Any) -> float:
        if not isinstance(value, (int, float)) or not total_value:
            return 0.0
        return round(value / total_value * 100, 2)

    allocation_by_type = [
        {
            "label": label,
            "value": value,
            "color": (allocations.get("by_type_colors") or {}).get(label, "#4f7cff"),
            "share_pct": share_of_total(value),
        }
        for label, value in (allocations.get("by_type") or {}).items()
    ]
    allocation_by_type.sort(
        key=lambda item: item["value"] if isinstance(item["value"], (int, float)) else 0.0,
        reverse=True,
    )

    allocation_by_security = [
        {
            "label": label,
            "share_pct": share_pct,
            "color": (allocations.get("by_security_colors") or {}).get(label, "#4f7cff"),
        }
        for label, share_pct in (allocations.get("by_security") or {}).items()
    ]
    allocation_by_security.sort(
        key=lambda item: item["share_pct"] if isinstance(item["share_pct"], (int, float)) else 0.0,
        reverse=True,
    )

    top_gainers = sorted(
        holdings_sorted,
        key=lambda item: item.get("zysk") if isinstance(item.get("zysk"), (int, float)) else float("-inf"),
        reverse=True,
    )[:5]
    top_losers = sorted(
        holdings_sorted,
        key=lambda item: item.get("zysk") if isinstance(item.get("zysk"), (int, float)) else float("inf"),
    )[:5]
    history_full = _build_history_slice(timeseries)
    history_month = _build_month_to_date_slice(timeseries)

    return {
        "latest": {
            "portfolio_value": portfolio.get("wartosc"),
            "invested_capital": _last_numeric_value(timeseries.get("wkladWCzasie") or {}),
            "profit": portfolio.get("zysk"),
            "daily_change_pct": portfolio.get("zmianaDzienna"),
            "daily_change_pl": portfolio.get("zyskDzienny"),
            "mtd_return_pct": portfolio.get("zmianaMdD"),
            "ytd_return_pct": portfolio.get("zmianaRdD"),
            "benchmark_name": portfolio.get("benchName"),
            "holdings_count": portfolio.get("tickersCount", len(holdings_sorted)),
        },
        "allocation_by_type": allocation_by_type,
        "allocation_by_security": allocation_by_security,
        "holdings_sorted": holdings_sorted,
        "top_gainers": top_gainers,
        "top_losers": top_losers,
        "history": {
            "full": history_full,
            "month_to_date": history_month,
        },
        "benchmark_delta": history_full.get("benchmark_delta", []),
    }


def _last_numeric_value(series: dict[str, Any]) -> Any:
    if not isinstance(series, dict) or not series:
        return None
    return series[sorted(series.keys())[-1]]


def _build_history_slice(timeseries: dict[str, Any]) -> dict[str, Any]:
    value_series = timeseries.get("wartoscWCzasie") or {}
    capital_series = timeseries.get("wkladWCzasie") or {}
    profit_series = timeseries.get("zyskWCzasie") or {}
    portfolio_return_series = timeseries.get("stopaZwrotuWCzasie") or {}
    benchmark_series = timeseries.get("benchWCzasie") or {}

    dates = sorted(value_series.keys())
    return_dates = sorted(set(portfolio_return_series.keys()) | set(benchmark_series.keys()))
    benchmark_delta = []
    for day in return_dates:
        portfolio_value = portfolio_return_series.get(day)
        benchmark_value = benchmark_series.get(day)
        if isinstance(portfolio_value, (int, float)) and isinstance(benchmark_value, (int, float)):
            benchmark_delta.append(round(portfolio_value - benchmark_value, 2))
        else:
            benchmark_delta.append(None)

    return {
        "dates": dates,
        "value": [value_series.get(day) for day in dates],
        "capital": [capital_series.get(day) for day in dates],
        "profit": [profit_series.get(day) for day in dates],
        "return_dates": return_dates,
        "portfolio_return": [portfolio_return_series.get(day) for day in return_dates],
        "benchmark_return": [benchmark_series.get(day) for day in return_dates],
        "benchmark_delta": benchmark_delta,
    }


def _build_month_to_date_slice(timeseries: dict[str, Any]) -> dict[str, Any]:
    full = _build_history_slice(timeseries)
    if not full["dates"]:
        return full

    latest_prefix = full["dates"][-1][:7]
    value_dates = [day for day in full["dates"] if day.startswith(latest_prefix)]
    return_dates = [day for day in full["return_dates"] if day.startswith(latest_prefix)]
    value_lookup = dict(zip(full["dates"], full["value"]))
    capital_lookup = dict(zip(full["dates"], full["capital"]))
    profit_lookup = dict(zip(full["dates"], full["profit"]))
    portfolio_return_lookup = dict(zip(full["return_dates"], full["portfolio_return"]))
    benchmark_return_lookup = dict(zip(full["return_dates"], full["benchmark_return"]))
    benchmark_delta_lookup = dict(zip(full["return_dates"], full["benchmark_delta"]))

    return {
        "dates": value_dates,
        "value": [value_lookup.get(day) for day in value_dates],
        "capital": [capital_lookup.get(day) for day in value_dates],
        "profit": [profit_lookup.get(day) for day in value_dates],
        "return_dates": return_dates,
        "portfolio_return": [portfolio_return_lookup.get(day) for day in return_dates],
        "benchmark_return": [benchmark_return_lookup.get(day) for day in return_dates],
        "benchmark_delta": [benchmark_delta_lookup.get(day) for day in return_dates],
    }


def inspect_payload(payload: dict[str, Any], config: RuntimeConfig) -> dict[str, Any]:
    summary = payload.get("portfel") if isinstance(payload.get("portfel"), dict) else {}
    tickers = payload.get("tickers") if isinstance(payload.get("tickers"), dict) else {}
    first_ticker = next(iter(tickers.values()), {})

    return {
        "request": {
            "portfolio": config.portfolio,
            "api_base_url": config.api_base_url,
        },
        "status": payload.get("status"),
        "top_level_keys": sorted(payload.keys()),
        "present_sections": sorted(set(payload.keys()) & EXPECTED_TOP_LEVEL_FIELDS),
        "missing_sections": sorted(EXPECTED_TOP_LEVEL_FIELDS - set(payload.keys())),
        "counts": {
            "holdings": len(tickers),
            "allocation_categories": len(payload.get("struktura") or {})
            if isinstance(payload.get("struktura"), dict)
            else 0,
            "allocation_securities": len(payload.get("strukturaWalory") or {})
            if isinstance(payload.get("strukturaWalory"), dict)
            else 0,
            "timeseries_points": {
                field: len(payload.get(field) or {})
                for field in TIMESERIES_FIELDS
                if isinstance(payload.get(field), dict)
            },
        },
        "type_samples": {
            "portfolio": {key: type(value).__name__ for key, value in list(summary.items())[:10]},
            "first_ticker": {
                key: type(value).__name__
                for key, value in list(first_ticker.items())[:10]
            }
            if isinstance(first_ticker, dict)
            else {},
        },
        "numeric_string_examples": _collect_numeric_string_examples(payload),
    }


def _collect_numeric_string_examples(payload: dict[str, Any]) -> dict[str, str]:
    examples: dict[str, str] = {}
    summary = payload.get("portfel")
    if isinstance(summary, dict):
        for field in sorted(SUMMARY_NUMERIC_FIELDS):
            value = summary.get(field)
            if isinstance(value, str) and value != _coerce_number(value):
                examples[f"portfel.{field}"] = value

    tickers = payload.get("tickers")
    if isinstance(tickers, dict):
        for ticker_id, ticker_data in tickers.items():
            if not isinstance(ticker_data, dict):
                continue
            for field in sorted(TICKER_NUMERIC_FIELDS):
                value = ticker_data.get(field)
                if isinstance(value, str) and value != _coerce_number(value):
                    examples[f"tickers[{ticker_id}].{field}"] = value
            if examples:
                break

    for field in sorted(TIMESERIES_FIELDS):
        series = payload.get(field)
        if not isinstance(series, dict) or not series:
            continue
        first_key = next(iter(series))
        value = series[first_key]
        if isinstance(value, str):
            examples[f"{field}[{first_key}]"] = value
    return examples
