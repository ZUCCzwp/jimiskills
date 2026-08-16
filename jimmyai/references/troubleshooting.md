# Troubleshooting

## code 20001 — auth failure

- Cause: missing, wrong, or expired API key.
- Fix: recreate key at https://api.viraltok.ai, set `JIMMYAI_API_KEY`, confirm no extra spaces.

## code 20002 — bad parameters

- Cause: invalid model, duration, or field combo.
- Fix: check model docs. Route1 `sora2-12s` requires `duration: 12`.

## code -1 — server error

- Cause: temporary upstream issue.
- Fix: retry with exponential backoff (5 s → 10 s → 20 s).

## Insufficient balance

- Cause: account not recharged or `available` balance too low.
- Fix: recharge at https://api.viraltok.ai (minimum ~$1).
- Check: `GET /api/open-api/v1/user/balance` or `python "$JIMMYAI_CLI" user-balance`.

## API key quota exhausted

- Cause: `total_quota` set on the key and `used_quota` reached the cap.
- Fix: raise quota in console or use another key.
- Check: `GET /api/open-api/v1/key/balance` or `python "$JIMMYAI_CLI" key-balance`.

## Sync image timeout

- Cause: client timeout too short; generation takes 30–120 s.
- Fix: set timeout ≥ 180 s (`--timeout 180` in CLI, or curl `--max-time 180`).

## Task stuck in queued / processing

- Cause: queue delay or heavy load.
- Fix: increase poll timeout; retry later; avoid burst concurrency.

## video_url / image_url expired

- Cause: URLs valid ~3 days only.
- Fix: download and store locally immediately after completion.

## sora2-12s duration error

- Cause: `duration` not equal to 12 on route1.
- Fix: always pass `--duration 12` for `sora2-12s`.

## File upload failed (unsupported format / too large)

- Cause: extension not in allowlist, or file > 100 MB.
- Fix: convert to a supported format (jpg/png/mp4/mp3, etc.) or compress; field name must be `file`.
- Endpoint: `POST /api/open-api/v1/files/upload` or `python "$JIMMYAI_CLI" upload-file --file PATH`.

## Large b64_json response

- Cause: sync image returns multi-MB base64.
- Fix: use `--output file.png` in CLI; ensure gateway/proxy allows large bodies.

## JIMMYAI_API_KEY not set

- Cause: env var missing in shell or Codex session.
- Fix: `export JIMMYAI_API_KEY="..."` in the same shell before running CLI.

## Network blocked in Codex

- Cause: sandbox has no outbound network.
- Fix: see `references/codex-network.md`.

## Seedance asset rejected

- Cause: reference assets need platform audit first.
- Fix: submit via assets audit endpoint; poll audit status before video create.

## Seedance SP economy (`seedance2.0-sp`, `seedance2.0-fast-sp`)

- Use `POST /api/open-api/v1/seedance/videos` with `"model": "seedance2.0-sp"` or `"seedance2.0-fast-sp"`.
- `resolution` must be `720p` (default) or `1080p` — **`480p` is not supported** on SP economy (use Mini / Mini 特价版 for `480p`).
- `duration` must be 4–15 seconds.
- `seedance2.0-fast-sp` does not support `reference_videos`.
- Reference audio requires paired images, videos, or frame refs.
- Upload assets via `POST /api/open-api/v1/seedance/sp/assets/upload`, then reference `asset://{asset_id}`.
- Poll with `GET /api/open-api/v1/videos/{taskId}` like other async video tasks.
- Docs: https://docs.viraltok.ai/zh/api-reference/seedance/sp/create.md

## Seedance Mini (`seedance2.0-mini`)

