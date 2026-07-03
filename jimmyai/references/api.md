# API reference (summary)

Full docs: https://docs.jimmyai.cn/llms.txt  
OpenAPI: https://docs.jimmyai.cn/zh/api-reference/openapi.json

Base URL: `https://api.viraltok.ai`  
Auth: `Authorization: Bearer <JIMMYAI_API_KEY>`

## Response codes

| code | meaning |
|------|---------|
| 20000 | success |
| 20001 | auth failure — check API key |
| 20002 | bad request — check params |
| -1 | server error — retry later |

## Video endpoints

### Sora — create

`POST /api/open-api/v1/videos`

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | e.g. `sora2-12s`, `sora2-gz-stable`, `openai-sora-2` |
| prompt | yes | text description |
| duration | yes | route1 `sora2-12s` must be `12` |
| orientation | no | `landscape` (16:9) or `portrait` (9:16) |
| images | no | reference image URL array (image-to-video) |

### Sora — query

`GET /api/open-api/v1/videos/{taskId}`

Result fields: `data.status`, `data.progress`, `data.result.video_url`, `data.error_message`

### Gemini Omni — create

`POST /api/open-api/v1/gemini/omni/videos`

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `Gemini-Omini`, `Omni-Flash-Ext`, `gemini-omni`, or `omni-10s` (fixed 10s / 720p, up to 7 refs) |
| prompt | yes | text description |
| duration | no | default 6 seconds |
| resolution | no | `720p`, `1080p`, `4k` |
| aspect_ratio | no | e.g. `16:9`, `9:16` (overrides orientation) |
| orientation | no | `landscape` / `portrait` when aspect_ratio empty |
| image_urls / images | no | reference images; `omni-10s` supports up to 7 |

Poll via same `GET /api/open-api/v1/videos/{taskId}`.

### VEO — create

`POST /api/open-api/v1/veo/videos` — see https://docs.jimmyai.cn/zh/api-reference/veo/create-video.md

`POST /api/open-api/v1/veo/frames` — first/last frame mode

### Seedance — create

`POST /api/open-api/v1/seedance/videos` — see https://docs.jimmyai.cn/zh/api-reference/seedance/create.md

Poll via `GET /api/open-api/v1/videos/{taskId}` (same as Sora / Gemini Omni).

| Route | `model` | Billing | Duration | Notes |
|-------|---------|---------|----------|-------|
| Manxue | `sd2_mx_*`, `sd2_mx_fast_*`, `sd2_mx_video_*` | per second | 4–12 s | assets need `asset://` audit |
| SP economy | `seedance2.0-sp`, `seedance2.0-fast-sp` | per second × resolution | 4–15 s | see SP doc |
| SP official | `seedance2.0-of-sp`, `seedance2.0-of-fast-sp` | per second × resolution | 4–15 s | see SP doc |
| Mini | `seedance2.0-mini`, `seedance2.0-mini-video` | per second × resolution | 4–15 s | |
| **Mini 特价版** | `seedance2.0-mini-sp` | per second × resolution | 4–15 s | `480p` / `720p` only; same endpoint as other Seedance routes |
| MD standard | `seedance2.0-md` | per task | 4–15 s | direct `https://` URLs; max 4 images |
| MD fast | `seedance2.0-fast-md` | per task | 4–15 s | same as MD |
| **Fast I2V** | `seedance2.0-fast-i2v` | per task | 1–15 s | image refs only, max 9; no video/audio refs |
| STD | `seedance2.0-std` | per task | 4–15 s | max 9 images, max 3 audio refs |

Fast I2V detail: https://docs.jimmyai.cn/zh/api-reference/seedance/md/fast-i2v.md

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | e.g. `seedance2.0-fast-i2v`, `seedance2.0-mini-sp` (request model = billing model) |
| prompt | yes | max 5000 chars for MD / Fast I2V |
| duration | yes | Fast I2V: 1–15; MD / Mini 特价版: 4–15 |
| resolution | no | Mini 特价版: `480p` or `720p` (default `720p`); SP / Mini: affects billing |
| ratio | no | Fast I2V / MD: `16:9`, `9:16`, `1:1` |
| images | no | reference image URLs |
| first_image / last_image | no | frame mode; mutually exclusive with `images` |
| reference_videos | no | not supported on `seedance2.0-fast-i2v` |
| reference_audios | no | not supported on MD / Fast I2V |

**Mini 特价版** (`seedance2.0-mini-sp`): use `POST /api/open-api/v1/seedance/videos` (not a separate mini-sp path). Poll via `GET /api/open-api/v1/videos/{taskId}`. Supports `images`, `first_image` / `last_image`, `reference_videos`, and `reference_audios` (audio requires image or video refs).

```json
{
  "model": "seedance2.0-mini-sp",
  "prompt": "A cat walking in a garden, cinematic",
  "duration": 8,
  "resolution": "720p",
  "ratio": "16:9",
  "images": ["https://example.com/ref.jpg"]
}
```

Asset audit (Manxue routes only):
- `POST /api/open-api/v1/seedance/assets/audit`
- `GET /api/open-api/v1/seedance/assets/status`

## Image endpoints

### Async — create

`POST /api/open-api/v1/images`

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `gpt-image-2`, `nano-banana`, `nano-banana-2`, `nano-banana-pro` |
| prompt | yes | text description |
| ratio | no | `auto`, `1:1`, `16:9`, `9:16`, etc. |
| resolution | no | `1k`, `2k`, `4k` |
| quality | no | `low`, `medium`, `high` (gpt-image-2) |
| images | no | reference URLs or base64 |

### Async — query

`GET /api/open-api/v1/images/{taskId}`

### Sync — text-to-image

`POST /api/open-api/v1/images/generations`

OpenAI-compatible. Returns image in `data.data[0].b64_json` immediately. Timeout ≥ 180 s.

| Field | Required | Notes |
|-------|----------|-------|
| prompt | yes | |
| model | no | default `gpt-image-2` |
| size | no | default `1024x1024` |
| quality | no | `low`, `medium`, `high`, `auto` |
| n | no | max 1 |

### Sync — edit

`POST /api/open-api/v1/images/edits` (multipart/form-data)

### Image understanding

`POST /api/open-api/v1/images/understand` — Gemini-powered analysis

## Model route notes (Sora)

| route | models | duration |
|-------|--------|----------|
| route1 | `sora2-12s` | must be 12 |
| route3 | `sora2-gz-stable`, `sora2-gz-sp` | per model |
| route6 | `openai-sora-2`, etc. | per model |

Route is configured in the开放平台 per model.

## Best practices

1. Copy `video_url` / `image_url` within 3 days
2. `video_url` is always a full HTTPS URL (signed when OSS is private); custom OSS users get URLs on their configured domain
3. Use exponential backoff on `-1` errors
3. Sync image: client timeout ≥ 180 s
4. Async: poll every 5–15 s, cap total wait (e.g. 30 min)
5. Store API keys in env vars, never in source code
