"""
Model Health Check — tests every provider in the stack.

Covers:
  1. Gemini native SDK  (llm_director.py path)
  2. Groq  → OpenAI-compat  (multi_model_director primary)
  3. Cerebras → OpenAI-compat  (multi_model_director fallback 1)
  4. Gemini → OpenAI-compat  (multi_model_director fallback 2)
  5. Full _call_with_fallback() chain
  6. Local deterministic fallback (_fallback_scenes)

Run from project root:
    python -m backend.scratch.test_model_health
"""
from __future__ import annotations

import sys
import json
import time
import textwrap
from pathlib import Path

# ── ensure project root is on sys.path ────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(ROOT))

# ── colour helpers ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
CYAN   = "\033[96m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def ok(msg):   print(f"  {GREEN}✓{RESET} {msg}")
def fail(msg): print(f"  {RED}✗{RESET} {msg}")
def warn(msg): print(f"  {YELLOW}~{RESET} {msg}")
def hdr(msg):  print(f"\n{BOLD}{CYAN}{'─'*60}{RESET}\n{BOLD}{msg}{RESET}")


SAMPLE_TEXT = (
    "Bitcoin is a decentralised digital currency that enables peer-to-peer "
    "transactions without banks or governments. It runs on a public ledger "
    "called the blockchain, secured by cryptographic proof-of-work."
)

SIMPLE_PROMPT = [
    {"role": "system", "content": "Reply with ONLY valid JSON: {\"ok\": true}"},
    {"role": "user",   "content": "Ping."},
]

results: dict[str, str] = {}   # name → "pass" | "fail" | "skip"


# ══════════════════════════════════════════════════════════════════════════════
# 1. Gemini native SDK
# ══════════════════════════════════════════════════════════════════════════════
hdr("1 · Gemini native SDK (llm_director)")
try:
    from backend.core.config import get_settings
    from backend.services.llm_director import generate_scenes

    settings = get_settings()
    if not settings.gemini_api_key:
        warn("GEMINI_API_KEY not set — skipping")
        results["gemini_native"] = "skip"
    else:
        t0 = time.perf_counter()
        scenes = generate_scenes(SAMPLE_TEXT, target_count=2)
        elapsed = time.perf_counter() - t0
        assert scenes, "Empty scene list returned"
        ok(f"Generated {len(scenes)} scene(s) in {elapsed:.1f}s")
        ok(f"  scene[0]: {textwrap.shorten(scenes[0].narration, 70)!r}")
        results["gemini_native"] = "pass"
except Exception as exc:
    fail(f"Gemini native SDK failed: {exc}")
    results["gemini_native"] = "fail"


# ══════════════════════════════════════════════════════════════════════════════
# 2. Groq (primary provider)
# ══════════════════════════════════════════════════════════════════════════════
hdr("2 · Groq (primary, OpenAI-compat)")
try:
    import openai
    settings = get_settings()
    if not settings.groq_api_key:
        warn("GROQ_API_KEY not set — skipping")
        results["groq"] = "skip"
    else:
        client = openai.OpenAI(
            api_key=settings.groq_api_key,
            base_url="https://api.groq.com/openai/v1",
            timeout=15.0,
        )
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=SIMPLE_PROMPT,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        elapsed = time.perf_counter() - t0
        content = resp.choices[0].message.content
        parsed = json.loads(content)
        ok(f"Response in {elapsed:.1f}s: {content!r}")
        results["groq"] = "pass"
except Exception as exc:
    fail(f"Groq failed: {exc}")
    results["groq"] = "fail"


# ══════════════════════════════════════════════════════════════════════════════
# 3. Cerebras (fallback 1)
# ══════════════════════════════════════════════════════════════════════════════
hdr("3 · Cerebras (fallback 1, OpenAI-compat)")
try:
    settings = get_settings()
    if not settings.cerebras_api_key:
        warn("CEREBRAS_API_KEY not set — will be skipped by fallback chain (expected)")
        results["cerebras"] = "skip"
    else:
        client = openai.OpenAI(
            api_key=settings.cerebras_api_key,
            base_url="https://api.cerebras.ai/v1",
            timeout=15.0,
        )
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model="llama3.1-8b",
            messages=SIMPLE_PROMPT,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        elapsed = time.perf_counter() - t0
        content = resp.choices[0].message.content
        ok(f"Response in {elapsed:.1f}s: {content!r}")
        results["cerebras"] = "pass"
except Exception as exc:
    fail(f"Cerebras failed: {exc}")
    results["cerebras"] = "fail"


