# Troubleshooting

## code 20001 — auth failure

- Cause: missing, wrong, or expired API key.
- Fix: recreate key at https://api.viraltok.ai, set `JIMMYAI_API_KEY`, confirm no extra spaces.

## code 20002 — bad parameters

- Cause: invalid model, duration, or field combo.
- Fix: check model docs. Route1 `sora2-12s` requires `duration: 12`.

## code -1 — server error

- Cause: temporary upstream issue.
- Fix: retry with exponential backoff (5 s → 10 s → 20 s).

## Insufficient balance

- Cause: account not recharged or `available` balance too low.
- Fix: recharge at https://api.viraltok.ai (minimum ~$1).
- Check: `GET /api/open-api/v1/user/balance` or `python "$JIMMYAI_CLI" user-balance`.

## API key quota exhausted

- Cause: `total_quota` set on the key and `used_quota` reached the cap.
- Fix: raise quota in console or use another key.
- Check: `GET /api/open-api/v1/key/balance` or `python "$JIMMYAI_CLI" key-balance`.

## Sync image timeout

- Cause: client timeout too short; generation takes 30–120 s.
- Fix: set timeout ≥ 180 s (`--timeout 180` in CLI, or curl `--max-time 180`).

## Task stuck in queued / processing

- Cause: queue delay or heavy load.
- Fix: increase poll timeout; retry later; avoid burst concurrency.

## video_url / image_url expired

- Cause: URLs valid ~3 days only.
- Fix: download and store locally immediately after completion.

## sora2-12s duration error

- Cause: `duration` not equal to 12 on route1.
- Fix: always pass `--duration 12` for `sora2-12s`.

## Large b64_json response

- Cause: sync image returns multi-MB base64.
- Fix: use `--output file.png` in CLI; ensure gateway/proxy allows large bodies.

## JIMMYAI_API_KEY not set

- Cause: env var missing in shell or Codex session.
- Fix: `export JIMMYAI_API_KEY="..."` in the same shell before running CLI.

## Network blocked in Codex

- Cause: sandbox has no outbound network.
- Fix: see `references/codex-network.md`.

## Seedance asset rejected

- Cause: reference assets need platform audit first.
- Fix: submit via assets audit endpoint; poll audit status before video create.

## Seedance Mini 特价版 (`seedance2.0-mini-sp`)

- Use `POST /api/open-api/v1/seedance/videos` with `"model": "seedance2.0-mini-sp"` — there is no separate `/seedance/mini-sp/videos` path.
- `resolution` must be `480p` or `720p` (default `720p`).
- `duration` must be 4–15 seconds.
- Poll with `GET /api/open-api/v1/videos/{taskId}` like other async video tasks.

## video_url is a relative path (custom OSS)

- Cause: older API responses could return OSS object keys like `seedance/mini-sp/video/xxx.mp4` instead of a full URL.
- Fix: ensure you query the latest API; completed tasks should return a full `https://` URL (signed when OSS is private). Download within 3 days.

## More help

- Docs: https://docs.jimmyai.cn/llms.txt
- Email: 2114272829@qq.com
- Online chat on https://api.viraltok.ai
