# CLI reference (`scripts/jimmyai.py`)

Command catalog for the bundled JimmyAI CLI. Keep `SKILL.md` overview-first; put verbose details here.

## Setup

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export JIMMYAI_CLI="$CODEX_HOME/skills/jimmyai/scripts/jimmyai.py"
```

From this repo:

```bash
export JIMMYAI_CLI="$(git rev-parse --show-toplevel)/jimmyai/scripts/jimmyai.py"
```

Required env for live calls:

```bash
export JIMMYAI_API_KEY="sk-..."
# Optional override:
export JIMMYAI_BASE_URL="https://api.viraltok.ai"
```

## Commands

| Command | Purpose |
|---------|---------|
| `create-video` | Create Sora video task (async) |
| `create-seedance-video` | Create Seedance video task (async) |
| `create-minimax-video` | Create MiniMax H3 video task (async) |
| `create-seedance25-video` | Create Seedance 2.5 video task (async) |
| `create-seedance20933-video` | Create Seedance 2.0 933 video task (async) |
| `create-gemini-video` | Create Gemini Omni video task |
| `create-image` | Create async image task |
| `generate-image` | Sync text-to-image (OpenAI-compatible) |
| `remove-bg` | Sync background removal |
| `remove-subtitle` | Create video subtitle-removal task (async) |
| `poll` | Query task status by ID |
| `user-balance` | Query user JimiCoin account balance |
| `key-balance` | Query API key quota balance |
| `upload-file` | Upload image/video/audio; returns URL |
| `create-and-poll` | Create task and wait for completion |

All commands support `--dry-run` (prints request, no network).

## create-video

```bash
python "$JIMMYAI_CLI" create-video \
  --model sora2-12s \
  --prompt "A cat walking in a garden" \
  --duration 12 \
  --orientation landscape

# With reference image
python "$JIMMYAI_CLI" create-video \
  --model sora2-12s \
  --prompt "Animate this scene" \
  --duration 12 \
  --image "https://example.com/ref.jpg"
```

## create-seedance-video

`POST /api/open-api/v1/seedance/videos` — poll with `poll --type video`.

```bash
# Fast I2V (image-to-video, per-task billing)
python "$JIMMYAI_CLI" create-seedance-video \
  --model seedance2.0-fast-i2v \
  --prompt "Subject turns slowly, cinematic lighting" \
  --duration 8 \
  --ratio "16:9" \
  --image "https://example.com/ref-1.jpg" \
  --image "https://example.com/ref-2.jpg"

# MD fast
python "$JIMMYAI_CLI" create-seedance-video \
  --model seedance2.0-fast-md \
  --prompt "Rainy street at night" \
  --duration 5 \
  --ratio "9:16"

# SP economy (720p / 1080p only — not 480p)
python "$JIMMYAI_CLI" create-seedance-video \
  --model seedance2.0-sp \
  --prompt "Rainy street at night, cinematic push-in" \
  --duration 8 \
  --resolution 720p \
  --ratio "16:9" \
  --first-image "https://example.com/start.png"

# Mini 特价版 (economy Mini SP)
python "$JIMMYAI_CLI" create-seedance-video \
  --model seedance2.0-mini-sp \
  --prompt "A cat walking in a garden, cinematic" \
  --duration 8 \
  --resolution 720p \
  --ratio "16:9" \
  --image "https://example.com/ref.jpg"

# GZ 720p (fixed 720p; per-second billing; direct result media URL)
python "$JIMMYAI_CLI" create-seedance-video \
  --model seedance2.0-gz-720p \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --ratio "16:9" \
  --image "https://example.com/reference.png" \
  --video "https://example.com/reference.mp4"

# 933 720p (fixed 720p; 0.0479/s)
python "$JIMMYAI_CLI" create-seedance-video \
  --model sd2-933-720p \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --ratio "16:9" \
  --image "https://example.com/reference.png" \
  --video "https://example.com/reference.mp4"
