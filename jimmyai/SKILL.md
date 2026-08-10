---
name: "jimmyai"
description: "Integrate JimmyAI image and video generation APIs (Sora, VEO, Gemini Omni, Seedance including SP economy, Mini 特价版, Seedance 2.5 / 2.5 SP, MiniMax H3, Seedance 2.0 933, GPT Image, remove-bg) via the bundled CLI (`scripts/jimmyai.py`). Use when the user asks to connect JimmyAI, generate AI images/videos, remove image backgrounds, poll async tasks, set up API keys, or integrate https://api.viraltok.ai — including zero-experience onboarding. Requires `JIMMYAI_API_KEY`."
---

# JimmyAI API Skill

JimmyAI is an OpenAI-compatible gateway for image and video generation. Base URL: `https://api.viraltok.ai`. Docs index: https://docs.viraltok.ai/llms.txt

This skill helps users integrate JimmyAI from zero — register, get a key, send the first request, and poll async tasks. Prefer the bundled CLI for deterministic runs. `$jimmyai` is a skill tag in prompts, not a shell command.

## When to use

- First-time JimmyAI setup (account, API key, recharge, env var)
- Generate a video (Sora / Gemini Omni / VEO / Seedance / Seedance 2.5 / MiniMax H3 / Seedance 2.0 933)
- Generate an image (sync or async)
- Remove image background (sync `remove-bg`)
- Poll task status and download results
- Debug auth, billing, or network errors
- Build integration code (curl, Python, Node, etc.)

## Zero-experience onboarding

When the user has no API key or has never used JimmyAI, walk through these steps in order. Do not skip steps.

1. **Register** at https://api.viraltok.ai
2. **Create API key** in the console (shown once — save it locally)
3. **Recharge** account (minimum ~$1; Alipay / WeChat supported)
4. **Set environment variable** (never paste the full key in chat):
   ```bash
   export JIMMYAI_API_KEY="sk-..."
   ```
5. **Verify** with a dry-run (no network, no key required):
   ```bash
   python "$JIMMYAI_CLI" create-video --prompt "test" --dry-run
   ```
6. **First live call** — sync image is fastest for beginners:
   ```bash
   python "$JIMMYAI_CLI" generate-image --prompt "a red apple on white background"
   ```
7. For video (async), use `create-and-poll` or `create-video` then `poll`.

If `JIMMYAI_API_KEY` is missing, guide the user to set it locally and confirm when ready. Offer OS-specific env-var help if needed.

## Decision tree

| User wants | Command / endpoint |
|------------|-------------------|
| Quick image, no polling | `generate-image` → `POST /images/generations` (sync) |
| Image with more model options | `create-image` → poll `GET /images/{taskId}` |
| Remove image background | `remove-bg` → `POST /images/remove-bg` (sync; default `b64_json`) |
| Sora video | `create-video` → poll `GET /videos/{taskId}` |
| Gemini Omni video | `create-gemini-video` → poll `GET /videos/{taskId}` |
| Gemini Omni 10s (`omni-10s`) | same endpoint with `--model omni-10s` |
| VEO frames (Fast / Lite) | `POST /api/open-api/v1/veo/frames` → poll `GET /videos/{taskId}` (see docs; CLI may need raw curl) |
| Seedance video (SP economy / MD / Fast I2V / Mini 特价版 / etc.) | `create-seedance-video` → poll `GET /videos/{taskId}` |
| MiniMax H3 video | `create-minimax-video` → poll `GET /videos/{taskId}` |
| Seedance 2.5 / 2.5 SP video | `create-seedance25-video` → poll `GET /videos/{taskId}` |
| Flux 3 video | `POST /api/open-api/v1/flux3/videos` → poll `GET /videos/{taskId}` |
| Seedance 2.0 933 video | `create-seedance20933-video` → poll `GET /videos/{taskId}` |
| Just check task status | `poll --task-id <id> --type video\|image` |
| Check user account balance | `user-balance` → `GET /user/balance` |
| Check API key quota | `key-balance` → `GET /key/balance` |
| Upload reference media (image/video/audio) | `upload-file` → `POST /files/upload` |
| Create + wait in one step | `create-and-poll` |

For VEO, Manxue Seedance, STD, image edits, image understanding, remove-bg, or **local file upload** (`POST /files/upload`), fetch the specific page from https://docs.viraltok.ai/llms.txt before calling. SP economy detail: https://docs.viraltok.ai/zh/api-reference/seedance/sp/create.md · Seedance 2.5: https://docs.viraltok.ai/zh/api-reference/seedance/25/create.md · Flux 3: https://docs.viraltok.ai/zh/api-reference/flux3/create.md · MiniMax H3: https://docs.viraltok.ai/zh/api-reference/minimax/create.md · Seedance 2.0 933: https://docs.viraltok.ai/zh/api-reference/seedance/20933/create.md · Remove background: https://docs.viraltok.ai/zh/api-reference/images/remove-bg.md

