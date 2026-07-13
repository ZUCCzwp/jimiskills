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

## Balance endpoints

### User account balance

`GET /api/open-api/v1/user/balance`

Returns JimiCoin balance for the user who owns the API key. OpenAPI usage is billed against this account.

| Field | Description |
|-------|-------------|
| `balance` | Total balance (includes active subscription credits) |
| `used_coin` | Cumulative consumption |
| `available` | `balance` - `used_coin` |

### API key quota balance

`GET /api/open-api/v1/key/balance`

Returns per-key quota (separate from account balance).

| Field | Description |
|-------|-------------|
| `name` | Key display name |
| `total_quota` | Total quota; `0` = unlimited |
| `used_quota` | Quota used |
| `available_quota` | Remaining quota |
| `unlimited` | `true` when no quota cap |

Docs: https://docs.jimmyai.cn/zh/api-reference/common/user-balance.md

## File upload

`POST /api/open-api/v1/files/upload` (multipart/form-data)

Upload a local image, video, or audio file; returns a URL for use in `images`, `reference_videos`, `reference_audios`, image edits, etc.

| Item | Notes |
|------|-------|
| Field name | `file` (required) |
| Max size | 100 MB |
| Auth | `Authorization: Bearer <JIMMYAI_API_KEY>` |

**Supported formats**

| Type | Extensions |
|------|------------|
| Images | `.jpg` `.jpeg` `.png` `.gif` `.webp` `.bmp` `.svg` |
| Video | `.mp4` `.mov` `.avi` `.webm` `.mkv` `.m4v` `.flv` |
| Audio | `.mp3` `.wav` `.aac` `.m4a` `.flac` `.ogg` |

**Response** (`code: 20000`):

```json
{
  "code": 20000,
  "msg": "ok",
  "data": {
    "url": "https://cdn.example.com/uploads/photo.jpg",
    "filename": "photo.jpg",
    "size": 102400,
    "mime_type": "image/jpeg"
  }
}
```

`data.url` may be a signed URL when object storage is private. Copy URLs within ~3 days.

Docs: https://docs.jimmyai.cn/zh/api-reference/common/files-upload.mdx

```bash
curl --request POST \
  --url https://api.viraltok.ai/api/open-api/v1/files/upload \
  --header "Authorization: Bearer $JIMMYAI_API_KEY" \
  --form "file=@/path/to/photo.jpg"
```

CLI: `python "$JIMMYAI_CLI" upload-file --file /path/to/photo.jpg`

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
| SP economy | `seedance2.0-sp`, `seedance2.0-fast-sp` | per second × resolution | 4–15 s | `resolution`: `720p` / `1080p` only (**not `480p`**); see SP doc |
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
| resolution | no | SP economy: `720p` (default) or `1080p` only; Mini 特价版: `480p` or `720p`; Mini: `480p` / `720p` / `1080p` |
| ratio | no | Fast I2V / MD: `16:9`, `9:16`, `1:1` |
| images | no | reference image URLs |
| first_image / last_image | no | frame mode; mutually exclusive with `images` |
| reference_videos | no | not supported on `seedance2.0-fast-i2v` |
| reference_audios | no | not supported on MD / Fast I2V |

**SP economy** (`seedance2.0-sp`, `seedance2.0-fast-sp`): unified `POST /api/open-api/v1/seedance/videos`. Poll via `GET /api/open-api/v1/videos/{taskId}`. `resolution` must be `720p` (default) or `1080p` — **`480p` is not supported**. Duration 4–15 s. Supports `images`, `first_image` / `last_image`, `reference_videos` (not on `seedance2.0-fast-sp`), and `reference_audios` (audio requires image/video/frame refs). Materials: public `https://` URLs or `asset://` after `POST /api/open-api/v1/seedance/sp/assets/upload`. Detail: https://docs.jimmyai.cn/zh/api-reference/seedance/sp/create.md

```json
{
  "model": "seedance2.0-sp",
  "prompt": "Rainy street at night, girl turns and smiles, cinematic push-in",
  "duration": 8,
  "resolution": "720p",
  "ratio": "16:9",
  "first_image": "https://example.com/start.png"
}
```

Catalog billing names (per second): `sd2_sp_720p`, `sd2_sp_1080p`, `sd2_sp_2k`, `sd2_sp_4k`, `sd2_sp_fast_780p`, `sd2_sp_video_*` — request still uses `seedance2.0-sp` + `resolution`.

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

OpenAI-compatible. Default returns `data.data[0].url` (image uploaded to storage). Set `response_format=b64_json` to return base64 instead. Timeout ≥ 180 s.

| Field | Required | Notes |
|-------|----------|-------|
| prompt | yes | |
| model | no | default `gpt-image-2` |
| size | no | default `1024x1024` |
| quality | no | `low`, `medium`, `high`, `auto` |
| n | no | max 1 |
| response_format | no | `url` (default) or `b64_json` |

### Sync — edit

`POST /api/open-api/v1/images/edits` (multipart/form-data)

Same `response_format` as generations: default `url`, optional `b64_json`. Form field name: `response_format`.

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