```

`seedance2.0-sp` / `seedance2.0-fast-sp`: unified `POST /api/open-api/v1/seedance/videos`, `resolution` `720p` or `1080p` only (default `720p`), duration 4–15 s. `seedance2.0-fast-sp` does not support `reference_videos`. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/sp/create.md

`seedance2.0-mini-sp`: unified `POST /api/open-api/v1/seedance/videos`, `resolution` `480p` or `720p`, duration 4–15 s.

`seedance2.0-fast-i2v`: image refs only (max 9), no `reference_videos` / `reference_audios`, duration 1–15 s. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/md/fast-i2v.md

`seedance2.0-gz-720p`: fixed **720p**, billed `per_second`, duration 4–15 s (default 5); aspect_ratio `21:9|16:9|4:3|1:1|3:4|9:16`; max 9 `--image` / 3 `--video` / 3 `--audio` (audio requires image or video). Result URL is a direct media link. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/gz720/create.md

`sd2-933-720p`: fixed **720p**, billed `per_second` at **0.0479**/s, duration 4–15 s (default 5); aspect_ratio `16:9|9:16|1:1|4:3|3:4`; max 9 `--image` / 3 `--video` / 3 `--audio`. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/933720/create.md

## create-minimax-video

`POST /api/open-api/v1/minimax/videos` — poll with `poll --type video`.

```bash
python "$JIMMYAI_CLI" create-minimax-video \
  --model minimax-h3 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --aspect-ratio "16:9" \
  --size "2560x1440" \
  --image "https://example.com/reference.png" \
  --audio "https://example.com/reference.mp3" \
  --first-image "https://example.com/first.png" \
  --last-image "https://example.com/last.png"
```

`minimax-h3`: billed `per_task` (flat per request). Duration 5–15 s (default 5); max 5 `--image` and 1 `--audio`; optional first/last frames. Docs: https://docs.viraltok.ai/zh/api-reference/minimax/create.md

## create-seedance25-video

`POST /api/open-api/v1/seedance25/videos` — poll with `poll --type video`.

```bash
python "$JIMMYAI_CLI" create-seedance25-video \
  --model seedance-2.5 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio 16:9 \
  --resolution 720p \
  --image "https://example.com/reference.png" \
  --audio "https://example.com/reference.mp3"
```

SP:

```bash
python "$JIMMYAI_CLI" create-seedance25-video \
  --model seedance-2.5-sp \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --aspect-ratio 16:9 \
  --resolution 720p \
  --first-image "https://example.com/start.png" \
  --last-image "https://example.com/end.png"
```

`seedance-2.5`: billed `per_second` by resolution (`seedance-2.5-480p` / `seedance-2.5-720p`). Duration 4–30 s (default 4); aspect_ratio `16:9|9:16|1:1` (default `9:16`); resolution `480p|720p`; max 30 `--image` / 10 `--video` (each & total ≤30.2s) / 10 `--audio` (each ≤30s). Docs: https://docs.viraltok.ai/zh/api-reference/seedance/25/create.md

`seedance-2.5-sp`: billed `per_second` at fixed **0.5**/s. Duration 4–30 s; resolution **720p only**; same media limits; optional `--first-image` / `--last-image` (mutually exclusive with `--image`). Same docs.

## create-seedance20933-video

`POST /api/open-api/v1/seedance/videos` — poll with `poll --type video`.

```bash
python "$JIMMYAI_CLI" create-seedance20933-video \
  --model seedance2.0-933 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio 16:9 \
  --resolution 720p \
  --face-processing true \
  --generate-audio false \
  --reference-mode image \
  --image "https://example.com/reference.png" \
  --video "https://example.com/reference.mp4" \
  --audio "https://example.com/reference.mp3"
```

`seedance2.0-933`: billed `per_second` by resolution (`seedance2.0-933-480p` / `seedance2.0-933-720p` / `seedance2.0-933-1080p`). Duration 4–15 s (default 4); aspect_ratio `21:9|16:9|4:3|1:1|3:4|9:16` (default `16:9`); resolution `480p|720p|1080p`; max 9 `--image` / 3 `--video` / 3 `--audio`; optional `--face-processing` / `--generate-audio` / `--reference-mode`. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/20933/create.md

## create-gemini-video

```bash
python "$JIMMYAI_CLI" create-gemini-video \
  --model Gemini-Omini \
  --prompt "Neon city at night, cinematic tracking shot" \
  --duration 6 \
  --resolution 720p \
  --aspect-ratio "16:9"
```

## create-image (async)

```bash
python "$JIMMYAI_CLI" create-image \
  --model gpt-image-2 \
  --prompt "A watercolor landscape" \
  --ratio "16:9" \
  --quality high
```

## generate-image (sync)

```bash
python "$JIMMYAI_CLI" generate-image \
  --prompt "Cyberpunk alley in the rain" \
  --size 1024x1024 \
  --quality high \
  --output result.png
```

Sync calls may take 30–120 s. Default timeout is 180 s (`--timeout`).

## remove-bg (sync)

`POST /api/open-api/v1/images/remove-bg` — default returns `b64_json`; use `--response-format url` for `image_url`.

```bash
# Default: save base64 result to file
python "$JIMMYAI_CLI" remove-bg \
  --image-url "https://example.com/photo.png" \
  --output cutout.png

