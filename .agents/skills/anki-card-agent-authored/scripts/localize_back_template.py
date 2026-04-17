#!/usr/bin/env python3
"""Update a model's Card 1 back template labels using a caller-supplied mapping."""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Tuple


DEFAULT_LABEL_KEYS = (
    "Definition:",
    "New Example:",
    "Pronunciation:",
    "British:",
    "American:",
    "Source:",
)

REPO_ROOT = Path(__file__).resolve().parents[4]
CANONICAL_BACK_TEMPLATE_PATH = REPO_ROOT / "src" / "anki_vocab_automation" / "templates" / "vocabulary_back.html"


def _load_mapping(args: argparse.Namespace) -> Dict[str, str]:
    sources = [bool(args.label_json), bool(args.label_file), bool(args.label_stdin)]
    if sum(sources) != 1:
        raise ValueError("Provide exactly one of --label-json, --label-file, or --label-stdin.")

    if args.label_json:
        payload = json.loads(args.label_json)
    elif args.label_file:
        payload = json.loads(Path(args.label_file).read_text(encoding="utf-8"))
    else:
        payload = json.loads(sys.stdin.read())

    if not isinstance(payload, dict):
        raise ValueError("Label mapping must decode to a JSON object.")

    mapping: Dict[str, str] = {}
    for key, value in payload.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise ValueError("All label mapping keys and values must be strings.")
        mapping[key] = value
    return mapping


def _invoke(url: str, action: str, params: Dict[str, object]) -> Dict[str, object]:
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        parsed = json.loads(response.read().decode("utf-8"))
    if parsed.get("error") is not None:
        raise RuntimeError("{0} failed: {1}".format(action, parsed["error"]))
    return parsed


def _load_canonical_back_template() -> str:
    if not CANONICAL_BACK_TEMPLATE_PATH.is_file():
        raise FileNotFoundError("Canonical back template not found: {0}".format(CANONICAL_BACK_TEMPLATE_PATH))
    return CANONICAL_BACK_TEMPLATE_PATH.read_text(encoding="utf-8").strip()


def _localize_canonical_back_template(mapping: Dict[str, str]) -> Tuple[str, List[str]]:
    back = _load_canonical_back_template()
    missing_keys = [key for key in mapping if key not in back]
    if missing_keys:
        raise ValueError(
            "Label keys not found in canonical back template: {0}".format(", ".join(sorted(missing_keys)))
        )

    updated_keys: List[str] = []
    localized_back = back
    for key, value in mapping.items():
        updated_back = localized_back.replace(key, value)
        if updated_back != localized_back:
            updated_keys.append(key)
        localized_back = updated_back

    if not updated_keys:
        raise ValueError("Label mapping did not modify the canonical back template.")

    ordered_keys = [key for key in DEFAULT_LABEL_KEYS if key in updated_keys]
    ordered_keys.extend(key for key in updated_keys if key not in DEFAULT_LABEL_KEYS)
    return localized_back, ordered_keys


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Localize a model's Card 1 back template labels with a JSON mapping.",
    )
    parser.add_argument("--host", default="127.0.0.1", help="AnkiConnect host (default: 127.0.0.1).")
    parser.add_argument("--port", type=int, default=8765, help="AnkiConnect port (default: 8765).")
    parser.add_argument("--model-name", required=True, help="Target Anki model name.")
    parser.add_argument("--card-name", default="Card 1", help="Card template name (default: Card 1).")
    parser.add_argument("--label-json", default="", help="Inline JSON label mapping.")
    parser.add_argument("--label-file", default="", help="Path to a JSON file containing the label mapping.")
    parser.add_argument("--label-stdin", action="store_true", help="Read the label mapping JSON object from stdin.")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print the resulting template metadata.")
    args = parser.parse_args()

    try:
        mapping = _load_mapping(args)
        url = "http://{0}:{1}".format(args.host, args.port)
        template_response = _invoke(url, "modelTemplates", {"modelName": args.model_name})
        templates = template_response["result"]
        if args.card_name not in templates:
            raise RuntimeError("Template '{0}' not found in model '{1}'.".format(args.card_name, args.model_name))

        target = templates[args.card_name]
        back, updated_keys = _localize_canonical_back_template(mapping)

        updated_templates = dict(templates)
        updated_templates[args.card_name] = {
            "Front": target["Front"],
            "Back": back,
        }
        update_response = _invoke(
            url,
            "updateModelTemplates",
            {"model": {"name": args.model_name, "templates": updated_templates}},
        )
    except (OSError, ValueError, json.JSONDecodeError, urllib.error.URLError, RuntimeError) as exc:
        print("Failed to localize back template: {0}".format(exc), file=sys.stderr)
        return 1

    output = {
        "modelName": args.model_name,
        "cardName": args.card_name,
        "updatedKeys": updated_keys,
        "result": update_response.get("result"),
    }
    if args.pretty:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(output, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
