from __future__ import annotations

import unittest

from my_fund_mcp.api import (
    MyFundError,
    RuntimeConfig,
    _redact_secret,
    normalize_payload,
    require_success,
    validate_api_base_url,
)


class ApiNormalizationTests(unittest.TestCase):
    def test_normalize_payload_coerces_numbers_and_builds_derived_views(self) -> None:
        payload = {
            "status": {"code": "0", "text": "OK"},
            "portfel": {
                "wartosc": "1 000,50",
                "zysk": "25,25",
                "zmianaDzienna": "1,5",
                "zyskDzienny": "15",
                "benchName": "Benchmark",
            },
            "tickers": {
                "abc": {
                    "nazwa": "Alpha",
                    "tickerClear": "ALP",
                    "wartosc": "700,50",
                    "udzial": "70",
                    "zysk": "20",
                    "zmiana": "3,5",
                },
                "def": {
                    "nazwa": "Beta",
                    "tickerClear": "BET",
                    "wartosc": "300",
                    "udzial": "30",
                    "zysk": "-5",
                    "zmiana": "-1",
                },
            },
            "struktura": {"Stocks": "1000,50"},
            "strukturaKolor": {"Stocks": "#123456"},
            "strukturaWalory": {"Alpha": "70", "Beta": "30"},
            "strukturaWaloryKolor": {"Alpha": "#111111", "Beta": "#222222"},
            "wartoscWCzasie": {"2026-05-01": "950", "2026-05-02": "1000,50"},
            "wkladWCzasie": {"2026-05-01": "900", "2026-05-02": "900"},
            "zyskWCzasie": {"2026-05-01": "50", "2026-05-02": "100,50"},
            "stopaZwrotuWCzasie": {"2026-05-01": "1,2", "2026-05-02": "2,4"},
            "benchWCzasie": {"2026-05-01": "1", "2026-05-02": "2"},
        }
        config = RuntimeConfig(
            api_key="secret",
            portfolio="main",
            api_base_url="https://myfund.pl/API/v1",
        )

        normalized = normalize_payload(payload, config)

        self.assertTrue(normalized["status"]["ok"])
        self.assertEqual(normalized["portfolio"]["wartosc"], 1000.50)
        self.assertEqual(normalized["holdings"][0]["wartosc"], 700.50)
        self.assertEqual(normalized["derived"]["latest"]["portfolio_value"], 1000.50)
        self.assertEqual(normalized["derived"]["allocation_by_type"][0]["share_pct"], 100.0)
        self.assertEqual(normalized["derived"]["history"]["full"]["benchmark_delta"], [0.2, 0.4])

    def test_require_success_raises_actionable_portfolio_not_found_error(self) -> None:
        with self.assertRaisesRegex(MyFundError, "Portfolio was not found"):
            require_success({"status": {"code": "7", "text": "not found"}})


class ApiSecurityTests(unittest.TestCase):
    def test_api_base_url_must_be_https_myfund_by_default(self) -> None:
        self.assertEqual(
            validate_api_base_url("https://myfund.pl/API/v1/"),
            "https://myfund.pl/API/v1",
        )
        with self.assertRaisesRegex(MyFundError, "https"):
            validate_api_base_url("http://myfund.pl/API/v1")
        with self.assertRaisesRegex(MyFundError, "myfund.pl"):
            validate_api_base_url("https://example.com/API/v1")

    def test_custom_api_base_url_requires_explicit_opt_in(self) -> None:
        self.assertEqual(
            validate_api_base_url(
                "https://example.com/myfund",
                allow_custom=True,
            ),
            "https://example.com/myfund",
        )

    def test_redacts_api_key_from_error_text(self) -> None:
        self.assertEqual(
            _redact_secret("upstream echoed abc123 in error", "abc123"),
            "upstream echoed <redacted> in error",
        )


if __name__ == "__main__":
    unittest.main()
