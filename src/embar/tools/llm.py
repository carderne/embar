"""Wrapper for Anthropic API"""

import json
from typing import Protocol
from urllib.request import Request, urlopen


class Llm(Protocol):
    def __call__(self, api_key: str, prompt: str, max_tokens: int = 2000) -> str: ...


def call_anthropic(api_key: str, prompt: str, max_tokens: int = 2000) -> str:
    """Make a request to Anthropic API using urllib."""
    url = "https://api.anthropic.com/v1/messages"

    data = {
        "model": "claude-3-5-haiku-20241022",
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }

    headers = {"Content-Type": "application/json", "x-api-key": api_key, "anthropic-version": "2023-06-01"}

    request = Request(url, data=json.dumps(data).encode("utf-8"), headers=headers, method="POST")

    with urlopen(request) as response:
        result = json.loads(response.read().decode("utf-8"))
        return result["content"][0]["text"]
