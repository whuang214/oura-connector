"""Fetch one day from the local HTTP server using the saved local API token."""

import argparse
import json
import sys
from pathlib import Path

import httpx

from oura_connector.config import load_settings
from oura_connector.errors import ConnectorError
from oura_connector.models import iso_date
from oura_connector.resources import SECTIONS


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("date", help="Oura date in YYYY-MM-DD format")
    parser.add_argument("--config", type=Path, help="Use the same TOML profile as the server")
    parser.add_argument("--include", action="append", choices=tuple(SECTIONS), help="Repeat for multiple sections")
    parser.add_argument("--format", choices=("compact", "source"), default="compact")
    args = parser.parse_args()
    try:
        day = iso_date(args.date).isoformat()
        settings = load_settings(args.config)
        if not settings.http_token:
            print("No local HTTP token saved. Complete setup first.", file=sys.stderr)
            return 1
        host = f"[{settings.http_host}]" if settings.http_host == "::1" else settings.http_host
        params = [("format", args.format), *(("include", section) for section in args.include or [])]
        with httpx.Client(trust_env=False, follow_redirects=False, timeout=600) as client:
            response = client.get(
                f"http://{host}:{settings.http_port}/days/{day}",
                params=params,
                headers={"Authorization": f"Bearer {settings.http_token}"},
            )
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPStatusError as exc:
        print(f"Local API returned HTTP {exc.response.status_code}; check the HTTP guide.", file=sys.stderr)
        return 1
    except (ConnectorError, ValueError, OSError, httpx.RequestError):
        print("Request failed. Check the date, profile, and running local server.", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