# Prefer URL instead of base64
python "$JIMMYAI_CLI" remove-bg \
  --image-url "https://example.com/photo.png" \
  --response-format url
```

Timeout ≥ 180 s recommended (`--timeout`).

## remove-subtitle (async)

`POST /api/open-api/v1/remove-subtitle/videos` — poll with `poll --type video`.

```bash
python "$JIMMYAI_CLI" remove-subtitle \
  --video-url "https://example.com/input.mp4"

# Create + wait
python "$JIMMYAI_CLI" create-and-poll \
  --type remove-subtitle \
  --video-url "https://example.com/input.mp4" \
  --download output.mp4
```

Default model: `video_remove_subtitle`. Billing is `per_second` (duration probed from `video_url`, ceiled, min 1s).

## poll

```bash
python "$JIMMYAI_CLI" poll --task-id "abc123" --type video
python "$JIMMYAI_CLI" poll --task-id "abc123" --type image
```

## create-and-poll

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type video \
  --model sora2-12s \
  --prompt "A cat in a garden" \
  --duration 12 \
  --orientation landscape \
  --interval 10 \
  --timeout 1800 \
  --download output.mp4
```

`--type` values: `video`, `gemini-video`, `seedance-video`, `seedance25-video`, `seedance20933-video`, `minimax-video`, `remove-subtitle`, `image`

For `--type remove-subtitle`, pass `--video-url` (no `--prompt`). Model defaults to `video_remove_subtitle`.

Seedance example:

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance-video \
  --model seedance2.0-fast-i2v \
  --prompt "A cat walking in a garden" \
  --duration 8 \
  --ratio "16:9" \
  --image "https://example.com/ref.jpg" \
  --download output.mp4
```

GZ 720p example:

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance-video \
  --model seedance2.0-gz-720p \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --ratio "16:9" \
  --image "https://example.com/reference.png" \
  --video "https://example.com/reference.mp4" \
  --download output.mp4
```

MiniMax H3 example:

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type minimax-video \
  --model minimax-h3 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --aspect-ratio "16:9" \
  --image "https://example.com/ref.jpg" \
  --download output.mp4
```

Seedance 2.5 example:

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance25-video \
  --model seedance-2.5 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio "16:9" \
  --resolution 720p \
  --image "https://example.com/ref.jpg" \
  --download output.mp4
```

Seedance 2.0 933 example:

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance20933-video \
  --model seedance2.0-933 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio "16:9" \
  --resolution 720p \
  --image "https://example.com/ref.jpg" \
  --download output.mp4
```

## Global flags

| Flag | Description |
|------|-------------|
| `--dry-run` | Print request JSON, skip network |
| `--json-out PATH` | Write response JSON to file |
| `--base-url URL` | Override `JIMMYAI_BASE_URL` |

## Prompt files

For long prompts, use `--prompt-file`:

```bash
cat > prompt.txt << 'EOF'
A cinematic wide shot of a teal sports car
driving through a desert highway at sunset.
EOF

python "$JIMMYAI_CLI" create-video \
  --prompt-file prompt.txt \
  --model sora2-12s \
  --duration 12
```

## poll

```bash
python "$JIMMYAI_CLI" poll --task-id TASK_ID --type video
```

## user-balance

Query JimiCoin account balance for the API key owner.

```bash
python "$JIMMYAI_CLI" user-balance
```

`GET /api/open-api/v1/user/balance` — fields: `balance`, `used_coin`, `available`.

## key-balance

Query per-key quota usage.

```bash
python "$JIMMYAI_CLI" key-balance
```

`GET /api/open-api/v1/key/balance` — fields: `name`, `total_quota`, `used_quota`, `available_quota`, `unlimited`.

## upload-file

Upload a local file and get a URL for downstream APIs (`images`, `reference_videos`, etc.).

```bash
python "$JIMMYAI_CLI" upload-file --file ./photo.jpg
python "$JIMMYAI_CLI" upload-file --file ./clip.mp4 --json-out upload.json
```

`POST /api/open-api/v1/files/upload` — multipart field `file`, max 100 MB.

Supported: common image (jpg/png/webp/…), video (mp4/mov/webm/…), audio (mp3/wav/…). See `references/api.md` for the full extension list.

Default timeout 300 s (`--timeout`). Use the returned `data.url` in create-video / create-seedance-video `--image` or API `images` arrays.

## Output

Successful poll shows `status`, `progress`, and result URLs. Use `--download PATH` with `create-and-poll` to save the file locally.
