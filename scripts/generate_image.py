#!/usr/bin/env python3
"""Generate an image with gpt-image-1.5 using the stored openai-oauth token."""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path

import httpx

from openai_oauth import get_api_key

IMAGES_ENDPOINT = "https://api.openai.com/v1/images/generations"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate an image via OpenAI Images API using openai-oauth credentials.",
    )
    parser.add_argument("prompt", help="Prompt to generate an image from.")
    parser.add_argument(
        "--model",
        default="gpt-image-1.5",
        help="Image model to use (default: gpt-image-1.5).",
    )
    parser.add_argument(
        "--size",
        default="1024x1024",
        help="Image size (example: 1024x1024, 1024x1536, 1536x1024).",
    )
    parser.add_argument(
        "--quality",
        default="medium",
        choices=["low", "medium", "high"],
        help="Output quality (default: medium).",
    )
    parser.add_argument(
        "--out",
        default="generated.png",
        help="Output image path (default: generated.png).",
    )
    return parser


def _save_image_from_response(payload: dict, out_path: Path) -> None:
    data = payload.get("data") or []
    if not data:
        raise RuntimeError("API response does not contain image data.")

    image_obj = data[0]
    image_b64 = image_obj.get("b64_json")
    image_url = image_obj.get("url")

    if image_b64:
        out_path.write_bytes(base64.b64decode(image_b64))
        return

    if image_url:
        image_resp = httpx.get(image_url, timeout=60)
        image_resp.raise_for_status()
        out_path.write_bytes(image_resp.content)
        return

    raise RuntimeError("Image payload missing both 'b64_json' and 'url'.")


def main() -> int:
    args = _build_parser().parse_args()
    out_path = Path(args.out).expanduser().resolve()
    out_path.parent.mkdir(parents=True, exist_ok=True)

    api_key = get_api_key()
    request_body = {
        "model": args.model,
        "prompt": args.prompt,
        "size": args.size,
        "quality": args.quality,
    }

    try:
        resp = httpx.post(
            IMAGES_ENDPOINT,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json=request_body,
            timeout=180,
        )
        resp.raise_for_status()
    except httpx.HTTPStatusError as e:
        detail = e.response.text.strip()
        print(f"API error: HTTP {e.response.status_code}\n{detail}", file=sys.stderr)
        return 1
    except httpx.HTTPError as e:
        print(f"Network error: {e}", file=sys.stderr)
        return 1

    try:
        _save_image_from_response(resp.json(), out_path)
    except Exception as e:
        print(f"Failed to save image: {e}", file=sys.stderr)
        return 1

    print(f"Saved: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
