#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys

from myfund_api import MyFundError, dump_json, fetch_portfolio_payload, normalize_payload, resolve_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Fetch portfolio data from the myFund API."
    )
    parser.add_argument(
        "--portfolio",
        help="Portfolio selector to send as the API 'portfel' parameter.",
    )
    parser.add_argument(
        "--raw",
        action="store_true",
        help="Print the raw API payload instead of normalized output.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="HTTP timeout in seconds (default: 20).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    try:
        config = resolve_config(args.portfolio)
        payload = fetch_portfolio_payload(config, timeout=args.timeout)
        output = payload if args.raw else normalize_payload(payload, config)
        dump_json(output)
        return 0
    except MyFundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
