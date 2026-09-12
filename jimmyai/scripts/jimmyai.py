#!/usr/bin/env python3
"""JimmyAI image and video API CLI.

Docs: https://docs.viraltok.ai/llms.txt
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
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

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


def _norm_model_key(model: str) -> str:
    return (model or "").strip().lower().replace("_", "-")


def _is_seedance25_model(model: str) -> bool:
    m = _norm_model_key(model)
    if not m:
        return False
    return (
        "seedance-2.5" in m
        or "seedance2.5" in m
        or m.startswith("seedance25")
    )


def _is_minimax_h3_model(model: str) -> bool:
    m = _norm_model_key(model)
    return m == "minimax-h3" or m.startswith("minimax-h3-")


def _is_kling_o3_model(model: str) -> bool:
    m = _norm_model_key(model)
    return m == "kling-o3" or m.startswith("kling-o3-") or m in ("klingo3", "kling-o3")


def _is_wan30_model(model: str) -> bool:
    m = _norm_model_key(model)
    return m.startswith("wan3.0") or m.startswith("wan-3.0") or m.startswith("wan30")


def _is_flux3_model(model: str) -> bool:
    m = _norm_model_key(model)
    return m.startswith("flux-3") or m.startswith("flux3")


def _is_video_translate_model(model: str) -> bool:
    m = _norm_model_key(model)
    return m.startswith("video-translate")


def _is_seedance20_family_model(model: str) -> bool:
    """Seedance 2.0 line (not 2.5). Used only to tip wrong dedicated endpoints."""
    if _is_seedance25_model(model):
        return False
    m = _norm_model_key(model)
    if not m:
        return False
    if m.startswith("seedance2.0") or m.startswith("seedance-2.0") or m.startswith("seedance20"):
        return True
    if m.startswith("sd2-") or m.startswith("sd2mx") or m.startswith("sd2-sp") or m.startswith("sd2sp"):
        return True
    return False


# Dedicated create paths: foreign models must not be posted here.
_DEDICATED_VIDEO_ENDPOINTS: Tuple[Tuple[str, Callable[[str], bool], str], ...] = (
    (
        "/api/open-api/v1/seedance25/videos",
        _is_seedance25_model,
        "create-seedance25-video",
    ),
    (
        "/api/open-api/v1/minimax/videos",
        _is_minimax_h3_model,
        "create-minimax-video",
    ),
    (
        "/api/open-api/v1/kling/videos",
        _is_kling_o3_model,
        "create-kling-video",
    ),
    (
        "/api/open-api/v1/wan/videos",
        _is_wan30_model,
        "POST /api/open-api/v1/wan/videos",
    ),
    (
        "/api/open-api/v1/flux3/videos",
        _is_flux3_model,
        "create-flux3-video",
    ),
    (
        "/api/open-api/v1/video-translate/videos",
        _is_video_translate_model,
        "video-translate",
    ),
    (
        "/api/open-api/v1/seedance/videos",
        _is_seedance20_family_model,
        "create-seedance-video",
    ),
)


def _endpoint_path(url_or_path: str) -> str:
    """Return `/api/open-api/v1/...` path from a full URL or path."""
    s = (url_or_path or "").strip()
    idx = s.find("/api/open-api/v1/")
    if idx >= 0:
        path = s[idx:]
        q = path.find("?")
        return path if q < 0 else path[:q]
    return s


def _assert_model_matches_endpoint(model: Optional[str], url_or_path: str) -> None:
    """Refuse cross-family model×path before calling the API (customers often mix paths)."""
    model_s = (model or "").strip()
    if not model_s:
        return
    path = _endpoint_path(url_or_path)
    # Find which dedicated family this model belongs to.
    owner_path = ""
    owner_hint = ""
    for ep_path, matcher, hint in _DEDICATED_VIDEO_ENDPOINTS:
        if matcher(model_s):
            owner_path = ep_path
            owner_hint = hint
            break
    if not owner_path:
        return
    if path == owner_path or path.endswith(owner_path):
        return
    # Only enforce when current call is also a known create endpoint (or seedance/minimax/…).
    known = {ep[0] for ep in _DEDICATED_VIDEO_ENDPOINTS} | {
        "/api/open-api/v1/videos",
        "/api/open-api/v1/gemini/omni/videos",
        "/api/open-api/v1/grok/videos",
        "/api/open-api/v1/digital-human/videos",
        "/api/open-api/v1/remove-subtitle/videos",
        "/api/open-api/v1/super-resolution/videos",
        "/api/open-api/v1/veo/frames",
    }
    if path not in known and not any(path.endswith(k) for k in known):
        return
    hint = owner_hint if owner_hint.startswith("POST ") else f"CLI `{owner_hint}` or POST {owner_path}"
    _die(
        f"model {model_s} must use POST {owner_path} ({hint}); "
        f"current path is {path}. Do not reuse another family's URL and only change model."
    )


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
        "Content-Type": "application/json",
        "Accept": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
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
    elif task_type == "audio":
        path = f"/api/open-api/v1/audios/{task_id}"
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

    data = last.get("data") or {}
    result = data.get("result") or {}
    media_url = (
        result.get("video_url")
        or result.get("image_url")
        or data.get("audioUrl")
        or result.get("audio_url")
    )
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

    url = f"{base}/api/open-api/v1/videos"
    _assert_model_matches_endpoint(args.model, url)
    payload = _request(
        "POST",
        url,
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
    if getattr(args, "video", None):
        body["reference_videos"] = args.video
    if getattr(args, "audio", None):
        body["reference_audios"] = args.audio
    if args.first_image:
        body["first_image"] = args.first_image
    if args.last_image:
        body["last_image"] = args.last_image

    url = f"{base}/api/open-api/v1/seedance/videos"
    _assert_model_matches_endpoint(args.model, url)
    payload = _request(
        "POST",
        url,
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

    url = f"{base}/api/open-api/v1/gemini/omni/videos"
    _assert_model_matches_endpoint(args.model, url)
    payload = _request(
        "POST",
        url,
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


def cmd_create_minimax_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "duration": args.duration,
    }
    if args.aspect_ratio:
        body["aspect_ratio"] = args.aspect_ratio
    if args.size:
        body["size"] = args.size
    if args.image:
        body["reference_images"] = args.image
    if args.audio:
        body["reference_audios"] = args.audio
    if args.first_image:
        body["first_image"] = args.first_image
    if args.last_image:
        body["last_image"] = args.last_image

    url = f"{base}/api/open-api/v1/minimax/videos"
    _assert_model_matches_endpoint(args.model, url)
    payload = _request(
        "POST",
        url,
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


def cmd_create_kling_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "duration": args.duration,
    }
    if args.aspect_ratio:
        body["aspect_ratio"] = args.aspect_ratio
    if args.resolution:
        body["resolution"] = args.resolution
    if args.image:
        body["reference_images"] = args.image
    if args.first_image:
        body["first_image"] = args.first_image
    if args.last_image:
        body["last_image"] = args.last_image
    if getattr(args, "generate_audio", None) is not None:
        body["generate_audio"] = args.generate_audio
    if getattr(args, "reference_mode", None):
        body["reference_mode"] = args.reference_mode

    url = f"{base}/api/open-api/v1/kling/videos"
    _assert_model_matches_endpoint(args.model, url)
    payload = _request(
        "POST",
        url,
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


def cmd_create_seedance25_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "duration": args.duration,
    }
    if args.aspect_ratio:
        body["aspect_ratio"] = args.aspect_ratio
    if args.resolution:
        body["resolution"] = args.resolution
    if args.image:
        body["reference_images"] = args.image
    if getattr(args, "video", None):
        body["reference_videos"] = args.video
    if args.audio:
        body["reference_audios"] = args.audio
    if getattr(args, "first_image", None):
        body["first_image"] = args.first_image
    if getattr(args, "last_image", None):
        body["last_image"] = args.last_image

    url = f"{base}/api/open-api/v1/seedance25/videos"
    _assert_model_matches_endpoint(args.model, url)
    payload = _request(
        "POST",
        url,
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


def _parse_optional_bool(value: str) -> bool:
    v = value.strip().lower()
    if v in ("1", "true", "yes", "y", "on"):
        return True
    if v in ("0", "false", "no", "n", "off"):
        return False
    raise argparse.ArgumentTypeError(f"expected boolean, got {value!r}")


def cmd_create_seedance20933_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    body: Dict[str, Any] = {
        "model": args.model,
        "prompt": prompt,
        "duration": args.duration,
    }
    if args.aspect_ratio:
        body["aspect_ratio"] = args.aspect_ratio
    if args.resolution:
        body["resolution"] = args.resolution
    if getattr(args, "face_processing", None) is not None:
        body["face_processing"] = args.face_processing
    if getattr(args, "generate_audio", None) is not None:
        body["generate_audio"] = args.generate_audio
    if getattr(args, "reference_mode", None):
        body["reference_mode"] = args.reference_mode
    if args.image:
        body["reference_images"] = args.image
    if getattr(args, "video", None):
        body["reference_videos"] = args.video
    if args.audio:
        body["reference_audios"] = args.audio

    url = f"{base}/api/open-api/v1/seedance/videos"
    _assert_model_matches_endpoint(args.model, url)
    payload = _request(
        "POST",
        url,
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


def cmd_remove_bg(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    image_url = (args.image_url or "").strip()
    if not image_url:
        _die("--image-url is required")

    body: Dict[str, Any] = {"image_url": image_url}
    if args.model:
        body["model"] = args.model
    if args.operating_resolution:
        body["operating_resolution"] = args.operating_resolution
    if args.output_format:
        body["output_format"] = args.output_format
    if args.refine_foreground is not None:
        body["refine_foreground"] = args.refine_foreground
    if args.response_format:
        body["response_format"] = args.response_format

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/images/remove-bg",
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

    data = payload.get("data") or {}
    if args.output:
        b64 = data.get("b64_json")
        if b64:
            Path(args.output).write_bytes(base64.b64decode(b64))
            print(f"Saved to {args.output}")
        elif data.get("image_url"):
            _warn("response_format=url returned image_url; use that URL instead of --output")
        else:
            _warn("no b64_json in response; nothing saved to --output")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def cmd_remove_subtitle(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    video_url = (args.video_url or "").strip()
    if not video_url:
        _die("--video-url is required")

    body: Dict[str, Any] = {"video_url": video_url}
    if args.model:
        body["model"] = args.model

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/remove-subtitle/videos",
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


def _video_translate_body(args: argparse.Namespace, *, default_model: str) -> Dict[str, Any]:
    video_url = (getattr(args, "video_url", None) or "").strip()
    if not video_url:
        _die("--video-url is required")
    output_language = (getattr(args, "output_language", None) or "").strip()
    if not output_language:
        _die("--output-language is required")

    model = getattr(args, "model", None) or default_model
    if model == "sora2-12s":
        model = default_model
    body: Dict[str, Any] = {
        "video_url": video_url,
        "output_language": output_language,
        "model": model,
    }
    if getattr(args, "translate_audio_only", None) is not None:
        body["translate_audio_only"] = args.translate_audio_only
    if getattr(args, "speaker_num", None) is not None:
        body["speaker_num"] = args.speaker_num
    if getattr(args, "enable_dynamic_duration", None) is not None:
        body["enable_dynamic_duration"] = args.enable_dynamic_duration
    if getattr(args, "enable_caption", None) is not None:
        body["enable_caption"] = args.enable_caption
    srt_url = (getattr(args, "srt_url", None) or "").strip()
    if srt_url:
        body["srt_url"] = srt_url
    srt_role = (getattr(args, "srt_role", None) or "").strip()
    if srt_role:
        body["srt_role"] = srt_role
    brand_glossary_id = (getattr(args, "brand_glossary_id", None) or "").strip()
    if brand_glossary_id:
        body["brand_glossary_id"] = brand_glossary_id
    return body


def cmd_video_translate(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _video_translate_body(args, default_model="video-translate-precision")

    url = f"{base}/api/open-api/v1/video-translate/videos"
    _assert_model_matches_endpoint(body.get("model"), url)
    payload = _request(
        "POST",
        url,
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


def _print_create_payload(args: argparse.Namespace, payload: Dict[str, Any], *, id_keys: tuple = ("task_id", "id")) -> None:
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    data = payload.get("data") or {}
    for key in id_keys:
        value = data.get(key)
        if value:
            print(value)
            return


def _grok_video_body(args: argparse.Namespace, *, default_model: str) -> Dict[str, Any]:
    prompt = _read_prompt(args.prompt, args.prompt_file)
    model = getattr(args, "model", None) or default_model
    if model == "sora2-12s":
        model = default_model
    images = list(getattr(args, "image", None) or [])
    if len(images) != 1:
        _die("Grok 1.5 video requires exactly one --image URL")
    body: Dict[str, Any] = {
        "model": model,
        "prompt": prompt,
        "image_urls": images,
    }
    duration = getattr(args, "duration", None)
    if duration not in (10, 15):
        duration = 10
    body["duration"] = duration
    ratio = getattr(args, "ratio", None) or getattr(args, "aspect_ratio", None)
    if ratio and ratio != "auto":
        body["ratio"] = ratio
    return body


def cmd_create_grok_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _grok_video_body(args, default_model="grok-imagine-video-1.5")
    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/grok/videos",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    _print_create_payload(args, payload)


def _digital_human_body(args: argparse.Namespace, *, default_model: str) -> Dict[str, Any]:
    video_url = (getattr(args, "video_url", None) or "").strip()
    audio_url = (getattr(args, "audio_url", None) or "").strip()
    if not video_url:
        _die("--video-url is required")
    if not audio_url:
        _die("--audio-url is required")
    model = getattr(args, "model", None) or default_model
    if model == "sora2-12s":
        model = default_model
    body: Dict[str, Any] = {
        "model": model,
        "video_url": video_url,
        "audio_url": audio_url,
    }
    if getattr(args, "model_version", None) is not None:
        body["model_version"] = args.model_version
    if getattr(args, "side_face", None) is not None:
        body["side_face"] = args.side_face
    if getattr(args, "tilted_face", None) is not None:
        body["tilted_face"] = args.tilted_face
    return body


def cmd_create_digital_human(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _digital_human_body(args, default_model="digitalHuman")
    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/digital-human/videos",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    _print_create_payload(args, payload)


def cmd_upscale(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    image_url = (args.image_url or "").strip()
    if not image_url:
        _die("--image-url is required")

    body: Dict[str, Any] = {"image_url": image_url}
    if args.upscale_mode:
        body["upscale_mode"] = args.upscale_mode
    if args.upscale_factor is not None:
        body["upscale_factor"] = args.upscale_factor
    if args.target_resolution:
        body["target_resolution"] = args.target_resolution
    if args.noise_scale is not None:
        body["noise_scale"] = args.noise_scale
    if args.output_format:
        body["output_format"] = args.output_format
    if args.seed is not None:
        body["seed"] = args.seed
    if args.response_format:
        body["response_format"] = args.response_format

    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/images/upscale",
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

    data = payload.get("data") or {}
    if args.output:
        b64 = data.get("b64_json")
        if b64:
            Path(args.output).write_bytes(base64.b64decode(b64))
            print(f"Saved to {args.output}")
        elif data.get("image_url"):
            _download_url(data["image_url"], Path(args.output))
        else:
            _warn("no b64_json/image_url in response; nothing saved to --output")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _flux3_video_body(args: argparse.Namespace, *, default_model: str) -> Dict[str, Any]:
    model = getattr(args, "model", None) or default_model
    if model == "sora2-12s":
        model = default_model
    body: Dict[str, Any] = {"model": model}
    if model != "flux-3-enhance":
        prompt = _read_prompt(args.prompt, args.prompt_file)
        body["prompt"] = prompt
    duration = getattr(args, "duration", None)
    if duration is not None:
        body["duration"] = duration
    aspect = getattr(args, "aspect_ratio", None) or getattr(args, "ratio", None)
    if aspect and aspect != "auto" and model != "flux-3-enhance":
        body["aspect_ratio"] = aspect
    if getattr(args, "generate_audio", None) is not None and model != "flux-3-enhance":
        body["generate_audio"] = args.generate_audio
    if getattr(args, "safety_tolerance", None) is not None:
        body["safety_tolerance"] = args.safety_tolerance

    image_url = (getattr(args, "image_url", None) or "").strip()
    if not image_url and getattr(args, "image", None):
        imgs = args.image if isinstance(args.image, list) else [args.image]
        if imgs:
            image_url = (imgs[0] or "").strip()
    if image_url:
        body["image_url"] = image_url

    start = (getattr(args, "first_image", None) or getattr(args, "start_image_url", None) or "").strip()
    end = (getattr(args, "last_image", None) or getattr(args, "end_image_url", None) or "").strip()
    if start:
        body["start_image_url"] = start
    if end:
        body["end_image_url"] = end

    video_url = (getattr(args, "video_url", None) or "").strip()
    if video_url:
        body["video_url"] = video_url
    draft = (getattr(args, "draft_cache_url", None) or "").strip()
    if draft:
        body["draft_cache_url"] = draft

    keyframes_json = (getattr(args, "keyframes_json", None) or "").strip()
    if keyframes_json:
        try:
            body["keyframes"] = json.loads(keyframes_json)
        except json.JSONDecodeError as exc:
            _die(f"Invalid --keyframes-json: {exc}")

    if model == "flux-3-i2v-draft" and not body.get("image_url"):
        _die("flux-3-i2v-draft requires --image-url or --image")
    if model == "flux-3-flf-draft" and (not body.get("start_image_url") or not body.get("end_image_url")):
        _die("flux-3-flf-draft requires --first-image and --last-image")
    if model == "flux-3-keyframes-draft" and not body.get("keyframes"):
        _die("flux-3-keyframes-draft requires --keyframes-json")
    if model == "flux-3-extend-draft" and not body.get("video_url"):
        _die("flux-3-extend-draft requires --video-url")
    if model == "flux-3-enhance" and not body.get("draft_cache_url"):
        _die("flux-3-enhance requires --draft-cache-url")
    return body


def cmd_create_flux3_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _flux3_video_body(args, default_model="flux-3-draft")
    url = f"{base}/api/open-api/v1/flux3/videos"
    _assert_model_matches_endpoint(body.get("model"), url)
    payload = _request(
        "POST",
        url,
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    _print_create_payload(args, payload)


def _veo_frames_body(args: argparse.Namespace, *, default_model: str) -> Dict[str, Any]:
    prompt = _read_prompt(args.prompt, args.prompt_file)
    model = getattr(args, "model", None) or default_model
    if model == "sora2-12s":
        model = default_model
    body: Dict[str, Any] = {"model": model, "prompt": prompt}
    if getattr(args, "resolution", None):
        body["resolution"] = args.resolution
    if getattr(args, "orientation", None):
        body["orientation"] = args.orientation
    first = (getattr(args, "first_image", None) or getattr(args, "first_frame_url", None) or "").strip()
    last = (getattr(args, "last_image", None) or getattr(args, "last_frame_url", None) or "").strip()
    images = list(getattr(args, "image", None) or [])
    if images and (first or last):
        _die("VEO: --image and --first-image/--last-image are mutually exclusive")
    if first:
        body["first_frame_url"] = first
    if last:
        body["last_frame_url"] = last
    if images:
        body["images"] = images
    return body


def cmd_create_veo_frames(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _veo_frames_body(args, default_model="veo_3_1_fast")
    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/veo/frames",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    _print_create_payload(args, payload)


def _super_resolution_body(args: argparse.Namespace, *, default_model: str) -> Dict[str, Any]:
    video_url = (getattr(args, "video_url", None) or "").strip()
    if not video_url:
        _die("--video-url is required")
    model = getattr(args, "model", None) or default_model
    if model == "sora2-12s":
        model = default_model
    return {"model": model, "video_url": video_url}


def cmd_super_resolution(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _super_resolution_body(args, default_model="superResolution-1080p-lowfps")
    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/super-resolution/videos",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    _print_create_payload(args, payload)


def cmd_understand_video(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    prompt = _read_prompt(args.prompt, args.prompt_file)
    video_url = (getattr(args, "video_url", None) or "").strip()
    if not video_url:
        _die("--video-url is required")
    body: Dict[str, Any] = {
        "model": args.model or "gemini-3.7-flash",
        "video_url": video_url,
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
    }
    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/videos/understand",
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
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def _sound_clone_body(args: argparse.Namespace) -> Dict[str, Any]:
    file_url = (getattr(args, "file_url", None) or "").strip()
    if not file_url:
        _die("--file-url is required")
    body: Dict[str, Any] = {"fileUrl": file_url}
    content = (getattr(args, "content_text", None) or "").strip()
    if content:
        body["contentText"] = content
    if getattr(args, "sound_version", None):
        body["soundVersion"] = args.sound_version
    if getattr(args, "language", None):
        body["language"] = args.language
    return body


def cmd_sound_clone(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _sound_clone_body(args)
    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/soundCloning/clones",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    _print_create_payload(args, payload, id_keys=("id", "task_id"))


def _sound_clone_audio_body(args: argparse.Namespace) -> Dict[str, Any]:
    model_id = (getattr(args, "model_id", None) or "").strip()
    content = (getattr(args, "content_text", None) or "").strip()
    if not model_id:
        _die("--model-id is required")
    if not content:
        _die("--content-text is required")
    body: Dict[str, Any] = {"modelId": model_id, "contentText": content}
    if getattr(args, "sound_version", None):
        body["soundVersion"] = args.sound_version
    if getattr(args, "language", None):
        body["language"] = args.language
    if getattr(args, "emotion", None):
        body["emotion"] = args.emotion
    if getattr(args, "speed", None) is not None:
        body["speed"] = args.speed
    if getattr(args, "vol", None) is not None:
        body["vol"] = args.vol
    if getattr(args, "pitch", None) is not None:
        body["pitch"] = args.pitch
    if getattr(args, "subtitle_enable", None) is not None:
        body["subtitleEnable"] = args.subtitle_enable
    if getattr(args, "subtitle_type", None):
        body["subtitleType"] = args.subtitle_type
    return body


def cmd_sound_clone_audio(args: argparse.Namespace) -> None:
    api_key = _api_key(args.dry_run)
    base = _base_url(args.base_url)
    body = _sound_clone_audio_body(args)
    payload = _request(
        "POST",
        f"{base}/api/open-api/v1/soundCloning/audios",
        api_key,
        body,
        dry_run=args.dry_run,
    )
    if args.dry_run:
        return
    _check_code(payload)
    _print_create_payload(args, payload, id_keys=("id", "task_id"))


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

    if args.type == "remove-subtitle":
        video_url = (getattr(args, "video_url", None) or "").strip()
        if not video_url:
            _die("--video-url is required for --type remove-subtitle")
        # create-and-poll defaults --model to sora2-12s; remap for this type
        model = args.model if args.model and args.model != "sora2-12s" else "video_remove_subtitle"
        body: Dict[str, Any] = {"video_url": video_url, "model": model}
        url = f"{base}/api/open-api/v1/remove-subtitle/videos"
        poll_type = "video"
    elif args.type == "video-translate":
        body = _video_translate_body(args, default_model="video-translate-precision")
        url = f"{base}/api/open-api/v1/video-translate/videos"
        poll_type = "video"
    elif args.type == "grok-video":
        body = _grok_video_body(args, default_model="grok-imagine-video-1.5")
        url = f"{base}/api/open-api/v1/grok/videos"
        poll_type = "video"
    elif args.type == "digital-human":
        body = _digital_human_body(args, default_model="digitalHuman")
        url = f"{base}/api/open-api/v1/digital-human/videos"
        poll_type = "video"
    elif args.type == "flux3-video":
        body = _flux3_video_body(args, default_model="flux-3-draft")
        url = f"{base}/api/open-api/v1/flux3/videos"
        poll_type = "video"
    elif args.type == "veo-frames":
        body = _veo_frames_body(args, default_model="veo_3_1_fast")
        url = f"{base}/api/open-api/v1/veo/frames"
        poll_type = "video"
    elif args.type == "super-resolution":
        body = _super_resolution_body(args, default_model="superResolution-1080p-lowfps")
        url = f"{base}/api/open-api/v1/super-resolution/videos"
        poll_type = "video"
    elif args.type == "sound-clone":
        body = _sound_clone_body(args)
        url = f"{base}/api/open-api/v1/soundCloning/clones"
        poll_type = "audio"
    elif args.type == "sound-clone-audio":
        body = _sound_clone_audio_body(args)
        url = f"{base}/api/open-api/v1/soundCloning/audios"
        poll_type = "audio"
    elif args.type == "video":
        prompt = _read_prompt(args.prompt, args.prompt_file)
        body = {
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
        prompt = _read_prompt(args.prompt, args.prompt_file)
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
        prompt = _read_prompt(args.prompt, args.prompt_file)
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
        if getattr(args, "video", None):
            body["reference_videos"] = args.video
        if getattr(args, "audio", None):
            body["reference_audios"] = args.audio
        if getattr(args, "first_image", None):
            body["first_image"] = args.first_image
        if getattr(args, "last_image", None):
            body["last_image"] = args.last_image
        url = f"{base}/api/open-api/v1/seedance/videos"
        poll_type = "video"
    elif args.type == "minimax-video":
        prompt = _read_prompt(args.prompt, args.prompt_file)
        body = {
            "model": args.model,
            "prompt": prompt,
            "duration": args.duration,
        }
        if args.aspect_ratio:
            body["aspect_ratio"] = args.aspect_ratio
        if getattr(args, "size", None):
            body["size"] = args.size
        if args.image:
            body["reference_images"] = args.image
        if getattr(args, "audio", None):
            body["reference_audios"] = args.audio
        if getattr(args, "first_image", None):
            body["first_image"] = args.first_image
        if getattr(args, "last_image", None):
            body["last_image"] = args.last_image
        url = f"{base}/api/open-api/v1/minimax/videos"
        poll_type = "video"
    elif args.type == "kling-video":
        prompt = _read_prompt(args.prompt, args.prompt_file)
        model = args.model if args.model and args.model != "sora2-12s" else "kling-o3"
        body = {
            "model": model,
            "prompt": prompt,
            "duration": args.duration,
        }
        if args.aspect_ratio:
            body["aspect_ratio"] = args.aspect_ratio
        if args.resolution:
            body["resolution"] = args.resolution
        if args.image:
            body["reference_images"] = args.image
        if getattr(args, "first_image", None):
            body["first_image"] = args.first_image
        if getattr(args, "last_image", None):
            body["last_image"] = args.last_image
        if getattr(args, "generate_audio", None) is not None:
            body["generate_audio"] = args.generate_audio
        if getattr(args, "reference_mode", None):
            body["reference_mode"] = args.reference_mode
        url = f"{base}/api/open-api/v1/kling/videos"
        poll_type = "video"
    elif args.type == "seedance25-video":
        prompt = _read_prompt(args.prompt, args.prompt_file)
        body = {
            "model": args.model,
            "prompt": prompt,
            "duration": args.duration,
        }
        if args.aspect_ratio:
            body["aspect_ratio"] = args.aspect_ratio
        if args.resolution:
            body["resolution"] = args.resolution
        if args.image:
            body["reference_images"] = args.image
        if getattr(args, "video", None):
            body["reference_videos"] = args.video
        if getattr(args, "audio", None):
            body["reference_audios"] = args.audio
        if getattr(args, "first_image", None):
            body["first_image"] = args.first_image
        if getattr(args, "last_image", None):
            body["last_image"] = args.last_image
        url = f"{base}/api/open-api/v1/seedance25/videos"
        poll_type = "video"
    elif args.type == "seedance20933-video":
        prompt = _read_prompt(args.prompt, args.prompt_file)
        body = {
            "model": args.model,
            "prompt": prompt,
            "duration": args.duration,
        }
        if args.aspect_ratio:
            body["aspect_ratio"] = args.aspect_ratio
        if args.resolution:
            body["resolution"] = args.resolution
        if getattr(args, "face_processing", None) is not None:
            body["face_processing"] = args.face_processing
        if getattr(args, "generate_audio", None) is not None:
            body["generate_audio"] = args.generate_audio
        if getattr(args, "reference_mode", None):
            body["reference_mode"] = args.reference_mode
        if args.image:
            body["reference_images"] = args.image
        if getattr(args, "video", None):
            body["reference_videos"] = args.video
        if getattr(args, "audio", None):
            body["reference_audios"] = args.audio
        url = f"{base}/api/open-api/v1/seedance/videos"
        poll_type = "video"
    elif args.type == "image":
        prompt = _read_prompt(args.prompt, args.prompt_file)
        body = {"model": args.model, "prompt": prompt}
        if args.ratio:
            body["ratio"] = args.ratio
        if args.quality:
            body["quality"] = args.quality
        url = f"{base}/api/open-api/v1/images"
        poll_type = "image"
    else:
        _die(f"Unknown --type: {args.type}")

    _assert_model_matches_endpoint(body.get("model") if isinstance(body, dict) else None, url)
    created = _request("POST", url, api_key, body, dry_run=args.dry_run)
    if args.dry_run:
        task_id = "dry-run-task"
    else:
        _check_code(created)
        data = created.get("data") or {}
        task_id = data.get("task_id") or data.get("id")
        if not task_id:
            _die(f"No task_id/id in response: {json.dumps(created)}")
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


def cmd_list_models(args: argparse.Namespace) -> None:
    """List available billing models via GET /api/openapi/model/catalog (no API key required)."""
    base = _base_url(args.base_url)
    params: Dict[str, str] = {}
    search = (args.search or "").strip()
    if search:
        params["search"] = search
    url = f"{base}/api/openapi/model/catalog"
    if params:
        url = f"{url}?{urllib.parse.urlencode(params)}"

    api_key = os.getenv("JIMMYAI_API_KEY", "").strip()
    if not api_key and args.dry_run:
        _warn("JIMMYAI_API_KEY is not set; catalog needs no key (dry-run).")
    elif api_key:
        print("JIMMYAI_API_KEY is set.", file=sys.stderr)

    if args.dry_run:
        print(json.dumps({"method": "GET", "url": url, "headers": {"Accept": "application/json"}, "body": None}, indent=2))
        return

    payload = _request("GET", url, api_key, dry_run=False)
    _check_code(payload)

    model_type = (args.type or "").strip().lower()
    if model_type:
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
        items: List[Any] = list(data.get("list") or []) if isinstance(data, dict) else []

        def _type_match(raw: Any) -> bool:
            mt = str(raw or "").strip().lower()
            if not mt:
                return False
            if mt == model_type:
                return True
            # Catalog often uses plural forms (videos/images/audios).
            if model_type in {"video", "image", "audio"} and mt == f"{model_type}s":
                return True
            if model_type.endswith("s") and mt == model_type[:-1]:
                return True
            return False

        filtered = [item for item in items if isinstance(item, dict) and _type_match(item.get("model_type"))]
        payload = {
            **payload,
            "data": {**(data if isinstance(data, dict) else {}), "list": filtered},
        }

    if args.json_out:
        Path(args.json_out).write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


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
    p.add_argument("--video", action="append", help="Reference video URL (repeatable; e.g. seedance2.0-gz*)")
    p.add_argument("--audio", action="append", help="Reference audio URL (repeatable; e.g. seedance2.0-gz*)")
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

    p = sub.add_parser("create-minimax-video", help="Create MiniMax H3 video task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="minimax-h3")
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--aspect-ratio", dest="aspect_ratio", default="16:9")
    p.add_argument("--size", default="2560x1440")
    p.add_argument("--image", action="append", help="Reference image URL (repeatable, max 5)")
    p.add_argument("--audio", action="append", help="Reference audio URL (repeatable, max 1)")
    p.add_argument("--first-image", dest="first_image", help="First frame image URL")
    p.add_argument("--last-image", dest="last_image", help="Last frame image URL")
    p.set_defaults(func=cmd_create_minimax_video)

    p = sub.add_parser("create-kling-video", help="Create Kling O3 video task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="kling-o3")
    p.add_argument("--duration", type=int, default=6)
    p.add_argument("--aspect-ratio", dest="aspect_ratio", default="16:9")
    p.add_argument("--resolution", default="720p", choices=["720p", "1080p"])
    p.add_argument("--image", action="append", help="Reference image URL (repeatable, max 3)")
    p.add_argument("--first-image", dest="first_image", help="First frame image URL")
    p.add_argument("--last-image", dest="last_image", help="Last frame image URL")
    p.add_argument(
        "--generate-audio",
        dest="generate_audio",
        type=_parse_optional_bool,
        default=None,
        help="Whether to generate an audio track (true/false)",
    )
    p.add_argument("--reference-mode", dest="reference_mode", help="Optional reference mode")
    p.set_defaults(func=cmd_create_kling_video)

    p = sub.add_parser("create-seedance25-video", help="Create Seedance 2.5 video task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument(
        "--model",
        default="seedance-2.5",
        help="seedance-2.5 (standard) or seedance-2.5-sp (SP, 0.5/s, 720p only)",
    )
    p.add_argument("--duration", type=int, default=4)
    p.add_argument("--aspect-ratio", dest="aspect_ratio", default="9:16")
    p.add_argument("--resolution", default="480p", choices=["480p", "720p"])
    p.add_argument("--image", action="append", help="Reference image URL (repeatable, max 30)")
    p.add_argument("--video", action="append", help="Reference video URL (repeatable, max 10)")
    p.add_argument("--audio", action="append", help="Reference audio URL (repeatable, max 10)")
    p.add_argument("--first-image", dest="first_image", help="First frame image URL (SP only)")
    p.add_argument("--last-image", dest="last_image", help="Last frame image URL (SP only)")
    p.set_defaults(func=cmd_create_seedance25_video)

    p = sub.add_parser("create-seedance20933-video", help="Create Seedance 2.0 933 video task")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="seedance2.0-933")
    p.add_argument("--duration", type=int, default=4)
    p.add_argument("--aspect-ratio", dest="aspect_ratio", default="16:9")
    p.add_argument("--resolution", default="480p", choices=["480p", "720p", "1080p"])
    p.add_argument(
        "--face-processing",
        dest="face_processing",
        type=_parse_optional_bool,
        default=None,
        help="Enable face processing (true/false); API default true",
    )
    p.add_argument(
        "--generate-audio",
        dest="generate_audio",
        type=_parse_optional_bool,
        default=None,
        help="Generate audio (true/false); API default false",
    )
    p.add_argument(
        "--reference-mode",
        dest="reference_mode",
        choices=["image", "frame"],
        default=None,
        help="Reference mode (default image)",
    )
    p.add_argument("--image", action="append", help="Reference image URL (repeatable, max 9)")
    p.add_argument("--video", action="append", help="Reference video URL (repeatable, max 3)")
    p.add_argument("--audio", action="append", help="Reference audio URL (repeatable, max 3)")
    p.set_defaults(func=cmd_create_seedance20933_video)

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

    p = sub.add_parser("remove-bg", help="Sync background removal")
    _add_common_flags(p)
    p.add_argument("--image-url", required=True, help="Public source image URL")
    p.add_argument("--model", default="general_light_2k")
    p.add_argument("--operating-resolution", dest="operating_resolution", default="2048x2048")
    p.add_argument("--output-format", dest="output_format", default="png", choices=["png", "webp", "gif"])
    p.add_argument(
        "--refine-foreground",
        dest="refine_foreground",
        type=_parse_optional_bool,
        default=None,
        help="Refine foreground edges (true/false, default true server-side)",
    )
    p.add_argument(
        "--response-format",
        dest="response_format",
        choices=["b64_json", "url"],
        default="b64_json",
        help="b64_json (default) or url",
    )
    p.add_argument("--timeout", type=float, default=DEFAULT_SYNC_TIMEOUT)
    p.add_argument("--output", help="Save b64_json result to file")
    p.set_defaults(func=cmd_remove_bg)

    p = sub.add_parser("remove-subtitle", help="Create video subtitle-removal task (async)")
    _add_common_flags(p)
    p.add_argument("--video-url", required=True, help="Public source video URL")
    p.add_argument("--model", default="video_remove_subtitle")
    p.set_defaults(func=cmd_remove_subtitle)

    p = sub.add_parser("video-translate", help="Create video translation task (async)")
    _add_common_flags(p)
    p.add_argument("--video-url", required=True, help="Public source video URL (max 8 minutes)")
    p.add_argument(
        "--output-language",
        dest="output_language",
        required=True,
        help="Target language enum or short alias (e.g. Chinese, zh, English)",
    )
    p.add_argument(
        "--model",
        default="video-translate-precision",
        help="video-translate-precision (default) or video-translate-speed",
    )
    p.add_argument(
        "--translate-audio-only",
        dest="translate_audio_only",
        type=_parse_optional_bool,
        default=None,
        help="Translate voice track only (true/false)",
    )
    p.add_argument("--speaker-num", dest="speaker_num", type=int, default=None, help="Number of speakers")
    p.add_argument(
        "--enable-dynamic-duration",
        dest="enable_dynamic_duration",
        type=_parse_optional_bool,
        default=None,
        help="Adjust duration for speaking rate (true/false, server default true)",
    )
    p.add_argument(
        "--enable-caption",
        dest="enable_caption",
        type=_parse_optional_bool,
        default=None,
        help="Generate SRT captions (true/false); result.caption_url when done",
    )
    p.add_argument("--srt-url", dest="srt_url", help="Custom SRT file public URL")
    p.add_argument("--srt-role", dest="srt_role", choices=["input", "output"], help="SRT role")
    p.add_argument("--brand-glossary-id", dest="brand_glossary_id", help="Brand glossary ID")
    p.set_defaults(func=cmd_video_translate)

    p = sub.add_parser("create-grok-video", help="Create Grok 1.5 video task (async)")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="grok-imagine-video-1.5")
    p.add_argument("--duration", type=int, default=10, choices=[10, 15])
    p.add_argument("--ratio", default="16:9", help="16:9 / 9:16 / 1:1 / 3:2 / 2:3")
    p.add_argument("--image", action="append", required=True, help="Exactly one reference image URL")
    p.set_defaults(func=cmd_create_grok_video)

    p = sub.add_parser("create-digital-human", help="Create digital-human lip-sync task (async)")
    _add_common_flags(p)
    p.add_argument("--model", default="digitalHuman")
    p.add_argument("--video-url", dest="video_url", required=True, help="Face video public URL")
    p.add_argument("--audio-url", dest="audio_url", required=True, help="Drive audio public URL")
    p.add_argument("--model-version", dest="model_version", type=int, choices=[1, 2], default=None)
    p.add_argument("--side-face", dest="side_face", type=int, choices=[0, 1], default=None)
    p.add_argument("--tilted-face", dest="tilted_face", type=int, choices=[0, 1], default=None)
    p.set_defaults(func=cmd_create_digital_human)

    p = sub.add_parser("upscale", help="Sync image upscale")
    _add_common_flags(p)
    p.add_argument("--image-url", dest="image_url", required=True, help="Public source image URL")
    p.add_argument("--upscale-mode", dest="upscale_mode", choices=["factor", "target"], default="factor")
    p.add_argument("--upscale-factor", dest="upscale_factor", type=float, default=None, help="1-20; factor mode")
    p.add_argument(
        "--target-resolution",
        dest="target_resolution",
        choices=["720p", "1080p", "1440p", "2160p", "2k", "4k"],
        default=None,
    )
    p.add_argument("--noise-scale", dest="noise_scale", type=float, default=None)
    p.add_argument("--output-format", dest="output_format", choices=["jpg", "png", "webp"], default="jpg")
    p.add_argument("--seed", type=int, default=None)
    p.add_argument(
        "--response-format",
        dest="response_format",
        choices=["b64_json", "url"],
        default="b64_json",
    )
    p.add_argument("--timeout", type=float, default=DEFAULT_SYNC_TIMEOUT)
    p.add_argument("--output", help="Save result image to file")
    p.set_defaults(func=cmd_upscale)

    p = sub.add_parser("create-flux3-video", help="Create Flux 3 video task (async)")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument(
        "--model",
        default="flux-3-draft",
        help="flux-3-draft / flux-3-i2v-draft / flux-3-flf-draft / flux-3-keyframes-draft / flux-3-extend-draft / flux-3-enhance",
    )
    p.add_argument("--duration", type=int, default=5)
    p.add_argument("--aspect-ratio", dest="aspect_ratio", default="16:9")
    p.add_argument("--image", action="append", help="Alias for --image-url (first value)")
    p.add_argument("--image-url", dest="image_url", help="Required for flux-3-i2v-draft")
    p.add_argument("--first-image", dest="first_image", help="start_image_url for flf draft")
    p.add_argument("--last-image", dest="last_image", help="end_image_url for flf draft")
    p.add_argument("--video-url", dest="video_url", help="Required for flux-3-extend-draft")
    p.add_argument("--draft-cache-url", dest="draft_cache_url", help="Required for flux-3-enhance")
    p.add_argument("--keyframes-json", dest="keyframes_json", help="JSON array for keyframes draft")
    p.add_argument(
        "--generate-audio",
        dest="generate_audio",
        type=_parse_optional_bool,
        default=None,
        help="Generate audio (true/false; default true server-side)",
    )
    p.add_argument("--safety-tolerance", dest="safety_tolerance", type=int, default=None)
    p.set_defaults(func=cmd_create_flux3_video)

    p = sub.add_parser("create-veo-frames", help="Create VEO Fast/Lite frames task (async)")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--model", default="veo_3_1_fast", help="veo_3_1_fast / veo_3_1_fast-4k / veo_3_1_lite")
    p.add_argument("--resolution", default="720p", choices=["720p", "1080p", "4k"])
    p.add_argument("--orientation", choices=["landscape", "portrait"])
    p.add_argument("--image", action="append", help="Reference image URL (1-3; exclusive with frames)")
    p.add_argument("--first-image", dest="first_image", help="first_frame_url")
    p.add_argument("--last-image", dest="last_image", help="last_frame_url")
    p.set_defaults(func=cmd_create_veo_frames)

    p = sub.add_parser("super-resolution", help="Create video super-resolution task (async)")
    _add_common_flags(p)
    p.add_argument("--video-url", dest="video_url", required=True, help="Public source video URL")
    p.add_argument(
        "--model",
        default="superResolution-1080p-lowfps",
        help="superResolution-{720p|1080p|2k|4k}-{lowfps|highfps}",
    )
    p.set_defaults(func=cmd_super_resolution)

    p = sub.add_parser("understand-video", help="Sync video understanding (Gemini)")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument("--video-url", dest="video_url", required=True, help="Public source video URL")
    p.add_argument("--model", default="gemini-3.7-flash")
    p.add_argument("--timeout", type=float, default=DEFAULT_SYNC_TIMEOUT)
    p.set_defaults(func=cmd_understand_video)

    p = sub.add_parser("sound-clone", help="Create SoundClone preview task (async)")
    _add_common_flags(p)
    p.add_argument("--file-url", dest="file_url", required=True, help="Source audio/video public URL")
    p.add_argument("--content-text", dest="content_text", help="Preview script (<270 chars)")
    p.add_argument("--sound-version", dest="sound_version", choices=["v1", "v2"], default=None)
    p.add_argument("--language", default=None, help="e.g. Chinese, English, auto")
    p.set_defaults(func=cmd_sound_clone)

    p = sub.add_parser("sound-clone-audio", help="Create SoundClone production audio task (async)")
    _add_common_flags(p)
    p.add_argument("--model-id", dest="model_id", required=True, help="modelId from completed preview")
    p.add_argument("--content-text", dest="content_text", required=True, help="Script (<10000 chars)")
    p.add_argument("--sound-version", dest="sound_version", choices=["v1", "v2"], default=None)
    p.add_argument("--language", default=None)
    p.add_argument("--emotion", default=None)
    p.add_argument("--speed", type=float, default=None)
    p.add_argument("--vol", type=float, default=None)
    p.add_argument("--pitch", type=int, default=None)
    p.add_argument(
        "--subtitle-enable",
        dest="subtitle_enable",
        type=_parse_optional_bool,
        default=None,
    )
    p.add_argument("--subtitle-type", dest="subtitle_type", choices=["word"], default=None)
    p.set_defaults(func=cmd_sound_clone_audio)

    p = sub.add_parser("poll", help="Poll task status")
    _add_common_flags(p)
    p.add_argument("--task-id", required=True)
    p.add_argument("--type", choices=["video", "image", "audio"], default="video")
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

    p = sub.add_parser("list-models", help="List available models from catalog API")
    _add_common_flags(p)
    p.add_argument("--search", help="Substring filter (model_name / display_name / type / remark)")
    p.add_argument(
        "--type",
        dest="type",
        help="Client-side filter by model_type (video/videos, image/images, audio/audios, llm, ...)",
    )
    p.set_defaults(func=cmd_list_models)

    p = sub.add_parser("upload-file", help="Upload image/video/audio file")
    _add_common_flags(p)
    p.add_argument("--file", required=True, help="Local file path to upload")
    p.add_argument("--timeout", type=float, default=DEFAULT_UPLOAD_TIMEOUT)
    p.set_defaults(func=cmd_upload_file)

    p = sub.add_parser("create-and-poll", help="Create task and poll until done")
    _add_common_flags(p)
    _add_prompt_flags(p)
    p.add_argument(
        "--type",
        choices=[
            "video",
            "gemini-video",
            "seedance-video",
            "seedance25-video",
            "seedance20933-video",
            "minimax-video",
            "kling-video",
            "remove-subtitle",
            "video-translate",
            "grok-video",
            "digital-human",
            "flux3-video",
            "veo-frames",
            "super-resolution",
            "sound-clone",
            "sound-clone-audio",
            "image",
        ],
        default="video",
    )
    p.add_argument("--model", default="sora2-12s")
    p.add_argument("--duration", type=int, default=12)
    p.add_argument("--orientation", choices=["landscape", "portrait"])
    p.add_argument("--aspect-ratio", dest="aspect_ratio")
    p.add_argument("--resolution", default="720p")
    p.add_argument("--ratio", default="auto")
    p.add_argument("--quality", default="low")
    p.add_argument("--size", help="MiniMax H3 output size, e.g. 2560x1440")
    p.add_argument(
        "--face-processing",
        dest="face_processing",
        type=_parse_optional_bool,
        default=None,
        help="Seedance 2.0 933 face processing (true/false)",
    )
    p.add_argument(
        "--generate-audio",
        dest="generate_audio",
        type=_parse_optional_bool,
        default=None,
        help="Generate audio where supported (true/false)",
    )
    p.add_argument(
        "--reference-mode",
        dest="reference_mode",
        choices=["image", "frame"],
        default=None,
        help="Seedance 2.0 933 reference mode",
    )
    p.add_argument("--image", action="append", help="Reference image URL (repeatable)")
    p.add_argument("--image-url", dest="image_url", help="Flux 3 i2v image URL")
    p.add_argument("--video", action="append", help="Reference video URL (Seedance / Seedance 2.5 / Seedance 2.0 933 / GZ 2.0)")
    p.add_argument(
        "--video-url",
        dest="video_url",
        help="Source video URL (remove-subtitle / video-translate / digital-human / super-resolution / flux3 extend)",
    )
    p.add_argument("--audio-url", dest="audio_url", help="Drive audio URL (digital-human)")
    p.add_argument("--draft-cache-url", dest="draft_cache_url", help="Flux 3 enhance draft_cache_url")
    p.add_argument("--keyframes-json", dest="keyframes_json", help="Flux 3 keyframes JSON")
    p.add_argument("--safety-tolerance", dest="safety_tolerance", type=int, default=None)
    p.add_argument("--model-version", dest="model_version", type=int, choices=[1, 2], default=None)
    p.add_argument("--side-face", dest="side_face", type=int, choices=[0, 1], default=None)
    p.add_argument("--tilted-face", dest="tilted_face", type=int, choices=[0, 1], default=None)
    p.add_argument("--file-url", dest="file_url", help="SoundClone source audio/video URL")
    p.add_argument("--content-text", dest="content_text", help="SoundClone script text")
    p.add_argument("--model-id", dest="model_id", help="SoundClone modelId from preview")
    p.add_argument("--sound-version", dest="sound_version", choices=["v1", "v2"], default=None)
    p.add_argument("--language", default=None, help="SoundClone language")
    p.add_argument("--emotion", default=None, help="SoundClone emotion")
    p.add_argument("--speed", type=float, default=None, help="SoundClone speed")
    p.add_argument("--vol", type=float, default=None, help="SoundClone volume")
    p.add_argument("--pitch", type=int, default=None, help="SoundClone pitch")
    p.add_argument(
        "--subtitle-enable",
        dest="subtitle_enable",
        type=_parse_optional_bool,
        default=None,
        help="SoundClone subtitle enable",
    )
    p.add_argument("--subtitle-type", dest="subtitle_type", choices=["word"], default=None)
    p.add_argument(
        "--output-language",
        dest="output_language",
        help="Target language for video-translate (enum or alias)",
    )
    p.add_argument(
        "--translate-audio-only",
        dest="translate_audio_only",
        type=_parse_optional_bool,
        default=None,
        help="video-translate: voice only (true/false)",
    )
    p.add_argument("--speaker-num", dest="speaker_num", type=int, default=None, help="video-translate speaker count")
    p.add_argument(
        "--enable-dynamic-duration",
        dest="enable_dynamic_duration",
        type=_parse_optional_bool,
        default=None,
        help="video-translate dynamic duration (true/false)",
    )
    p.add_argument(
        "--enable-caption",
        dest="enable_caption",
        type=_parse_optional_bool,
        default=None,
        help="video-translate generate SRT (true/false)",
    )
    p.add_argument("--srt-url", dest="srt_url", help="video-translate custom SRT URL")
    p.add_argument("--srt-role", dest="srt_role", choices=["input", "output"], help="video-translate SRT role")
    p.add_argument("--brand-glossary-id", dest="brand_glossary_id", help="video-translate brand glossary ID")
    p.add_argument("--audio", action="append", help="Reference audio URL (MiniMax / Seedance / Seedance 2.5 / Seedance 2.0 933 / GZ 2.0)")
    p.add_argument("--first-image", dest="first_image", help="First frame URL (Seedance / VEO / Flux3 / MiniMax / Kling)")
    p.add_argument("--last-image", dest="last_image", help="Last frame URL (Seedance / VEO / Flux3 / MiniMax / Kling)")
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
