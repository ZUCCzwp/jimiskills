# jimiskills

Cursor / Codex Agent Skills for [JimmyAI](https://www.jimmyai.cn) services.

## Skills

| Skill | Description |
|-------|-------------|
| [jimmyai](./jimmyai/) | JimmyAI image & video API integration — zero-experience onboarding, CLI, and docs |

## Install (Codex)

Copy or symlink the skill into your Codex skills directory:

```bash
mkdir -p ~/.codex/skills
ln -s "$(pwd)/jimmyai" ~/.codex/skills/jimmyai
```

Or install from GitHub when published:

```bash
# using Codex skill-installer (if available)
python ~/.codex/skills/.system/skill-installer/scripts/install-skill-from-github.py \
  --repo <org>/jimiskills --path jimmyai
```

## Quick start

```bash
export JIMMYAI_API_KEY="your-key"
export JIMMYAI_CLI="$(pwd)/jimmyai/scripts/jimmyai.py"

# Dry-run (no API key needed)
python "$JIMMYAI_CLI" generate-image --prompt "test" --dry-run

# First live call — sync image
python "$JIMMYAI_CLI" generate-image --prompt "A red apple on white background" --output apple.png
```

Get your API key at https://www.jimmyai.cn. Docs: https://docs.jimmyai.cn/llms.txt

## Usage in Codex

Invoke with `$jimmyai` in your prompt:

```
Use $jimmyai to help me set up JimmyAI and generate my first video.
```
