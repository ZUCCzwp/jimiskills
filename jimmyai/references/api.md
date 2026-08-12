# API reference (summary)

Full docs: https://docs.viraltok.ai/llms.txt  
OpenAPI: https://docs.viraltok.ai/zh/api-reference/openapi.json

Base URL: `https://api.viraltok.ai`  
Auth: `Authorization: Bearer <JIMMYAI_API_KEY>`

**Content boundary:** document only public OpenAPI models, fields, and billing. Do not name or link upstream channel vendors, private vendor portals, or internal routing mounts.

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

Docs: https://docs.viraltok.ai/zh/api-reference/common/user-balance.md

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

Docs: https://docs.viraltok.ai/zh/api-reference/common/files-upload.mdx

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

`POST /api/open-api/v1/veo/videos` — see https://docs.viraltok.ai/zh/api-reference/veo/create-video.md

`POST /api/open-api/v1/veo/frames` — first/last frame or reference-image mode. Docs: https://docs.viraltok.ai/zh/api-reference/veo/create-frames.md

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | Fast: `veo_3_1_fast` (or `veo_3_1_fast-4k`); Lite: `veo_3_1_lite` (**720p only**) |
| prompt | yes | text description |
| resolution | no | see billing table below |
| orientation | no | `landscape` / `portrait` |
| first_frame_url / last_frame_url | frames | first frame required in frame mode |
| images | reference | 1–3 reference images (mutually exclusive with frames) |

Billing is `per_task`. Fast vs Lite are product tiers (same endpoint):

| Request `model` | resolution | Billing model |
|-----------------|------------|---------------|
| `veo_3_1_fast` | `720p` / `1080p` (default `720p`) | `veo_3_1_fast` |
| `veo_3_1_fast` | `4k` | `veo_3_1_fast-4k` |
| `veo_3_1_lite` | `720p` only (default) | `veo_3_1_lite` |

Lite rejects `1080p` / `4k`. You may pass `veo_3_1_fast-4k` as `model` for Fast 4K billing.

### Seedance — create

`POST /api/open-api/v1/seedance/videos` — see https://docs.viraltok.ai/zh/api-reference/seedance/create.md

Poll via `GET /api/open-api/v1/videos/{taskId}` (same as Sora / Gemini Omni).

| Route | `model` | Billing | Duration | Notes |
|-------|---------|---------|----------|-------|
| Manxue | `sd2_mx_*`, `sd2_mx_fast_*`, `sd2_mx_video_*` | per second | 4–15 s | assets need `asset://` audit |
| SP economy | `seedance2.0-sp`, `seedance2.0-fast-sp` | per second × resolution | 4–15 s | `resolution`: `720p` / `1080p` only (**not `480p`**); see SP doc |
| SP official | `seedance2.0-of-sp`, `seedance2.0-of-fast-sp` | per second × resolution | 4–15 s | see SP doc |
| Mini | `seedance2.0-mini`, `seedance2.0-mini-video` | per second × resolution | 4–15 s | billing names `seedance2.0-mini-{resolution}` / `seedance2.0-mini-{resolution}-video` also accepted as `model` (omit `resolution`) |
| **Mini 特价版** | `seedance2.0-mini-sp` | per second × resolution | 4–15 s | `480p` / `720p` only; same endpoint as other Seedance routes |
| MD standard | `seedance2.0-md` | per task | 4–15 s | direct `https://` URLs; max 4 images |
| MD fast | `seedance2.0-fast-md` | per task | 4–15 s | same as MD |
| **Fast I2V** | `seedance2.0-fast-i2v` | per task | 1–15 s | image refs only, max 9; no video/audio refs |
| STD | `seedance2.0-std` | per task | 4–15 s | max 9 images, max 3 audio refs |
| **GZ 720p** | `seedance2.0-gz-720p` | per second | 4–15 s | fixed 720p; max 9 images / 3 videos / 3 audios; audio requires image or video refs; direct result media URL |
| **933 720p** | `sd2-933-720p` | per second **0.0479**/s | 4–15 s | fixed 720p; max 9 images / 3 videos / 3 audios; `reference_mode` frame/media; `generate_audio` default true |

