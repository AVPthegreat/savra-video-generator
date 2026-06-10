"""Shared utilities for all agents — LLM fallback chain, JSON parsing, config."""

from __future__ import annotations

import json
import logging
import re

import openai

from backend.core.config import get_settings

logger = logging.getLogger("backend.agents.base")

_GROQ_BASE = "https://api.groq.com/openai/v1"
_CEREBRAS_BASE = "https://api.cerebras.ai/v1"
_GEMINI_BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


def _is_rate_limited(exc: Exception) -> bool:
    s = str(exc).lower()
    return any(k in s for k in ("429", "rate limit", "quota", "resource_exhausted", "too many"))


def llm_call(
    messages: list[dict],
    max_tokens: int,
    temperature: float = 0.3,
    json_mode: bool = True,
) -> str:
    """Call the LLM with automatic fallback across Groq → Cerebras → Gemini."""
    providers = [
        ("groq", "meta-llama/llama-4-scout-17b-16e-instruct", _GROQ_BASE),
        ("cerebras", "llama3.1-8b", _CEREBRAS_BASE),
        ("gemini", "gemini-2.5-flash", _GEMINI_BASE),
    ]
    s = get_settings()
    keys = {
        "groq": s.groq_api_key,
        "cerebras": s.cerebras_api_key,
        "gemini": s.gemini_api_key,
    }
    last_exc: Exception = RuntimeError("No LLM providers configured with valid API keys")
    for name, model, base_url in providers:
        api_key = keys[name]
        if not api_key:
            continue
        try:
            client = openai.OpenAI(api_key=api_key, base_url=base_url, timeout=15.0)
            kwargs = dict(model=model, messages=messages, temperature=temperature, max_tokens=max_tokens)
            if json_mode:
                kwargs["response_format"] = {"type": "json_object"}
            response = client.chat.completions.create(**kwargs)
            if name != "groq":
                logger.info("LLM call served by fallback provider: %s/%s", name, model)
            return response.choices[0].message.content
        except Exception as exc:
            last_exc = exc
            reason = "rate-limited" if _is_rate_limited(exc) else "failed"
            logger.warning("%s %s, trying next: %s", name, reason, exc)
    raise last_exc


def parse_json(content: str) -> dict:
    content = content.strip()
    content = re.sub(r'^```(?:json)?\s*', '', content)
    content = re.sub(r'\s*```$', '', content)
    return json.loads(content.strip())
