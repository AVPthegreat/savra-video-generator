#!/usr/bin/env python3
"""
Run this BEFORE the pipeline to verify Gemini is generating real SVGs.

Usage:
    cd document_to_video_pipeline
    python test_svg_gen.py

It will print the raw Gemini response and save the SVGs to test_output/
so you can open them in a browser and see what they look like.
"""
import json
import re
import sys
from pathlib import Path

# Use the backend settings loader for consistent configuration.
try:
    from backend.core.config import get_settings

    settings = get_settings()
    GEMINI_API_KEY = settings.gemini_api_key
    GEMINI_MODEL = settings.gemini_model
except Exception as exc:
    print(f"ERROR: Could not load backend settings: {exc}")
    print("Make sure you have a .env file or GEMINI_API_KEY set in your environment.")
    sys.exit(1)

if not GEMINI_API_KEY:
    print("ERROR: GEMINI_API_KEY not set in environment or .env file")
    sys.exit(1)

TEST_TEXT = """
Bitcoin is a digital currency that lets people send money directly to each other
over the internet, without needing a bank. Transactions are verified by a network
of computers and recorded on a public ledger called the blockchain.
"""

PROMPT = """
You are a whiteboard animation artist. Convert this text into 2 whiteboard animation scenes.

For each scene, draw a DETAILED hand-drawn SVG illustration.

STRICT SVG RULES:
- viewBox MUST be "0 0 400 300"  
- Use ONLY: <path>, <circle>, <rect>, <line>, <ellipse> elements
- Every element: fill="none" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"
- Draw RECOGNISABLE illustrations with 8-15 elements — NOT just a box with a label
- NO <text> elements, NO <image>, NO <defs>, NO gradients

EXAMPLE of a good wallet SVG (copy this style exactly):
<svg viewBox="0 0 400 300" xmlns="http://www.w3.org/2000/svg">
  <path d="M60,70 L60,230 Q60,245 75,245 L325,245 Q340,245 340,230 L340,70 Q340,55 325,55 L75,55 Q60,55 60,70 Z" fill="none" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
  <path d="M60,110 L340,110" fill="none" stroke="#1a1a1a" stroke-width="3"/>
  <path d="M240,110 L240,160 Q240,175 255,175 L310,175 Q325,175 325,160 L325,110" fill="none" stroke="#1a1a1a" stroke-width="3" stroke-linecap="round"/>
  <circle cx="282" cy="142" r="12" fill="none" stroke="#1a1a1a" stroke-width="3"/>
  <path d="M90,140 L160,140" fill="none" stroke="#1a1a1a" stroke-width="2.5"/>
  <path d="M90,160 L180,160" fill="none" stroke="#1a1a1a" stroke-width="2.5"/>
  <path d="M90,180 L150,180" fill="none" stroke="#1a1a1a" stroke-width="2"/>
  <path d="M90,200 L170,200" fill="none" stroke="#1a1a1a" stroke-width="2"/>
</svg>

OUTPUT: ONLY a JSON array. No markdown. No explanation.
[
  {
    "scene_id": 1,
    "narration": "spoken explanation",
    "svg_markup": "<svg viewBox='0 0 400 300' xmlns='http://www.w3.org/2000/svg'>...8+ elements...</svg>",
    "metaphor_hint": "what the drawing represents"
  }
]

INPUT TEXT:
""" + TEST_TEXT.strip()


def main():
    try:
        from google import genai
    except ImportError:
        print("ERROR: google-genai not installed. Run: pip install google-genai")
        sys.exit(1)

    print(f"Using model: {GEMINI_MODEL}")
    print(f"Sending prompt ({len(PROMPT)} chars)...")

    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(model=GEMINI_MODEL, contents=PROMPT)
    raw = response.text
    
    print("\n" + "="*60)
    print("RAW GEMINI RESPONSE:")
    print("="*60)
    print(raw[:3000])  # Print first 3000 chars
    print("="*60 + "\n")

    # Try to parse
    try:
        # Strip markdown fences if present
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
            cleaned = re.sub(r"```$", "", cleaned).strip()
        start = cleaned.find("[")
        end = cleaned.rfind("]")
        if start != -1 and end != -1:
            cleaned = cleaned[start:end+1]
        
        scenes = json.loads(cleaned)
        print(f"✅ Successfully parsed {len(scenes)} scene(s)")

        # Save SVGs for visual inspection
        out_dir = Path("test_output")
        out_dir.mkdir(exist_ok=True)

        for scene in scenes:
            sid = scene.get("scene_id", "?")
            svg = scene.get("svg_markup", "")
            narration = scene.get("narration", "")
            
            # Count drawable elements
            path_count = len(re.findall(r'<(path|line|polyline|polygon|circle|rect|ellipse)\b', svg))
            
            print(f"\nScene {sid}: {path_count} drawable elements")
            print(f"  Narration: {narration[:80]}...")
            
            svg_file = out_dir / f"scene_{sid}.svg"
            svg_file.write_text(svg, encoding="utf-8")
            print(f"  ✅ Saved to {svg_file} — open in browser to inspect")

        print(f"\nAll SVGs saved to test_output/")
        print("Open them in your browser to check if the drawings look correct.")
        print("If they look like boxes with labels → Gemini is ignoring the prompt.")
        print("If they look like real drawings → the pipeline SVG rendering is the issue.")

    except json.JSONDecodeError as e:
        print(f"❌ JSON parse failed: {e}")
        print("Gemini returned invalid JSON. Raw response saved to test_output/raw_response.txt")
        out_dir = Path("test_output")
        out_dir.mkdir(exist_ok=True)
        (out_dir / "raw_response.txt").write_text(raw, encoding="utf-8")


if __name__ == "__main__":
    main()