Fast I2V detail: https://docs.viraltok.ai/zh/api-reference/seedance/md/fast-i2v.md
GZ 720p detail: https://docs.viraltok.ai/zh/api-reference/seedance/gz720/create.md
933 720p detail: https://docs.viraltok.ai/zh/api-reference/seedance/933720/create.md

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

**SP economy** (`seedance2.0-sp`, `seedance2.0-fast-sp`): unified `POST /api/open-api/v1/seedance/videos`. Poll via `GET /api/open-api/v1/videos/{taskId}`. `resolution` must be `720p` (default) or `1080p` — **`480p` is not supported**. Duration 4–15 s. Supports `images`, `first_image` / `last_image`, `reference_videos` (not on `seedance2.0-fast-sp`), and `reference_audios` (audio requires image/video/frame refs). Materials: public `https://` URLs or `asset://` after `POST /api/open-api/v1/seedance/sp/assets/upload`. Detail: https://docs.viraltok.ai/zh/api-reference/seedance/sp/create.md

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

**Mini** (`seedance2.0-mini`, `seedance2.0-mini-video`): same `POST /api/open-api/v1/seedance/videos`. Either pass base `model` + `resolution`, or pass the **billing model name** directly (e.g. `seedance2.0-mini-720p`, `seedance2.0-mini-720p-video`) and omit `resolution`. Does **not** apply to `seedance2.0-mini-sp`. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/mini/create.md

```json
{
  "model": "seedance2.0-mini-720p",
  "prompt": "Subject turns slowly, cinematic lighting",
  "duration": 6,
  "ratio": "9:16",
  "images": ["https://example.com/ref.jpg"]
}
```

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
| model | yes | `gpt-image-2`, `nano-banana`, `nano-banana-2`, `nano-banana-pro`, `doubao-seedream-5-0-pro`, `grok-imagine-image`, `grok-imagine-image-2` |
| prompt | yes | text description |
| ratio | no | `auto`, `1:1`, `16:9`, `9:16`, etc. |
| resolution | no | `1k`, `2k`, `4k` (Seedream 5.0 Pro / Grok Imagine Image: `1k`/`2k` only) |
| quality | no | `low`, `medium`, `high` (gpt-image-2) |
| images | no | reference URLs or base64 (Seedream: max 10; Grok Imagine Image edit: max 3; per image limits vary by model) |

**Seedream 5.0 Pro** (`doubao-seedream-5-0-pro`): async `POST /api/open-api/v1/images`, poll `GET /api/open-api/v1/images/{taskId}`. Billing = resolution base (`doubao-seedream-5-0-pro-1k` / `-2k`) + `max(0, refs - 1) × doubao-seedream-5-0-pro-ref` (first reference free). Resolution `1k`/`2k` (default `2k`). Ratios: `1:1`, `4:3`, `3:4`, `16:9`, `9:16`, `3:2`, `2:3`, `21:9`, `auto`. Docs: https://docs.viraltok.ai/zh/api-reference/images/seedream-5-0-pro/create.md

**Grok Imagine Image** (`grok-imagine-image`): async `POST /api/open-api/v1/images`, poll `GET /api/open-api/v1/images/{taskId}`. Billing = unit price × `n` (`1`–`4`). Resolution `1k`/`2k` (default `1k`). `output_format`: `jpeg`/`png`/`webp`. With `images` (max 3) → edit mode (`ratio` default `auto`). Result: `image_url` + `image_urls`. Docs: https://docs.viraltok.ai/zh/api-reference/images/grok-imagine-image/create.md

**Grok Imagine Image 2.0** (`grok-imagine-image-2`): Quality tier. Same fields; billing by resolution (`grok-imagine-image-2-1k` / `-2k`) × `n`. Docs: https://docs.viraltok.ai/zh/api-reference/images/grok-imagine-image-2/create.md

```json
{
  "model": "doubao-seedream-5-0-pro",
  "prompt": "Cyberpunk city at night, neon on wet streets",
  "ratio": "16:9",
  "resolution": "2k"
}
```

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