- Use `POST /api/open-api/v1/seedance/videos` with `"model": "seedance2.0-mini"` or `"seedance2.0-mini-video"` plus `resolution` (`480p` / `720p` / `1080p`).
- **Billing model names** are also valid as `model`: e.g. `seedance2.0-mini-720p`, `seedance2.0-mini-1080p-video` — resolution is parsed from `model`; you can omit `resolution`.
- This alias applies only to **Mini standard / video-ref**, not `seedance2.0-mini-sp`.
- If you see「配置不存在」with `seedance2.0-mini-720p`, upgrade the API server or use `model: seedance2.0-mini` + `resolution: 720p`.
- Docs: https://docs.viraltok.ai/zh/api-reference/seedance/mini/create.md

## Seedance Mini 特价版 (`seedance2.0-mini-sp`)

- Use `POST /api/open-api/v1/seedance/videos` with `"model": "seedance2.0-mini-sp"` — there is no separate `/seedance/mini-sp/videos` path.
- `resolution` must be `480p` or `720p` (default `720p`).
- `duration` must be 4–15 seconds.
- Poll with `GET /api/open-api/v1/videos/{taskId}` like other async video tasks.

## MiniMax H3 (`minimax-h3`)

- Use `POST /api/open-api/v1/minimax/videos` with `"model": "minimax-h3"`.
- Billing is `per_task` (flat per request); `duration` does not change cost.
- `duration` must be 5–15 seconds (default 5).
- `aspect_ratio`: `16:9` / `9:16` / `1:1` / `4:3` / `3:4` / `21:9`.
- `reference_images` max 5; `reference_audios` max 1; optional `first_image` / `last_image`.
- Poll with `GET /api/open-api/v1/videos/{taskId}`.
- Docs: https://docs.viraltok.ai/zh/api-reference/minimax/create.md

## Kling O3 (`kling-o3`)

- Use `POST /api/open-api/v1/kling/videos` with `"model": "kling-o3"`.
- Billing is `per_task` (flat per request); `duration` does not change cost.
- Billing key follows `resolution` (`kling-o3-720p` / `kling-o3-1080p`), falling back to `kling-o3`.
- `duration` must be 3–15 seconds (default 6).
- `aspect_ratio`: `16:9` / `9:16` / `1:1` (default `16:9`).
- `resolution`: `720p` / `1080p` (default `720p`).
- `reference_images` max 3; optional `first_image` / `last_image`; `generate_audio` default `false`.
- Poll with `GET /api/open-api/v1/videos/{taskId}`.
- Docs: https://docs.viraltok.ai/zh/api-reference/kling/create.md

## Seedance 2.5 (`seedance-2.5` / `seedance-2.5-sp` / `seedance2.5-gz`)

- Use `POST /api/open-api/v1/seedance25/videos` with `"model": "seedance-2.5"`, `"seedance-2.5-sp"`, or `"seedance2.5-gz"`.
- **Do not** use `/api/open-api/v1/seedance/videos` for these models — that endpoint is Seedance 2.0 (including Full/Manxue). Wrong path routes onto the Full line.
- Standard billing is `per_second` by resolution (`seedance-2.5-480p` / `seedance-2.5-720p`; `unit_price × duration`). Request `model` stays `seedance-2.5`; billing key follows `resolution`.
- SP billing is `per_second` at fixed **0.5**/s (`seedance-2.5-sp`; `0.5 × duration`).
- GZ is precharged `per_second` by resolution (`seedance2.5-gz-480p` / `seedance2.5-gz-720p`). With reference videos the billing model becomes `seedance2.5-gz-video-*` and precharged seconds = output + ref video duration. `duration=-1` precharges 30s. After success, usage is settled to actual cost (one refund or extra-charge row).
- Standard: `duration` 4–30 s (default 4); `resolution` `480p` / `720p` (default `480p`).
- SP: `duration` 4–30 s; `resolution` **720p only**; optional `first_image` / `last_image` (cannot combine with `reference_images` / `images`).
- GZ: `duration` 4–30 s or `-1` (default 5); `resolution` `480p` / `720p` (default `720p`); aspect ratios include `adaptive`; optional first/last frames.
- `aspect_ratio`: `16:9` / `9:16` / `1:1` (default `9:16`). GZ also accepts `4:3` / `3:4` / `21:9` / `adaptive`.
- `reference_images` max 30; `reference_videos` max 10 (each and total ≤ **30.2** s); `reference_audios` max 10 (each ≤ **30** s).
- Poll with `GET /api/open-api/v1/videos/{taskId}`.
- Docs: https://docs.viraltok.ai/zh/api-reference/seedance/25/create.md · GZ: https://docs.viraltok.ai/zh/api-reference/seedance/25/create-gz.md

