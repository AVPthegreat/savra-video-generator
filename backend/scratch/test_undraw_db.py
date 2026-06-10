"""Quick check — generates scenes via multi-stage pipeline (text-only, no SVG)."""

import sys
import os
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.services.multi_model_director import generate_enhanced_scenes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def test_pipeline():
    test_text = "The ship sailed across the ocean. Wind pushed the sails."
    scenes = generate_enhanced_scenes(test_text, target_count=1)

    if not scenes:
        logger.error("FAILED: No scenes generated.")
        return

    scene = scenes[0]
    logger.info(f"SVG Path: {scene.svg_path}")
    logger.info(f"Narration: {scene.narration[:80]}...")

    # Current pipeline returns no SVGs — text-only scenes
    assert scene.svg_path == "none://"
    assert scene.narration
    logger.info("Test passed.")


if __name__ == "__main__":
    test_pipeline()