# ══════════════════════════════════════════════════════════════════════════════
# 4. Gemini via OpenAI-compat endpoint (fallback 2)
# ══════════════════════════════════════════════════════════════════════════════
hdr("4 · Gemini OpenAI-compat endpoint (fallback 2)")
try:
    settings = get_settings()
    if not settings.gemini_api_key:
        warn("GEMINI_API_KEY not set — skipping")
        results["gemini_compat"] = "skip"
    else:
        client = openai.OpenAI(
            api_key=settings.gemini_api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            timeout=20.0,
        )
        t0 = time.perf_counter()
        resp = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=SIMPLE_PROMPT,
            max_tokens=50,
            response_format={"type": "json_object"},
        )
        elapsed = time.perf_counter() - t0
        content = resp.choices[0].message.content
        ok(f"Response in {elapsed:.1f}s: {content!r}")
        results["gemini_compat"] = "pass"
except Exception as exc:
    fail(f"Gemini OpenAI-compat failed: {exc}")
    results["gemini_compat"] = "fail"


# ══════════════════════════════════════════════════════════════════════════════
# 5. Full _call_with_fallback() chain (as used at runtime)
# ══════════════════════════════════════════════════════════════════════════════
hdr("5 · Full _call_with_fallback() chain (runtime simulation)")
try:
    from backend.services.multi_model_director import _call_with_fallback, _LLMConfig, _GROQ_BASE, _CEREBRAS_BASE, _GEMINI_BASE
    settings = get_settings()
    configs = [
        _LLMConfig("groq",     settings.groq_api_key,     _GROQ_BASE,     "llama-3.3-70b-versatile"),
        _LLMConfig("cerebras", settings.cerebras_api_key, _CEREBRAS_BASE, "llama3.3-70b"),
        _LLMConfig("gemini",   settings.gemini_api_key,   _GEMINI_BASE,   "gemini-2.5-flash"),
    ]
    configured = [c.name for c in configs if c.api_key]
    warn(f"Providers with keys: {configured}")

    t0 = time.perf_counter()
    content = _call_with_fallback(
        configs,
        messages=SIMPLE_PROMPT,
        max_tokens=50,
    )
    elapsed = time.perf_counter() - t0
    ok(f"Chain succeeded in {elapsed:.1f}s via first responding provider")
    ok(f"Response: {content!r}")
    results["fallback_chain"] = "pass"
except Exception as exc:
    fail(f"Fallback chain failed: {exc}")
    results["fallback_chain"] = "fail"


# ══════════════════════════════════════════════════════════════════════════════
# 6. Local deterministic fallback (_fallback_scenes)
# ══════════════════════════════════════════════════════════════════════════════
hdr("6 · Local deterministic fallback (_fallback_scenes)")
try:
    from backend.services.llm_director import _fallback_scenes
    scenes = _fallback_scenes(SAMPLE_TEXT, target_count=3, reason="health-check test")
    assert len(scenes) >= 1, "Should produce at least 1 scene"
    ok(f"Produced {len(scenes)} scene(s) with no API calls")
    for s in scenes:
        ok(f"  scene {s.scene_id}: {textwrap.shorten(s.narration, 60)!r}")
        assert s.svg_markup and s.svg_markup.startswith("<svg"), "svg_markup looks malformed"
    results["local_fallback"] = "pass"
except Exception as exc:
    fail(f"Local fallback failed: {exc}")
    results["local_fallback"] = "fail"


# ══════════════════════════════════════════════════════════════════════════════
# Summary
# ══════════════════════════════════════════════════════════════════════════════
hdr("Summary")
all_pass = True
rows = {
    "gemini_native":   "Gemini native SDK",
    "groq":            "Groq (primary)",
    "cerebras":        "Cerebras (fallback 1)",
    "gemini_compat":   "Gemini OpenAI-compat (fallback 2)",
    "fallback_chain":  "_call_with_fallback() chain",
    "local_fallback":  "Local deterministic fallback",
}
for key, label in rows.items():
    status = results.get(key, "skip")
    if status == "pass":
        print(f"  {GREEN}PASS{RESET}  {label}")
    elif status == "skip":
        print(f"  {YELLOW}SKIP{RESET}  {label}")
    else:
        print(f"  {RED}FAIL{RESET}  {label}")
        all_pass = False

print()
if all_pass:
    print(f"{GREEN}{BOLD}All checks passed (or intentionally skipped).{RESET}")
else:
    print(f"{RED}{BOLD}Some checks FAILED — see output above.{RESET}")
    sys.exit(1)
