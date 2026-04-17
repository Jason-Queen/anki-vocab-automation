#!/usr/bin/env python3
"""Send a single version-6 request to AnkiConnect."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict


def _load_params(args: argparse.Namespace) -> Dict[str, Any]:
    sources = [
        bool(args.params_json),
        bool(args.params_file),
        bool(args.params_stdin),
    ]
    if sum(sources) > 1:
        raise ValueError("Choose only one of --params-json, --params-file, or --params-stdin.")

    if args.params_json:
        data = json.loads(args.params_json)
    elif args.params_file:
        data = json.loads(Path(args.params_file).read_text(encoding="utf-8"))
    elif args.params_stdin:
        data = json.loads(sys.stdin.read())
    else:
        data = {}

    if not isinstance(data, dict):
        raise ValueError("Params must decode to a JSON object.")
    return data


def _build_payload(args: argparse.Namespace) -> Dict[str, Any]:
    payload: Dict[str, Any] = {
        "action": args.action,
        "version": args.version,
        "params": _load_params(args),
    }
    if args.key:
        payload["key"] = args.key
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Send one AnkiConnect request and print the JSON response.",
        epilog=(
            "Examples:\n"
            "  python3 .agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py --action version --pretty\n"
            "  python3 .agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py --action findCards "
            "--params-json '{\"query\":\"deck:\\\"Vocabulary\\\"\"}' --pretty\n"
            "  printf '{\"scopes\":[\"actions\"],\"actions\":null}' | "
            "python3 .agents/skills/anki-card-study-coach/scripts/ankiconnect_request.py --action apiReflect --params-stdin --pretty"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--host", default="127.0.0.1", help="AnkiConnect host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="AnkiConnect port (default: 8765).")
    parser.add_argument("--action", required=True, help="AnkiConnect action name.")
    parser.add_argument("--version", type=int, default=6, help="API version to send (default: 6).")
    parser.add_argument("--key", default="", help="Optional API key.")
    parser.add_argument("--params-json", default="", help="Inline JSON object for params.")
    parser.add_argument("--params-file", default="", help="Path to a JSON file containing params.")
    parser.add_argument(
        "--params-stdin",
        action="store_true",
        help="Read the params JSON object from stdin.",
    )
    parser.add_argument("--timeout", type=float, default=30.0, help="HTTP timeout in seconds (default: 30).")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the JSON response.")
    args = parser.parse_args()

    try:
        payload = _build_payload(args)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print("Failed to build request: {0}".format(exc), file=sys.stderr)
        return 1

    body = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        "http://{0}:{1}".format(args.host, args.port),
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            raw_response = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        print("HTTP error {0}: {1}".format(exc.code, error_body), file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print("Connection failed: {0}".format(exc.reason), file=sys.stderr)
        return 1

    try:
        parsed = json.loads(raw_response)
    except json.JSONDecodeError as exc:
        print("Response was not valid JSON: {0}".format(exc), file=sys.stderr)
        print(raw_response)
        return 1

    if args.pretty:
        print(json.dumps(parsed, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(parsed, ensure_ascii=False))

    if isinstance(parsed, dict) and parsed.get("error") is not None:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
