import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.services.llm_director import generate_scenes
from backend.services.icon_fetcher import keyword_from_hint, fetch_icon_svg
from backend.core.config import get_settings

def test_pipeline():
    test_text = "Bitcoin is a decentralized digital currency without a central bank or single administrator."
    print(f"--- Testing Pipeline with text: {test_text} ---")
    
    try:
        # 1. Generate Scenes (LLM)
        print("\n[1/3] Generating scenes with Gemini...")
        scenes = generate_scenes(test_text, target_count=1)
        for s in scenes:
            print(f"  Scene {s.scene_id}:")
            print(f"    Narration: {s.narration}")
            print(f"    Metaphor: {s.metaphor_hint}")
            
            # 2. Extract Keyword
            keyword = keyword_from_hint(s.metaphor_hint)
            print(f"\n[2/3] Extracted keyword: '{keyword}'")
            
            # 3. Fetch Icon
            print(f"\n[3/3] Fetching icon for '{keyword}'...")
            settings = get_settings()
            svg = fetch_icon_svg(keyword, settings.iconify_base_url)
            
            if svg:
                print(f"  SUCCESS: Fetched SVG (length: {len(svg)})")
                if '<path' in svg or '<circle' in svg:
                    print("  SVG contains expected path/circle elements.")
            else:
                print("  FAILURE: Could not fetch SVG from Iconify.")
                
    except Exception as e:
        print(f"\nERROR: {e}")
        if "GEMINI_API_KEY" in str(e):
            print("\nTIP: Set GEMINI_API_KEY in your environment to test with the real LLM.")

if __name__ == "__main__":
    test_pipeline()
