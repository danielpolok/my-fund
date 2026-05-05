#!/usr/bin/env python3

from __future__ import annotations

import argparse
import sys

from myfund_api import MyFundError, dump_json, fetch_portfolio_payload, inspect_payload, resolve_config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Inspect the shape of a live myFund portfolio API response."
    )
    parser.add_argument(
        "--portfolio",
        help="Portfolio selector to send as the API 'portfel' parameter.",
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
        dump_json(inspect_payload(payload, config))
        return 0
    except MyFundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
