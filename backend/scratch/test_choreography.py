import sys
import os
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from backend.main import _synthesize_scene_choreography
from backend.core.schemas import SceneScript
from backend.services.icon_fetcher import keyword_from_hint, fetch_icon_svg, normalize_svg
import json

def test_choreography():
    print("--- Testing Scene Choreography & SVG Normalization ---")
    
    # Mock scene from LLM
    scene = SceneScript(
        scene_id=1,
        narration="Bitcoin is digital gold.",
        metaphor_hint="gold bar"
    )
    
    # We'll run the logic manually to see intermediate steps
    keyword = keyword_from_hint(scene.metaphor_hint)
    print(f"Keyword: {keyword}")
    
    raw_svg = fetch_icon_svg(keyword)
    if not raw_svg:
        print("Failed to fetch icon, trying simple 'gold'")
        raw_svg = fetch_icon_svg("gold")
        
    if raw_svg:
        print(f"Fetched raw SVG (sample): {raw_svg[:100]}...")
        
        normalized = normalize_svg(raw_svg)
        print(f"\nNormalized SVG (sample): {normalized[:150]}...")
        
        # Check for our whiteboard standards
        if 'viewBox="0 0 400 300"' in normalized:
            print("  [PASS] viewBox is 0 0 400 300")
        if 'stroke="#1a1a1a"' in normalized:
            print("  [PASS] stroke color is #1a1a1a")
        if 'stroke-width="3"' in normalized:
            print("  [PASS] stroke-width is 3")
        if 'fill="none"' in normalized:
            print("  [PASS] fill is none")
            
        # Element count for duration
        element_count = (
            normalized.count('<path') + normalized.count('<circle') +
            normalized.count('<rect') + normalized.count('<line') +
            normalized.count('<polyline') + normalized.count('<ellipse')
        )
        print(f"\nElement count: {element_count}")
        
        duration_ms = 5000 # mock 5s audio
        element_factor = min(1.0, element_count / 12)
        draw_duration_ms = int(duration_ms * 0.35 * (0.5 + 0.5 * element_factor))
        print(f"Draw duration for {duration_ms}ms audio: {draw_duration_ms}ms")
        
    else:
        print("Could not fetch any icon.")

if __name__ == "__main__":
    # Mock audio synthesis to avoid edge-tts dependency issues in scratch
    import backend.main
    backend.main.synthesize = lambda text, path: 5000 
    
    test_choreography()
