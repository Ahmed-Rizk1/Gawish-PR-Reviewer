import os
import httpx
from groq import AsyncGroq

from app.models.webhook import WebhookPayload
from app.core.config import GITHUB_TOKEN

GITHUB_API = "https://api.github.com"

REVIEW_PROMPT = """You are an expert code reviewer. Analyze the following Git diff and provide a structured review with these sections:

## Summary
A brief overview of what this PR does.

## Bugs & Issues
List any bugs, logic errors, or potential runtime issues found.

## Clean Code Suggestions
List improvements for readability, naming, structure, or best practices.

## Security Concerns
Flag any security issues (e.g., exposed secrets, injection risks, improper auth).

Diff:
{diff}
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