## Seedance 2.0 933 (`seedance2.0-933`)

- Use `POST /api/open-api/v1/seedance/videos` with `"model": "seedance2.0-933"`.
- Billing is `per_second` by resolution (`seedance2.0-933-480p` / `seedance2.0-933-720p` / `seedance2.0-933-1080p`; `unit_price × duration`).
- Request `model` stays `seedance2.0-933`; billing key follows `resolution`.
- `duration` must be 4–15 seconds (default 4).
- `aspect_ratio`: `21:9` / `16:9` / `4:3` / `1:1` / `3:4` / `9:16` (default `16:9`).
- `resolution`: `480p` / `720p` / `1080p` (default `480p`).
- `face_processing` default `true`; `generate_audio` default `false`; `reference_mode` `image` / `frame` (default `image`).
- `reference_images` max 9; `reference_videos` max 3; `reference_audios` max 3.
- Poll with `GET /api/open-api/v1/videos/{taskId}`.
- Docs: https://docs.viraltok.ai/zh/api-reference/seedance/20933/create.md

## Seedance 2.0 GZ (`seedance2.0-gz*`)

- Use `POST /api/open-api/v1/seedance/videos` with a `model` starting with `seedance2.0-gz` (e.g. `seedance2.0-gz-720p`, `seedance2.0-gz-fast`, `seedance2.0-gz-mini`).
- Billing is `per_million_tokens` (`completion_tokens / 1,000,000 × unit_price`).
- Standard resolution `480p` / `720p` / `1080p`; Fast / Mini `480p` / `720p` only.
- `duration` must be 4–15 seconds (default 5).
- `aspect_ratio`: `16:9` / `9:16` / `1:1` / `4:3` / `3:4` / `21:9` / `adaptive` (default `16:9`).
- `images` max 9; `reference_videos` max 3; `reference_audios` max 3 (audio requires image or video refs).
- Public HTTPS refs are auto-submitted for Seedance 2.0 asset review (or pass `asset://` / `assetId://`). First/last frame cannot mix with multimodal refs.
- Result `video_url` is a **direct upstream media link** (not copied to our storage) — download promptly.
- Poll with `GET /api/open-api/v1/videos/{taskId}`.
- Docs: https://docs.viraltok.ai/zh/api-reference/seedance/gz720/create.md

## Seedance 933 720p (`sd2-933-720p`)

- Use `POST /api/open-api/v1/seedance/videos` with `"model": "sd2-933-720p"`.
- Billing is `per_second` at **0.0479**/s (`0.0479 × duration`).
- Resolution is **fixed 720p**.
- `duration` must be 4–15 seconds (default 5).
- `aspect_ratio`: `16:9` / `9:16` / `1:1` / `4:3` / `3:4` (default `16:9`).
- `images` max 9; `reference_videos` max 3; `reference_audios` max 3 (audio requires image or video refs).
- `reference_mode`: `frame` / `media`; `generate_audio` default `true`.
- Poll with `GET /api/open-api/v1/videos/{taskId}`.
- Docs: https://docs.viraltok.ai/zh/api-reference/seedance/933720/create.md

## video_url is a relative path (custom OSS)

- Cause: older API responses could return OSS object keys like `seedance/mini-sp/video/xxx.mp4` instead of a full URL.
- Fix: ensure you query the latest API; completed tasks should return a full `https://` URL (signed when OSS is private). Download within 3 days.

## More help

- Docs: https://docs.viraltok.ai/llms.txt
- Email: 2114272829@qq.com
- Online chat on https://api.viraltok.ai