## Workflow

1. Confirm intent: image vs video, sync vs async, model choice.
2. Ensure `JIMMYAI_API_KEY` is set (or use `--dry-run` to preview).
3. Run the bundled CLI (`scripts/jimmyai.py`). Set `JIMMYAI_CLI` to its path (see `references/cli.md`).
4. For async tasks, poll until `status` is terminal (`completed`, `failed`, `canceled`).
5. Download `video_url` / `image_url` promptly — links expire in ~3 days.
6. Remove temp files (prompt files, JSON dumps) after the run.
7. Iterate with one targeted change per request.

## Authentication & config

| Variable | Default | Purpose |
|----------|---------|---------|
| `JIMMYAI_API_KEY` | — | Bearer token (required for live calls) |
| `JIMMYAI_BASE_URL` | `https://api.viraltok.ai` | API base URL |

Header: `Authorization: Bearer <JIMMYAI_API_KEY>`

## Async pattern

Most video and async image tasks follow:

1. `POST` create → receive `task_id`
2. `GET` poll every 5–15 s until done
3. Read `data.result.video_url` or `data.result.image_url`

Response `code`: `20000` = success, `20001` = auth failure, `20002` = bad params, `-1` = server error.

## Defaults & rules

- Default video model: `sora2-12s` (route1; `duration` must be `12`)
- Default Gemini Omni model: `Gemini-Omini`
- Default sync image model: `gpt-image-2`, size `1024x1024`, quality `low`
- Sync image response: default `response_format=url` (returns `data[].url`); use `b64_json` for base64
- Sync image timeout: set client timeout ≥ 180 s (generation takes 30–120 s)
- Generated URLs valid ~3 days — copy to own storage
- Prefer bundled CLI; do not modify `scripts/jimmyai.py` unless the user asks
- For full API params, see `references/api.md`
- For step-by-step beginner guide, see `references/quickstart.md`

### Customer-facing content boundaries

When writing docs, README snippets, chat answers, code comments for users, or examples that leave this skill:

- **Do not reveal upstream channel vendors.** Never name, link, or imply internal providers / reseller gateways (routing codes, private Apifox portals, vendor hostnames, channel mounts/weights, YAML vendor credentials).
- Describe only JimmyAI / ViraltokAI **public** OpenAPI models, request fields, billing, and behavior.
- Do not paste upstream vendor API path shapes or slug aliases unless they are identical to the public OpenAPI contract.
- When models differ by quality/speed tier (e.g. Veo Fast vs Lite), present them as **product variants**, not as different suppliers.

## Examples

### First video (Sora, async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type video \
  --model sora2-12s \
  --prompt "A cat walking through a sunny garden, cinematic" \
  --duration 12 \
  --orientation landscape
```

### Quick image (sync)

```bash
python "$JIMMYAI_CLI" generate-image \
  --prompt "Cyberpunk city at night, neon signs" \
  --quality high
```

### Remove background (sync)

```bash
# Default returns b64_json
python "$JIMMYAI_CLI" remove-bg \
  --image-url "https://example.com/photo.png" \
  --output cutout.png

# Prefer URL
python "$JIMMYAI_CLI" remove-bg \
  --image-url "https://example.com/photo.png" \
  --response-format url
```

### Fast I2V video (Seedance, async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance-video \
  --model seedance2.0-fast-i2v \
  --prompt "Subject turns slowly, cinematic lighting" \
  --duration 8 \
  --ratio "16:9" \
  --image "https://example.com/ref.jpg"
```

### SP economy video (Seedance, async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance-video \
  --model seedance2.0-sp \
  --prompt "Rainy street at night, girl turns and smiles, cinematic push-in" \
  --duration 8 \
  --resolution 720p \
  --ratio "16:9" \
  --first-image "https://example.com/start.png" \
  --download output.mp4
```

`seedance2.0-sp` / `seedance2.0-fast-sp`: `resolution` is `720p` (default) or `1080p` only — **not `480p`**. Duration 4–15 s. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/sp/create.md

### Mini video (Seedance, async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance-video \
  --model seedance2.0-mini-720p \
  --prompt "Subject turns slowly, cinematic lighting" \
  --duration 6 \
  --ratio "9:16" \
  --image "https://example.com/ref.jpg"
```

