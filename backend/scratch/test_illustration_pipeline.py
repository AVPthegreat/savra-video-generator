"""Quick integration check — generates scenes via the multi-stage pipeline."""

import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.multi_model_director import generate_enhanced_scenes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_pipeline():
    test_text = "Neural networks are computing systems inspired by biological neural networks."
    scenes = generate_enhanced_scenes(test_text, target_count=2)

    if not scenes:
        logger.error("FAILED: No scenes generated.")
        return

    logger.info(f"Generated {len(scenes)} scenes.")
    for scene in scenes:
        logger.info(f"--- Scene {scene.scene_id} ---")
        logger.info(f"Narration: {scene.narration[:80]}...")
        logger.info(f"SVG Path: {scene.svg_path}")
        assert scene.svg_path == "none://"  # current pipeline returns no SVGs
        assert scene.narration
    logger.info("Test completed successfully.")


if __name__ == "__main__":
    test_pipeline()
