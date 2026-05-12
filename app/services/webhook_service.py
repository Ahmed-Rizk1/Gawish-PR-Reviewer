import os
import httpx
from groq import AsyncGroq

from app.models.webhook import WebhookPayload
from app.core.config import GITHUB_TOKEN

GITHUB_API = "https://api.github.com"

REVIEW_PROMPT = """You are an expert Senior Software Engineer and Security Researcher. Analyze the following concatenated Git diffs from the pull request and provide a professional and constructive review.

You MUST format your response using the exact structure below, including emojis, the summary table, and HTML details tags for code blocks.

| Category | Status |
| :--- | :--- |
| Security | [Pass/Warning] |
| Performance | [Optimal/Review Needed] |

## 🚀 Summary
A brief overview of what this PR does.

## ⚠️ Bugs & Issues
List any bugs, logic errors, or potential runtime issues found.

## ✅ Security Check
Detect hardcoded keys, SQL injection risks, or insecure imports.

## ⚡ Performance
Look for inefficient loops or unnecessary memory usage.

## 💡 Clean Code Suggestions
Check for naming conventions (PEP 8), missing docstrings, readability, structure, and best practices.

IMPORTANT FORMATTING RULES:
- Wrap any suggested code fixes or large code blocks inside HTML `<details>` tags like this:
<details><summary><b>Click to see suggested code fixes</b></summary>

```python
# your code here
```
</details>
- Always ensure code blocks have the correct language identifier (e.g., ```python).

Diffs:
{diff}
"""

REPLY_PROMPT = """You are an expert Senior Software Engineer and Security Researcher participating in a discussion about a code review.
Be concise, defend your suggestions if they are correct, or acknowledge if the user has a better point.

Code Diff:
{diff}

Discussion Thread:
{comments}
"""


class WebhookService:
    def __init__(self):
        self._client = AsyncGroq(api_key=os.getenv("GROQ_API_KEY"))

    async def handle_event(self, payload: WebhookPayload) -> dict:
        full_name = payload.repository["full_name"]
        pr_number = payload.pull_request["number"]

        diff = await self._fetch_diff(full_name, pr_number)
        review = await self._analyze_diff(diff)
        await self._post_comment(full_name, pr_number, review)

        print(review)
        return {"status": "success", "review": review}

    async def handle_comment(self, payload: WebhookPayload) -> dict:
        if payload.action != "created":
            return {"status": "ignored", "reason": "Not a created comment"}
        
        if not payload.issue or "pull_request" not in payload.issue:
            return {"status": "ignored", "reason": "Not a PR comment"}
            
        if payload.sender and payload.sender.get("type") == "Bot":
            return {"status": "ignored", "reason": "Bot comment"}
            
        full_name = payload.repository["full_name"]
        pr_number = payload.issue["number"]
        
        diff = await self._fetch_diff(full_name, pr_number)
        comments_text = await self._fetch_comments(full_name, pr_number)
        
        reply = await self._generate_reply(diff, comments_text)
        await self._post_comment(full_name, pr_number, reply)
        
        return {"status": "success", "reply": reply}

    async def _fetch_comments(self, full_name: str, pr_number: int) -> str:
        url = f"{GITHUB_API}/repos/{full_name}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            comments = response.json()
            return "\n\n".join([f"{c['user']['login']}: {c['body']}" for c in comments])

    async def _generate_reply(self, diff: str, comments: str) -> str:
        prompt = REPLY_PROMPT.format(diff=diff, comments=comments)
        chat_completion = await self._client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content

    async def _fetch_diff(self, full_name: str, pr_number: int) -> str:
        url = f"{GITHUB_API}/repos/{full_name}/pulls/{pr_number}"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github.v3.diff",
        }
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers, follow_redirects=True)
            response.raise_for_status()
            return response.text

    async def _analyze_diff(self, diff: str) -> str:
        prompt = REVIEW_PROMPT.format(diff=diff)
        chat_completion = await self._client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
        )
        return chat_completion.choices[0].message.content

    async def _post_comment(self, full_name: str, pr_number: int, body: str) -> None:
        url = f"{GITHUB_API}/repos/{full_name}/issues/{pr_number}/comments"
        headers = {
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Accept": "application/vnd.github+json",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, json={"body": body})
            response.raise_for_status()
