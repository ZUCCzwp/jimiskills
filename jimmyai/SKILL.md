---
name: "jimmyai"
description: "Integrate JimmyAI image and video generation APIs (Sora, VEO, Gemini Omni, Seedance, GPT Image) via the bundled CLI (`scripts/jimmyai.py`). Use when the user asks to connect JimmyAI, generate AI images/videos, poll async tasks, set up API keys, or integrate https://www.jimmyai.cn — including zero-experience onboarding. Requires `JIMMYAI_API_KEY`."
---

# JimmyAI API Skill

JimmyAI is an OpenAI-compatible gateway for image and video generation. Base URL: `https://www.jimmyai.cn`. Docs index: https://docs.jimmyai.cn/llms.txt

This skill helps users integrate JimmyAI from zero — register, get a key, send the first request, and poll async tasks. Prefer the bundled CLI for deterministic runs. `$jimmyai` is a skill tag in prompts, not a shell command.

## When to use

- First-time JimmyAI setup (account, API key, recharge, env var)
- Generate a video (Sora / Gemini Omni / VEO / Seedance)
- Generate an image (sync or async)
- Poll task status and download results
- Debug auth, billing, or network errors
- Build integration code (curl, Python, Node, etc.)

## Zero-experience onboarding

When the user has no API key or has never used JimmyAI, walk through these steps in order. Do not skip steps.

1. **Register** at https://www.jimmyai.cn
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
| Sora video | `create-video` → poll `GET /videos/{taskId}` |
| Gemini Omni video | `create-gemini-video` → poll `GET /videos/{taskId}` |
| Just check task status | `poll --task-id <id> --type video\|image` |
| Create + wait in one step | `create-and-poll` |

For VEO, Seedance, image edits, or image understanding, fetch the specific page from https://docs.jimmyai.cn/llms.txt before calling.

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
| `JIMMYAI_BASE_URL` | `https://www.jimmyai.cn` | API base URL |

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
- Sync image timeout: set client timeout ≥ 180 s (generation takes 30–120 s)
- Generated URLs valid ~3 days — copy to own storage
- Prefer bundled CLI; do not modify `scripts/jimmyai.py` unless the user asks
- For full API params, see `references/api.md`
- For step-by-step beginner guide, see `references/quickstart.md`

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

### Poll existing task

```bash
python "$JIMMYAI_CLI" poll --task-id "abc123" --type video
```

## Reference map

- **`references/quickstart.md`**: zero-base onboarding, curl examples, language snippets
- **`references/cli.md`**: full CLI command catalog
- **`references/api.md`**: endpoint summary and model notes
- **`references/troubleshooting.md`**: common errors and fixes
- **`references/codex-network.md`**: Codex sandbox / network approval tips
- **Live docs**: https://docs.jimmyai.cn/llms.txt
