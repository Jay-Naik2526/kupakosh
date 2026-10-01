"""LLM abstraction (SPEC.md §4): Gemini primary, Groq fallback, JSON-schema output.

Plain REST over httpx (no vendor SDK). Keys come from the environment (GEMINI_API_KEY / GROQ_API_KEY).
`available()` is False without a key, and every caller then keeps rule-only behaviour.
Output handling: parse JSON -> validate with Pydantic -> on failure retry once (config llm.max_retries) -> else None,
and the caller marks the row needs_review.
"""
from __future__ import annotations

import json
import os
from typing import Callable

import httpx
from pydantic import BaseModel, ValidationError

from app.config import cfg

Transport = Callable[[str, str, dict], str]  # (provider, prompt, schema) -> raw text; injectable for tests


def _keys() -> dict:
    return {"gemini": os.environ.get("GEMINI_API_KEY") or None, "groq": os.environ.get("GROQ_API_KEY") or None}


def providers() -> list[str]:
    c, k = cfg()["llm"], _keys()
    return [p for p in (c["provider"], c["fallback"]) if p and k.get(p)]


def available() -> bool:
    return bool(providers())


def _gemini(prompt: str, schema: dict) -> str:
    c = cfg()["llm"]
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{c['gemini_model']}:generateContent"
    body = {"contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": c["temperature"], "responseMimeType": "application/json", "responseSchema": schema}}
    r = httpx.post(url, params={"key": _keys()["gemini"]}, json=body, timeout=c["timeout_s"])
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(prompt: str, schema: dict) -> str:
    c = cfg()["llm"]
    body = {"model": c["groq_model"], "temperature": c["temperature"], "response_format": {"type": "json_object"},
            "messages": [{"role": "system", "content": "Reply with one JSON object matching this JSON schema: " + json.dumps(schema)},
                         {"role": "user", "content": prompt}]}
    r = httpx.post("https://api.groq.com/openai/v1/chat/completions", headers={"Authorization": f"Bearer {_keys()['groq']}"},
                   json=body, timeout=c["timeout_s"])
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _ollama(prompt: str, schema: dict) -> str:
    """Local model through Ollama (offline: nothing leaves the machine). Structured output via `format`."""
    c = cfg()["llm"]
    body = {"model": c.get("local_model", "qwen2.5:7b-instruct-q4_K_M"), "prompt": prompt, "stream": False, "format": schema,
            "options": {"temperature": c["temperature"], "seed": 0, "num_ctx": 4096}}
    r = httpx.post(c.get("local_url", "http://localhost:11434") + "/api/generate", json=body, timeout=c.get("local_timeout_s", 120))
    r.raise_for_status()
    return r.json()["response"]


def local_available() -> bool:
    """True when the local Ollama server answers and has the configured model."""
    c = cfg()["llm"]
    try:
        r = httpx.get(c.get("local_url", "http://localhost:11434") + "/api/tags", timeout=2)
        return any(m.get("name") == c.get("local_model", "qwen2.5:7b-instruct-q4_K_M") for m in r.json().get("models", []))
    except (httpx.HTTPError, ValueError):
        return False


def _call(provider: str, prompt: str, schema: dict) -> str:
    return {"gemini": _gemini, "groq": _groq, "ollama": _ollama}[provider](prompt, schema)


def structured(prompt: str, schema: dict, model: type[BaseModel], transport: Transport | None = None,
               extra_check: Callable[[BaseModel], str | None] | None = None, only: list[str] | None = None) -> tuple[BaseModel | None, dict]:
    """Ask for JSON, validate with `model` (+ optional extra_check returning an error text).
    Returns (object or None, trace). Tries each configured provider; each gets 1 + max_retries attempts."""
    send = transport or _call
    trace = {"attempts": []}
    provs = only if only is not None else (providers() if transport is None else [cfg()["llm"]["provider"]])
    for prov in provs:
        p = prompt
        for attempt in range(1 + cfg()["llm"]["max_retries"]):
            try:
                raw = send(prov, p, schema)
                obj = model.model_validate(json.loads(raw))
                err = extra_check(obj) if extra_check else None
                if err is None:
                    trace["attempts"].append({"provider": prov, "ok": True})
                    trace["provider"] = prov
                    return obj, trace
            except (ValidationError, json.JSONDecodeError, KeyError, IndexError) as e:
                err = str(e)[:300]
            except httpx.HTTPError as e:
                trace["attempts"].append({"provider": prov, "ok": False, "error": f"http: {e!r}"[:200]})
                break  # provider down -> try the fallback provider
            trace["attempts"].append({"provider": prov, "ok": False, "error": err})
            p = prompt + f"\n\nYour previous answer was invalid: {err}\nReturn only valid JSON that fixes this."
    return None, trace