### Sync — remove background

`POST /api/open-api/v1/images/remove-bg`

Synchronous. Charges immediately on success (billing model `viraltok-remove-bg`, per-task). Default returns `data.b64_json`. Pass `response_format=url` to get `data.image_url` instead. Timeout ≥ 180 s. Docs: https://docs.viraltok.ai/zh/api-reference/images/remove-bg.md

| Field | Required | Notes |
|-------|----------|-------|
| image_url | yes | public source image URL |
| model | no | `general_light` / `general_light_2k` (default) / `general_heavy` / `matting` / `portrait` / `general_dynamic` |
| operating_resolution | no | `1024x1024` / `2048x2048` (default) / `2304x2304` (`general_dynamic` only) |
| output_format | no | `png` (default) / `webp` / `gif` |
| refine_foreground | no | default `true` |
| response_format | no | `b64_json` (default) or `url` |

```json
{
  "image_url": "https://example.com/photo.png",
  "model": "general_light_2k",
  "operating_resolution": "2048x2048",
  "output_format": "png",
  "refine_foreground": true,
  "response_format": "b64_json"
}
```

## Tools — video super-resolution

`POST /api/open-api/v1/super-resolution/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `superResolution-{720p\|1080p\|2k\|4k}-{lowfps\|highfps}` (`lowfps`=30FPS, `highfps`=120FPS) |
| video_url | yes | public source video URL |

Billing: `per_second`, duration probed from `video_url` and **ceiled** (min 1s). Docs: https://docs.viraltok.ai/zh/api-reference/super-resolution/create.md

```json
{
  "model": "superResolution-1080p-lowfps",
  "video_url": "https://example.com/input-low-resolution.mp4"
}
```

## Tools — remove video subtitles

`POST /api/open-api/v1/remove-subtitle/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | no | `video_remove_subtitle` (default) |
| video_url | yes | public source video URL; keep reachable while the task runs |

Billing: `per_second`, duration probed from `video_url` and **ceiled** (min 1s). Docs: https://docs.viraltok.ai/zh/api-reference/remove-subtitle/create.md

```json
{
  "model": "video_remove_subtitle",
  "video_url": "https://example.com/input.mp4"
}
```

## MiniMax H3 video

`POST /api/open-api/v1/minimax/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `minimax-h3` or `minimax-h3-gz` (separate billing; same endpoint) |
| prompt | yes | 1–2000 chars |
| duration | no | 5–15, default `5` |
| aspect_ratio / ratio | no | `16:9` / `9:16` / `1:1` / `4:3` / `3:4` / `21:9`, default `16:9` |
| size | no | `2560x1440` / `1440x2560` / `1440x1440` / `1920x1440` / `1440x1920` / `3360x1440` |
| reference_images / images | no | max **5** public URLs |
| reference_videos / videos | no | `minimax-h3-gz` only, max **3**; mutually exclusive with first/last frames |
| reference_audios | no | max **1** public URL; on `minimax-h3-gz` must pair with an image or video |
| first_image / last_image | no | optional first/last frame URL |
| resolution | no | `minimax-h3-gz` only: `768P` (default) or `2K` |

Billing:

- No reference videos: `per_task` via `minimax-h3-gz-768p` / `minimax-h3-gz-2k`. `duration` does not affect cost.
- With `reference_videos`: `per_second` via **separate** `minimax-h3-gz-video-768p` / `minimax-h3-gz-video-2k`. Cost = unit_price × (rounded reference-video seconds + `duration`).

Docs: https://docs.viraltok.ai/zh/api-reference/minimax/create.md · GZ: https://docs.viraltok.ai/zh/api-reference/minimax/create-gz.md

```json
{
  "model": "minimax-h3",
  "prompt": "A cinematic product shot with natural lighting",
  "duration": 5,
  "aspect_ratio": "16:9",
  "size": "2560x1440",
  "reference_images": ["https://example.com/reference.png"],
  "reference_audios": ["https://example.com/reference.mp3"]
}
```

## Kling O3 video

`POST /api/open-api/v1/kling/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `kling-o3` (aliases `klingo3` / `kling_o3` / `KlingO3` normalize) |
| prompt | yes | 1–2000 chars |
| duration | no | 3–15, default `6` |
| aspect_ratio / ratio | no | `16:9` / `9:16` / `1:1`, default `16:9` |
| resolution | no | `720p` / `1080p`, default `720p` |
| reference_images / images | no | max **3** public URLs |
| first_image / last_image | no | optional first/last frame URL |
| generate_audio | no | default `false` |
| reference_mode | no | optional string |

