"""Minimal client for Gemma 4 via the Gemini API (REST, no SDK needed)."""
import base64
import json
import os
import re
import time

import requests

API_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemma-4-26b-a4b-it"


class GemmaError(RuntimeError):
    pass


def ask_gemma(prompt, images=None, model=None, api_key=None, retries=2):
    """Send a prompt (plus optional images as (bytes, mime) tuples) to Gemma 4.

    Returns the model's text answer (thinking parts are dropped).
    """
    model = model or os.environ.get("GUARD_MODEL") or DEFAULT_MODEL
    api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise GemmaError("GEMINI_API_KEY is not set")

    parts = []
    for data, mime in images or []:
        parts.append({"inline_data": {"mime_type": mime, "data": base64.b64encode(data).decode()}})
    parts.append({"text": prompt})

    body = {
        "contents": [{"role": "user", "parts": parts}],
        "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
    }

    last_err = None
    for attempt in range(retries + 1):
        try:
            r = requests.post(
                API_URL.format(model=model),
                headers={"x-goog-api-key": api_key, "Content-Type": "application/json"},
                json=body,
                timeout=120,
            )
            if r.status_code == 200:
                data = r.json()
                cand = (data.get("candidates") or [{}])[0]
                texts = [
                    p.get("text", "")
                    for p in cand.get("content", {}).get("parts", [])
                    if not p.get("thought")
                ]
                text = "".join(texts).strip()
                if text:
                    return text
                last_err = f"empty response: {json.dumps(data)[:300]}"
            else:
                last_err = f"HTTP {r.status_code}: {r.text[:300]}"
                if r.status_code < 500 and r.status_code != 429:
                    break
        except requests.RequestException as e:
            last_err = str(e)
        time.sleep(2 * (attempt + 1))
    raise GemmaError(last_err)


def extract_json(text):
    """Pull the first JSON object out of a model reply (handles ```json fences and chatter)."""
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.S)
    candidate = fenced.group(1) if fenced else None
    if candidate is None:
        start = text.find("{")
        if start == -1:
            raise ValueError("no JSON object in model reply")
        depth = 0
        for i, ch in enumerate(text[start:], start):
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start : i + 1]
                    break
    if candidate is None:
        raise ValueError("unbalanced JSON in model reply")
    return json.loads(candidate)
