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
| `create-gemini-video` | Create Gemini Omni video task |
| `create-image` | Create async image task |
| `generate-image` | Sync text-to-image (OpenAI-compatible) |
| `poll` | Query task status by ID |
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

# Mini 特价版 (economy Mini SP)
python "$JIMMYAI_CLI" create-seedance-video \
  --model seedance2.0-mini-sp \
  --prompt "A cat walking in a garden, cinematic" \
  --duration 8 \
  --resolution 720p \
  --ratio "16:9" \
  --image "https://example.com/ref.jpg"
```

`seedance2.0-mini-sp`: unified `POST /api/open-api/v1/seedance/videos`, `resolution` `480p` or `720p`, duration 4–15 s.

`seedance2.0-fast-i2v`: image refs only (max 9), no `reference_videos` / `reference_audios`, duration 1–15 s. Docs: https://docs.jimmyai.cn/zh/api-reference/seedance/md/fast-i2v.md

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

`--type` values: `video`, `gemini-video`, `seedance-video`, `image`

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

## Output

Successful poll shows `status`, `progress`, and result URLs. Use `--download PATH` with `create-and-poll` to save the file locally.