Billing: `per_task`. Request `model` stays `kling-o3`. Billing key follows resolution (`kling-o3-720p` / `kling-o3-1080p`), falling back to `kling-o3`. `duration` does not affect cost. Docs: https://docs.viraltok.ai/zh/api-reference/kling/create.md

```json
{
  "model": "kling-o3",
  "prompt": "A cinematic product shot with natural lighting",
  "duration": 6,
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "reference_images": ["https://example.com/reference.png"],
  "generate_audio": false
}
```

## Seedance 2.5 video

`POST /api/open-api/v1/seedance25/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `seedance-2.5` (aliases `seedance2.5` / `seedance_2.5` / `seedance25`) or `seedance-2.5-sp` |
| prompt | yes | 1–5000 chars |
| duration | no | Standard / SP 4–30 (default `4`) |
| aspect_ratio / ratio | no | `16:9` / `9:16` / `1:1`, default `9:16` |
| resolution | no | Standard `480p` / `720p` (default `480p`); SP **720p only** |
| first_image / last_image | no | **SP only**; mutually exclusive with `reference_images` / `images` |
| reference_images / images | no | max **30** public URLs |
| reference_videos / videos | no | max **10**; each and total ≤ **30.2** s |
| reference_audios / audios | no | max **10**; each ≤ **30** s |

Billing:

- `seedance-2.5`: `per_second` by resolution (`seedance-2.5-480p` / `seedance-2.5-720p`; `unit_price × duration`). Request `model` stays `seedance-2.5`.
- `seedance-2.5-sp`: `per_second` fixed **0.5**/s (`seedance-2.5-sp`; `0.5 × duration`).

Docs: https://docs.viraltok.ai/zh/api-reference/seedance/25/create.md

Standard:

```json
{
  "model": "seedance-2.5",
  "prompt": "A cinematic product shot with natural lighting",
  "duration": 4,
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "reference_images": ["https://example.com/reference.png"],
  "reference_audios": ["https://example.com/reference.mp3"]
}
```

SP:

```json
{
  "model": "seedance-2.5-sp",
  "prompt": "A cinematic product shot with natural lighting",
  "duration": 5,
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "first_image": "https://example.com/start.png",
  "last_image": "https://example.com/end.png"
}
```

## Flux 3 video

`POST /api/open-api/v1/flux3/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | Only: `flux-3-draft` / `flux-3-i2v-draft` / `flux-3-flf-draft` / `flux-3-keyframes-draft` / `flux-3-extend-draft` / `flux-3-enhance` |
| prompt | usually | 1–5000 chars; **not** required for `flux-3-enhance` |
| duration | no | 5–20, default `5` (pass same duration when enhancing) |
| aspect_ratio / ratio | no | `auto` / `21:9` / `2:1` / `16:9` / `4:3` / `1:1` / `3:4` / `9:16` |
| image_url | i2v | required for `flux-3-i2v-draft` |
| start_image_url / end_image_url | flf | required for `flux-3-flf-draft` |
| keyframes | keyframes | required for `flux-3-keyframes-draft` (max 10) |
| video_url | extend | required for `flux-3-extend-draft` |
| draft_cache_url | enhance | required for `flux-3-enhance` (from draft task `result.draft_cache_url`) |

Do **not** send `resolution`. Drafts are fixed **720p**; enhance is fixed **1080p**. Billing is `per_second` and the billing model equals the request `model`.

