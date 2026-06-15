# Troubleshooting

## code 20001 — auth failure

- Cause: missing, wrong, or expired API key.
- Fix: recreate key at https://www.jimmyai.cn, set `JIMMYAI_API_KEY`, confirm no extra spaces.

## code 20002 — bad parameters

- Cause: invalid model, duration, or field combo.
- Fix: check model docs. Route1 `sora2-12s` requires `duration: 12`.

## code -1 — server error

- Cause: temporary upstream issue.
- Fix: retry with exponential backoff (5 s → 10 s → 20 s).

## Insufficient balance

- Cause: account not recharged.
- Fix: recharge at https://www.jimmyai.cn (minimum ~$1).

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

## More help

- Docs: https://docs.jimmyai.cn/llms.txt
- Email: 2114272829@qq.com
- Online chat on https://www.jimmyai.cn
