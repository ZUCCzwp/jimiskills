# API reference (summary)

Full docs: https://docs.jimmyai.cn/llms.txt  
OpenAPI: https://docs.jimmyai.cn/zh/api-reference/openapi.json

Base URL: `https://www.jimmyai.cn`  
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
| model | yes | `Gemini-Omini`, `Omni-Flash-Ext`, `gemini-omni` |
| prompt | yes | text description |
| duration | no | default 6 seconds |
| resolution | no | `720p`, `1080p`, `4k` |
| aspect_ratio | no | e.g. `16:9`, `9:16` (overrides orientation) |
| orientation | no | `landscape` / `portrait` when aspect_ratio empty |
| image_urls / images | no | reference images |

Poll via same `GET /api/open-api/v1/videos/{taskId}`.

### VEO — create

`POST /api/open-api/v1/veo/videos` — see https://docs.jimmyai.cn/zh/api-reference/veo/create-video.md

`POST /api/open-api/v1/veo/frames` — first/last frame mode

### Seedance — create

`POST /api/open-api/v1/seedance/videos` — see https://docs.jimmyai.cn/zh/api-reference/seedance/create.md

Asset audit required for some inputs:
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
2. Use exponential backoff on `-1` errors
3. Sync image: client timeout ≥ 180 s
4. Async: poll every 5–15 s, cap total wait (e.g. 30 min)
5. Store API keys in env vars, never in source code