Docs: https://docs.viraltok.ai/zh/api-reference/flux3/create.md


## Seedance 2.0 933 video

`POST /api/open-api/v1/seedance/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `seedance2.0-933` (aliases `seedance2_0_933` / `seedance20933` normalize) |
| prompt | yes | 1–5000 chars |
| duration | no | 4–15, default `4` |
| aspect_ratio / ratio | no | `21:9` / `16:9` / `4:3` / `1:1` / `3:4` / `9:16`, default `16:9` |
| resolution | no | `480p` / `720p` / `1080p`, default `480p` |
| face_processing | no | default `true` |
| generate_audio | no | default `false` |
| reference_mode | no | `image` / `frame`, default `image` |
| reference_images / images | no | max **9** public URLs |
| reference_videos / videos | no | max **3** public URLs |
| reference_audios / audios | no | max **3** public URLs |

Billing: `per_second` by resolution (`seedance2.0-933-480p` / `seedance2.0-933-720p` / `seedance2.0-933-1080p`; `unit_price × duration`). Request `model` stays `seedance2.0-933`. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/20933/create.md

```json
{
  "model": "seedance2.0-933",
  "prompt": "A cinematic product shot with natural lighting",
  "duration": 4,
  "aspect_ratio": "16:9",
  "resolution": "720p",
  "face_processing": true,
  "generate_audio": false,
  "reference_mode": "image",
  "reference_images": ["https://example.com/reference.png"],
  "reference_videos": ["https://example.com/reference.mp4"],
  "reference_audios": ["https://example.com/reference.mp3"]
}
```

## Seedance 2.0 GZ 720p video

`POST /api/open-api/v1/seedance/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `seedance2.0-gz-720p` (aliases `seedance2.0-gz720p` / `seedance20-gz-720p` normalize) |
| prompt | yes | 1–5000 chars |
| duration | no | 4–15, default `5` |
| aspect_ratio / ratio | no | `21:9` / `16:9` / `4:3` / `1:1` / `3:4` / `9:16`, default `16:9` |
| images / reference_images | no | max **9** public URLs or `asset://` |
| videos / reference_videos | no | max **3** public URLs |
| audios / reference_audios | no | max **3**; must pair with image or video refs |

Resolution is **fixed 720p**. Billing: `per_second` (`seedance2.0-gz-720p`; `unit_price × duration`). Result `video_url` is a direct media link — download promptly. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/gz720/create.md

```json
{
  "model": "seedance2.0-gz-720p",
  "prompt": "A cinematic product shot with natural lighting",
  "duration": 5,
  "aspect_ratio": "16:9",
  "images": ["https://example.com/reference.png"],
  "reference_videos": ["https://example.com/reference.mp4"]
}
```

## Seedance 933 720p video

`POST /api/open-api/v1/seedance/videos` — poll `GET /api/open-api/v1/videos/{taskId}`.

| Field | Required | Notes |
|-------|----------|-------|
| model | yes | `sd2-933-720p` (aliases `sd2_933_720p` / `sd2-933720p` normalize) |
| prompt | yes | 1–5000 chars |
| duration | no | 4–15, default `5` |
| aspect_ratio / ratio | no | `16:9` / `9:16` / `1:1` / `4:3` / `3:4`, default `16:9` |
| reference_mode | no | `frame` / `media` (alias `image` → `media`) |
| generate_audio | no | default `true` |
| images / reference_images | no | max **9** |
| videos / reference_videos | no | max **3** |
| audios / reference_audios | no | max **3**; must pair with image or video refs |

Resolution is **fixed 720p**. Billing: `per_second` at **0.0479**/s (`0.0479 × duration`). Docs: https://docs.viraltok.ai/zh/api-reference/seedance/933720/create.md

```json
{
  "model": "sd2-933-720p",
  "prompt": "A cinematic product shot with natural lighting",
  "duration": 5,
  "aspect_ratio": "16:9",
  "reference_mode": "media",
  "generate_audio": true,
  "images": ["https://example.com/reference.png"],
  "reference_videos": ["https://example.com/reference.mp4"]
}
```

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
