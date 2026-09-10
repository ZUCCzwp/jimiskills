---
name: "openapi-endpoint-routing"
description: >-
  Map JimmyAI/ViraltokAI public OpenAPI model IDs to the correct create
  endpoint (customers often mix /seedance/videos with /minimax/videos or
  /seedance25/videos). Use when writing curl/SDK samples, diagnosing
  「不支持的模型参数」, unexpected Source/channel mounts, or adding
  model×path guards in jimiaiopengo / jimiskills CLI.
---

# OpenAPI model × endpoint routing

## Core rule

**`model` alone is not enough.** Each dedicated video family must hit its own create path under `https://api.viraltok.ai`.

Wrong path → wrong product line, generic「不支持的模型参数」, or (historically) silent fall-through onto Seedance 2.0 Full. Console channel weights only apply on the handler that owns that model.

## Required path table (public)

| Models (request `model`) | Create path | CLI |
|--------------------------|-------------|-----|
| Seedance **2.0** (`seedance2.0-*`, `sd2_*`, Manxue/SP/Mini/GZ/933…) | `POST /api/open-api/v1/seedance/videos` | `create-seedance-video` / `create-seedance20933-video` |
| Seedance **2.5** (`seedance-2.5*`, `seedance2.5*`, `seedance-2.5-sp`, `seedance2.5-gz*`) | `POST /api/open-api/v1/seedance25/videos` | `create-seedance25-video` |
| MiniMax H3 (`minimax-h3`, `minimax-h3-gz`) | `POST /api/open-api/v1/minimax/videos` | `create-minimax-video` |
| Kling O3 (`kling-o3*`) | `POST /api/open-api/v1/kling/videos` | `create-kling-video` |
| Wan 3.0 (`wan3.0*`) | `POST /api/open-api/v1/wan/videos` | (API only) |
| Flux 3 (`flux-3-*`) | `POST /api/open-api/v1/flux3/videos` | `create-flux3-video` |
| Video translate (`video-translate-*`) | `POST /api/open-api/v1/video-translate/videos` | `video-translate` |
| Sora / generic | `POST /api/open-api/v1/videos` | `create-video` |
| Gemini Omni | `POST /api/open-api/v1/gemini/omni/videos` | `create-gemini-video` |
| Grok video | `POST /api/open-api/v1/grok/videos` | `create-grok-video` |
| Digital human | `POST /api/open-api/v1/digital-human/videos` | `create-digital-human` |

Poll almost all video tasks with `GET /api/open-api/v1/videos/{taskId}` (create path ≠ query path).

## Frequent mix-ups

| Wrong | Right |
|-------|-------|
| `minimax-h3` on `/seedance/videos` | `/minimax/videos` |
| `seedance-2.5` / `seedance2.5-gz` on `/seedance/videos` | `/seedance25/videos` |
| `kling-o3` on `/seedance/videos` | `/kling/videos` |
| Seedance 2.0 on `/minimax/videos` or `/seedance25/videos` | `/seedance/videos` |

## Agent checklist

1. Before any create curl/sample: look up **model → path** in the table above. Never copy another family’s URL and only change `model`.
2. If the user pastes a failing request: compare HTTP path to the table first; only then dig into params/billing.
3. Prefer the jimiskills CLI command for that family — CLI refuses cross-family `model` before calling the API.
4. Customer docs / replies: public paths and model IDs only. Do **not** name upstream vendors, channel codes, or internal mounts.

## Server-side guard pattern (`jimiaiopengo`)

Reject foreign models early with an actionable error that includes the **correct public path**:

```text
model minimax-h3 请改用 POST /api/open-api/v1/minimax/videos，勿使用 /seedance/videos
```

Today `rejectWrongEndpointOnSeedanceVideos` covers dedicated models wrongly hitting `/seedance/videos`. Prefer extending the same table-driven check onto other dedicated create handlers (minimax / seedance25 / kling / wan / flux3 / video-translate) so reverse mix-ups also tip the right path.

When adding a new dedicated video path:

1. Add model matcher + public path to the shared table.
2. Call reject at the start of the create handler (before generic validate).
3. Add table-driven tests (`endpoint_guard_test.go`).
4. Update this skill table + `jimmyai` CLI `_assert_model_matches_endpoint`.

## Ops: “channel weight ignored”

If DB mounts say TS-only for `minimax-h3` but tasks still show another `Source`:

1. Check access log / task create **HTTP path** first.
2. Expected only when path is `/minimax/videos`.
3. Then check PickProvider / yaml / empty-Pick fallback.

## Related

- Customer CLI + samples: `$jimmyai` (`jimmyai/SKILL.md`, `references/api.md`, `references/troubleshooting.md`)
- Docs index: https://docs.viraltok.ai/llms.txt