`seedance2.0-mini` / `seedance2.0-mini-video`: pass `resolution`, or use billing name as `--model` (e.g. `seedance2.0-mini-720p`). Docs: https://docs.viraltok.ai/zh/api-reference/seedance/mini/create.md

### MiniMax H3 video (async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type minimax-video \
  --model minimax-h3 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --aspect-ratio "16:9" \
  --image "https://example.com/reference.png" \
  --download output.mp4
```

Or create only:

```bash
python "$JIMMYAI_CLI" create-minimax-video \
  --model minimax-h3 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --aspect-ratio "16:9" \
  --size "2560x1440" \
  --image "https://example.com/reference.png" \
  --audio "https://example.com/reference.mp3"
```

`minimax-h3`: billed `per_task` (flat per request; `duration` does not change cost). Duration 5–15 s; max 5 reference images + 1 audio; optional `--first-image` / `--last-image`. Docs: https://docs.viraltok.ai/zh/api-reference/minimax/create.md

### Seedance 2.5 video (async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance25-video \
  --model seedance-2.5 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio "16:9" \
  --resolution 720p \
  --image "https://example.com/reference.png" \
  --audio "https://example.com/reference.mp3" \
  --download output.mp4
```

Or create only:

```bash
python "$JIMMYAI_CLI" create-seedance25-video \
  --model seedance-2.5 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio "9:16" \
  --resolution 480p
```

SP economy (`seedance-2.5-sp`, flat **0.5**/s, 720p only, reference videos allowed):

```bash
python "$JIMMYAI_CLI" create-seedance25-video \
  --model seedance-2.5-sp \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 5 \
  --aspect-ratio "16:9" \
  --resolution 720p \
  --image "https://example.com/reference.png" \
  --video "https://example.com/reference.mp4"
```

`seedance-2.5`: billed `per_second` by resolution (`seedance-2.5-480p` / `seedance-2.5-720p`). Duration 4–30 s (default 4); aspect_ratio `16:9|9:16|1:1`; resolution `480p|720p`; max 30 images / 10 audios; **reference videos not supported**. Docs: https://docs.viraltok.ai/zh/api-reference/seedance/25/create.md

`seedance-2.5-sp`: billed `per_second` at fixed **0.5**/s (`seedance-2.5-sp`). Duration 4–29 s; aspect_ratio `16:9|9:16|1:1`; resolution **720p only**; max 30 images / 10 videos / 10 audios. Same endpoint and docs.

### Seedance 2.0 933 video (async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance20933-video \
  --model seedance2.0-933 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio "16:9" \
  --resolution 720p \
  --image "https://example.com/reference.png" \
  --video "https://example.com/reference.mp4" \
  --audio "https://example.com/reference.mp3" \
  --download output.mp4
```

Or create only:

```bash
python "$JIMMYAI_CLI" create-seedance20933-video \
  --model seedance2.0-933 \
  --prompt "A cinematic product shot with natural lighting" \
  --duration 4 \
  --aspect-ratio "16:9" \
  --resolution 480p
```

`seedance2.0-933`: billed `per_second` by resolution (`seedance2.0-933-480p` / `seedance2.0-933-720p` / `seedance2.0-933-1080p`). Duration 4–15 s (default 4); aspect_ratio `21:9|16:9|4:3|1:1|3:4|9:16` (default `16:9`); resolution `480p|720p|1080p`; max 9 images / 3 videos / 3 audios; `face_processing` default true; `generate_audio` default false; `reference_mode` `image|frame` (default `image`). Docs: https://docs.viraltok.ai/zh/api-reference/seedance/20933/create.md

### Mini 特价版 video (Seedance, async)

```bash
python "$JIMMYAI_CLI" create-and-poll \
  --type seedance-video \
  --model seedance2.0-mini-sp \
  --prompt "A cat walking in a garden, cinematic" \
  --duration 8 \
  --resolution 720p \
  --ratio "16:9" \
  --image "https://example.com/ref.jpg"
```

### Poll existing task

```bash
python "$JIMMYAI_CLI" poll --task-id "abc123" --type video
```

### Check balances

```bash
python "$JIMMYAI_CLI" user-balance
python "$JIMMYAI_CLI" key-balance
```

### Upload reference file

```bash
python "$JIMMYAI_CLI" upload-file --file ./ref.jpg
# Use returned data.url in --image or API images[] field
```

## Reference map

- **`references/quickstart.md`**: zero-base onboarding, curl examples, language snippets
- **`references/cli.md`**: full CLI command catalog
- **`references/api.md`**: endpoint summary and model notes
- **`references/troubleshooting.md`**: common errors and fixes
- **`references/codex-network.md`**: Codex sandbox / network approval tips
- **Live docs**: https://docs.viraltok.ai/llms.txt
