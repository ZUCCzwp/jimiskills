#!/usr/bin/env python3
"""JimmyAI image and video API CLI.

Docs: https://docs.jimmyai.cn/llms.txt
"""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Dict, Optional

DEFAULT_BASE_URL = "https://api.viraltok.ai"
DEFAULT_POLL_INTERVAL = 10.0
DEFAULT_POLL_TIMEOUT = 1800.0
DEFAULT_SYNC_TIMEOUT = 180.0
DEFAULT_UPLOAD_TIMEOUT = 300.0
TERMINAL_STATUSES = {"completed", "failed", "canceled", "cancelled"}
SUCCESS_CODE = "20000"


def _die(message: str, code: int = 1) -> None:
    print(f"Error: {message}", file=sys.stderr)
    raise SystemExit(code)


def _warn(message: str) -> None:
    print(f"Warning: {message}", file=sys.stderr)


def _base_url(override: Optional[str]) -> str:
    url = (override or os.getenv("JIMMYAI_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
    return url


def _api_key(dry_run: bool) -> str:
    key = os.getenv("JIMMYAI_API_KEY", "").strip()
    if key:
        print("JIMMYAI_API_KEY is set.", file=sys.stderr)
        return key
    if dry_run:
        _warn("JIMMYAI_API_KEY is not set; dry-run only.")
        return "dry-run-key"
    _die("JIMMYAI_API_KEY is not set. Export it before running.")
    return ""


def _read_prompt(prompt: Optional[str], prompt_file: Optional[str]) -> str:
    if prompt and prompt_file:
        _die("Use --prompt or --prompt-file, not both.")
    if prompt_file:
        path = Path(prompt_file)
        if not path.exists():
            _die(f"Prompt file not found: {path}")
        return path.read_text(encoding="utf-8").strip()
    if prompt:
        return prompt.strip()
    _die("Missing prompt. Use --prompt or --prompt-file.")
    return ""


def _request(
    method: str,
    url: str,
    api_key: str,
    body: Optional[Dict[str, Any]] = None,
    timeout: float = 60.0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    data = json.dumps(body).encode("utf-8") if body is not None else None
    if dry_run:
        print(json.dumps({"method": method, "url": url, "headers": headers, "body": body}, indent=2))
        return {"code": SUCCESS_CODE, "msg": "dry-run", "data": {"task_id": "dry-run-task", "status": "completed"}}

    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        _die(f"HTTP {exc.code}: {raw}")
    except urllib.error.URLError as exc:
        _die(f"Network error: {exc.reason}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        _die(f"Invalid JSON response: {raw[:500]}")


def _multipart_upload(
    url: str,
    api_key: str,
    file_path: Path,
    timeout: float = DEFAULT_UPLOAD_TIMEOUT,
    dry_run: bool = False,
) -> Dict[str, Any]:
    if not file_path.is_file():
        _die(f"File not found: {file_path}")

    filename = file_path.name
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    file_data = file_path.read_bytes()
    boundary = f"----JimmyAI{uuid.uuid4().hex}"
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            file_data,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    if dry_run:
        print(
            json.dumps(
                {
                    "method": "POST",
                    "url": url,
                    "headers": headers,
                    "file": str(file_path),
                    "size_bytes": len(file_data),
                    "mime_type": mime_type,
                },
                indent=2,
            )
        )
        return {
            "code": SUCCESS_CODE,
            "msg": "dry-run",
            "data": {"url": "https://example.com/uploads/dry-run.jpg", "filename": filename, "size": len(file_data), "mime_type": mime_type},
        }

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        _die(f"HTTP {exc.code}: {raw}")
    except urllib.error.URLError as exc:
        _die(f"Network error: {exc.reason}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        _die(f"Invalid JSON response: {raw[:500]}")


def _check_code(payload: Dict[str, Any]) -> Dict[str, Any]:
    code = str(payload.get("code", ""))
    if code != SUCCESS_CODE:
        _die(f"API error code={code} msg={payload.get('msg', '')} payload={json.dumps(payload)}")
    return payload


def _upload_file(
    path: Path,
    api_key: str,
    base: str,
    timeout: float = 300.0,
    dry_run: bool = False,
) -> Dict[str, Any]:
    url = f"{base}/api/open-api/v1/files/upload"
    if dry_run:
        print(
            json.dumps(
                {"method": "POST", "url": url, "field": "file", "path": str(path)},
                indent=2,
            )
        )
        return {
            "code": SUCCESS_CODE,
            "msg": "dry-run",
            "data": {"url": "https://example.com/uploads/dry-run.jpg", "filename": path.name},
        }

    if not path.is_file():
        _die(f"File not found: {path}")

    boundary = f"----jimmyai{uuid.uuid4().hex}"
    filename = path.name
    mime_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    file_data = path.read_bytes()
    body = b"".join(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="file"; filename="{filename}"\r\n'.encode(),
            f"Content-Type: {mime_type}\r\n\r\n".encode(),
            file_data,
            f"\r\n--{boundary}--\r\n".encode(),
        ]
    )
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    }
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        _die(f"HTTP {exc.code}: {raw}")
    except urllib.error.URLError as exc:
        _die(f"Network error: {exc.reason}")

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        _die(f"Invalid JSON response: {raw[:500]}")


def _download_url(url: str, dest: Path, timeout: float = 120.0) -> None:
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        dest.write_bytes(resp.read())
    print(f"Saved to {dest}")


def _poll_task(
    base: str,
    api_key: str,
    task_id: str,
    task_type: str,
    interval: float,
    timeout: float,
    download: Optional[str],
    dry_run: bool,
) -> Dict[str, Any]:
    if task_type == "image":
        path = f"/api/open-api/v1/images/{task_id}"
    else:
        path = f"/api/open-api/v1/videos/{task_id}"

    deadline = time.time() + timeout
    last: Dict[str, Any] = {}
    while True:
        last = _request("GET", f"{base}{path}", api_key, dry_run=dry_run)
        if dry_run:
            return last
        _check_code(last)
        data = last.get("data") or {}
        status = str(data.get("status", "")).lower()
        progress = data.get("progress")
        print(f"status={status} progress={progress}", file=sys.stderr)
        if status in TERMINAL_STATUSES:
            break
        if time.time() >= deadline:
            _die(f"Poll timeout after {timeout}s; last status={status}")
        time.sleep(interval)

    result = (last.get("data") or {}).get("result") or {}
    media_url = result.get("video_url") or result.get("image_url")
    if download and media_url:
        _download_url(media_url, Path(download))
    elif media_url:
        print(media_url)
    print(json.dumps(last, indent=2, ensure_ascii=False))
    return last


def cmd_create_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "duration": args.duration,
    }
    if args.orientation:
        body["orientation"] = args.orientation
    if args.image:
        body["images"] = [args.image]

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/videos",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    task_id = (payload.get("data") or {}).get("task_id")
    if task_id:
        print(task_id)


def cmd_create_seedance_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "duration": args.duration,
    }
    if args.ratio:
        body["ratio"] = args.ratio
    if args.resolution:
        body["resolution"] = args.resolution
    if args.image:
        body["images"] = args.image
    if args.first_image:
        body["first_image"] = args.first_image
    if args.last_image:
        body["last_image"] = args.last_image

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/seedance/videos",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    task_id = (payload.get("data") or {}).get("task_id")
    if task_id:
        print(task_id)


def cmd_create_gemini_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
    }
    if args.duration is not None:
        body["duration"] = args.duration
    if args.resolution:
        body["resolution"] = args.resolution
    if args.aspect_ratio:
        body["aspect_ratio"] = args.aspect_ratio
    elif args.orientation:
        body["orientation"] = args.orientation
    if args.image:
        body["image_urls"] = [args.image]

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/gemini/omni/videos",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_create_image(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
    }
    if args.ratio:
        body["ratio"] = args.ratio
    if args.resolution:
        body["resolution"] = args.resolution
    if args.quality:
        body["quality"] = args.quality

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/images",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_generate_image(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "size": args.size,
        "n": 1,
        "quality": args.quality,
    }

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/images/generations",
        api_key,
        body,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")

    items = ((payload.get("data") or {}).get("data")) or []
    if args.output and items:
        b64 = items[0].get("b64_json")
        if b64:
            Path(args.output).write_bytes(base64.b64decode(b64))
            print(f"Saved to {args.output}")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_poll(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    _poll_task(
        base,
        api_key,
        args.task_id,
        args.type,
        args.interval,
        args.timeout,
        args.download,
        args.dry_run,
    )


def cmd_create_and_poll(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)

    if args.type == "video":
        body: Dict[str, Any] = {
            "model": args.model,
            "prompt": prompt,
            "duration": args.duration,
        }
        if args.orientation:
            body["orientation"] = args.orientation
        if args.image:
            body["images"] = args.image
        url = f"{base}/api/open-api/v1/videos"
        poll_type = "video"
    elif args.type == "gemini-video":
        body = {"model": args.model, "prompt": prompt}
        if args.duration is not None:
            body["duration"] = args.duration
        if args.resolution:
            body["resolution"] = args.resolution
        if args.aspect_ratio:
            body["aspect_ratio"] = args.aspect_ratio
        elif args.orientation:
            body["orientation"] = args.orientation
        if args.image:
            body["image_urls"] = args.image
        url = f"{base}/api/open-api/v1/gemini/omni/videos"
        poll_type = "video"
    elif args.type == "seedance-video":
        body = {
            "model": args.model,
            "prompt": prompt,
            "duration": args.duration,
        }
        if args.ratio:
            body["ratio"] = args.ratio
        if args.resolution:
            body["resolution"] = args.resolution
        if args.image:
            body["images"] = args.image
        if getattr(args, "first_image", None):
            body["first_image"] = args.first_image
        if getattr(args, "last_image", None):
            body["last_image"] = args.last_image
        url = f"{base}/api/open-api/v1/seedance/videos"
        poll_type = "video"
    elif args.type == "image":
        body = {"model": args.model, "prompt": prompt}
        if args.ratio:
            body["ratio"] = args.ratio
        if args.quality:
            body["quality"] = args.quality
        url = f"{base}/api/open-api/v1/images"
        poll_type = "image"
    else:
        _die(f"Unknown --type: {args.type}")

    created = _request("POST", url, api_key, body, dry_run=args.dry_run)
    if args.dry_run:
        task_id = "dry-run-task"
    else:
        _check_code(created)
        task_id = (created.get("data") or {}).get("task_id")
        if not task_id:
            _die(f"No task_id in response: {json.dumps(created)}")
        print(f"task_id={task_id}", file=sys.stderr)

    _poll_task(
        base,
        api_key,
        task_id,
        poll_type,
        args.interval,
        args.timeout,
        args.download,
        args.dry_run,
    )


def _cmd_balance(args: argparse.Namespace, path: str) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    payload = _request("GET", f"{base}{path}", api_key, dry_run=args.dry_run)
    if args.dry_run:
        return
    _check_code(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_user_balance(args: argparse.Namespace) -> None:
    _cmd_balance(args, "/api/open-api/v1/user/balance")


def cmd_key_balance(args: argparse.Namespace) -> None:
    _cmd_balance(args, "/api/open-api/v1/key/balance")


def cmd_upload_file(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    file_path = Path(args.file)
    payload = _multipart_upload(
        f"{base}/api/open-api/v1/files/upload",
        api_key,
        file_path,
        timeout=args.timeout,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _add_common_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--dry-run", action="store_true", help="Print request without calling API")
    parser.add_argument("--json-out", help="Write JSON response to file")
    parser.add_argument("--base-url", help="Override JIMMYAI_BASE_URL")


def _add_prompt_flags(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--prompt", help="Text prompt")
    parser.add_argument("--prompt-file", help="Read prompt from file")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="JimmyAI image and video API CLI")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("create-video", help="Create Sora video task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="sora2-12s")
    p.add_argument("--duration", type=int, default=12)
    p.add_argument("--orientation", choices=["landscape", "portrait"])
    p.add_argument("--image", help="Reference image URL")
    p.set_defaults(func=cmd_create_video)

    p = sub.add_parser("create-seedance-video", help="Create Seedance video task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="seedance2.0-fast-i2v")
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--ratio", default="16:9")
    p.add_argument("--resolution", default="720p", help="SP economy: 720p or 1080p; Mini 特价版 / Mini: 480p or 720p")
    p.add_argument("--image", action="append", help="Reference image URL (repeatable)")
    p.add_argument("--first-image", dest="first_image", help="First frame image URL")
    p.add_argument("--last-image", dest="last_image", help="Last frame image URL")
    p.set_defaults(func=cmd_create_seedance_video)

    p = sub.add_parser("create-gemini-video", help="Create Gemini Omni video task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="Gemini-Omini")
    p.add_argument("--duration", type=int, default=6)
    p.add_argument("--resolution", default="720p")
    p.add_argument("--aspect-ratio", dest="aspect_ratio")
    p.add_argument("--orientation", choices=["landscape", "portrait"])
    p.add_argument("--image", help="Reference image URL")
    p.set_defaults(func=cmd_create_gemini_video)

    p = sub.add_parser("create-image", help="Create async image task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--ratio", default="auto")
    p.add_argument("--resolution", default="1k")
    p.add_argument("--quality", default="low")
    p.set_defaults(func=cmd_create_image)

    p = sub.add_parser("generate-image", help="Sync text-to-image")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="gpt-image-2")
    p.add_argument("--size", default="1024x1024")
    p.add_argument("--quality", default="low")
    p.add_argument("--timeout", type=float, default=DEFAULT_SYNC_TIMEOUT)
    p.add_argument("--output", help="Save b64_json result to file")
    p.set_defaults(func=cmd_generate_image)

    p = sub.add_parser("poll", help="Poll task status")
    _add_common_flags(p)
    p.add_argument("--task-id", required=True)
    p.add_argument("--type", choices=["video", "image"], default="video")
    p.add_argument("--interval", type=float, default=DEFAULT_POLL_INTERVAL)
    p.add_argument("--timeout", type=float, default=DEFAULT_POLL_TIMEOUT)
    p.add_argument("--download", help="Download result media to path")
    p.set_defaults(func=cmd_poll)

    p = sub.add_parser("user-balance", help="Query user JimiCoin account balance")
    _add_common_flags(p)
    p.set_defaults(func=cmd_user_balance)

    p = sub.add_parser("key-balance", help="Query API key quota balance")
    _add_common_flags(p)
    p.set_defaults(func=cmd_key_balance)

    p = sub.add_parser("upload-file", help="Upload image/video/audio file")
    _add_common_flags(p)
    p.add_argument("--file", required=True, help="Local file path to upload")
    p.add_argument("--timeout", type=float, default=DEFAULT_UPLOAD_TIMEOUT)
    p.set_defaults(func=cmd_upload_file)

    p = sub.add_parser("create-and-poll", help="Create task and poll until done")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--type", choices=["video", "gemini-video", "seedance-video", "image"], default="video")
    p.add_argument("--model", default="sora2-12s")
    p.add_argument("--duration", type=int, default=12)
    p.add_argument("--orientation", choices=["landscape", "portrait"])
    p.add_argument("--aspect-ratio", dest="aspect_ratio")
    p.add_argument("--resolution", default="720p")
    p.add_argument("--ratio", default="auto")
    p.add_argument("--quality", default="low")
    p.add_argument("--image", action="append", help="Reference image URL (repeatable)")
    p.add_argument("--first-image", dest="first_image", help="Seedance first frame URL")
    p.add_argument("--last-image", dest="last_image", help="Seedance last frame URL")
    p.add_argument("--interval", type=float, default=DEFAULT_POLL_INTERVAL)
    p.add_argument("--timeout", type=float, default=DEFAULT_POLL_TIMEOUT)
    p.add_argument("--download", help="Download result media to path")
    p.set_defaults(func=cmd_create_and_poll)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
