# Quickstart (zero experience)

Complete guide for users who have never used JimmyAI or any AI API.

## Step 1: Create account

1. Open https://api.viraltok.ai
2. Register and log in

## Step 2: Get API key

1. Go to API key management in the console
2. Click create new key
3. Copy and save the key locally (shown only once)

## Step 3: Recharge

1. Open the recharge page
2. Add at least ~$1 (Alipay / WeChat)
3. Wait for balance to update

## Step 4: Set environment variable

**macOS / Linux (bash/zsh):**

```bash
export JIMMYAI_API_KEY="your-key-here"
# Optional: persist in ~/.zshrc or ~/.bashrc
```

**Windows (PowerShell):**

```powershell
$env:JIMMYAI_API_KEY = "your-key-here"
```

Never share the full key in chat or commit it to git. Use `.env` files listed in `.gitignore`.

## Step 5: Verify with curl

### Sync image (easiest first test)

```bash
curl --request POST \
  --url https://api.viraltok.ai/api/open-api/v1/images/generations \
  --header "Authorization: Bearer $JIMMYAI_API_KEY" \
  --header "Content-Type: application/json" \
  --max-time 180 \
  --data '{
    "model": "gpt-image-2",
    "prompt": "A simple red apple on white background",
    "size": "1024x1024",
    "quality": "low"
  }'
```

Success: `"code": 20000` and `data.data[0].b64_json` or URL in response.

### Async video

```bash
# Create task
curl --request POST \
  --url https://api.viraltok.ai/api/open-api/v1/videos \
  --header "Authorization: Bearer $JIMMYAI_API_KEY" \
  --header "Content-Type: application/json" \
  --data '{
    "model": "sora2-12s",
    "prompt": "A cat walking in a garden",
    "duration": 12,
    "orientation": "landscape"
  }'

# Poll (replace TASK_ID)
curl --request GET \
  --url "https://api.viraltok.ai/api/open-api/v1/videos/TASK_ID" \
  --header "Authorization: Bearer $JIMMYAI_API_KEY"
```

Poll every 10 s until `status` is `completed`. Download `result.video_url` within 3 days.

## Step 6: Use the bundled CLI

```bash
export CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
export JIMMYAI_CLI="/path/to/jimiskills/jimmyai/scripts/jimmyai.py"

# Dry-run (no key needed)
python "$JIMMYAI_CLI" generate-image --prompt "test" --dry-run

# Live sync image
python "$JIMMYAI_CLI" generate-image --prompt "A red apple"

# Live video with auto-poll
python "$JIMMYAI_CLI" create-and-poll \
  --type video \
  --prompt "A cat in a garden" \
  --model sora2-12s \
  --duration 12
```

## Python snippet (minimal)

```python
import os, time, requests

API_KEY = os.environ["JIMMYAI_API_KEY"]
BASE = "https://api.viraltok.ai"
headers = {"Authorization": f"Bearer {API_KEY}"}

# Sync image
r = requests.post(
    f"{BASE}/api/open-api/v1/images/generations",
    headers=headers,
    json={"model": "gpt-image-2", "prompt": "A red apple", "size": "1024x1024"},
    timeout=180,
)
print(r.json())

# Async video
r = requests.post(
    f"{BASE}/api/open-api/v1/videos",
    headers=headers,
    json={
        "model": "sora2-12s",
        "prompt": "A cat in a garden",
        "duration": 12,
        "orientation": "landscape",
    },
)
task_id = r.json()["data"]["task_id"]

while True:
    q = requests.get(f"{BASE}/api/open-api/v1/videos/{task_id}", headers=headers).json()
    status = q["data"]["status"]
    print(status)
    if status in ("completed", "failed", "canceled"):
        print(q)
        break
    time.sleep(10)
```

## Node.js snippet (minimal)

```javascript
const API_KEY = process.env.JIMMYAI_API_KEY;
const BASE = "https://api.viraltok.ai";
const headers = { Authorization: `Bearer ${API_KEY}`, "Content-Type": "application/json" };

const res = await fetch(`${BASE}/api/open-api/v1/images/generations`, {
  method: "POST",
  headers,
  body: JSON.stringify({ model: "gpt-image-2", prompt: "A red apple", size: "1024x1024" }),
  signal: AbortSignal.timeout(180_000),
});
console.log(await res.json());
```

## Next steps

- Full API index: https://docs.jimmyai.cn/llms.txt
- OpenAPI spec: https://docs.jimmyai.cn/zh/api-reference/openapi.json
- Support: 2114272829@qq.com or online chat on the website
