# Codex network approvals / sandbox notes

JimmyAI API calls need outbound HTTPS to `www.jimmyai.cn`. In Codex, network may be disabled by default.

## Reduce approval prompts

Example `~/.codex/config.toml`:

```
approval_policy = "never"
sandbox_mode = "workspace-write"

[sandbox_workspace_write]
network_access = true
```

Or for a single session:

```
codex --sandbox workspace-write --ask-for-approval never
```

## Safety note

Enabling network and disabling approvals is convenient but risky in untrusted repos. Use judgment.
