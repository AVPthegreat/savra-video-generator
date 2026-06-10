"""Unit tests for the Iconify fetcher service."""

import unittest
from backend.services.icon_fetcher import keyword_from_hint, normalize_svg

class IconFetcherTests(unittest.TestCase):

    def test_keyword_extraction(self):
        self.assertEqual(keyword_from_hint("represents a leather wallet"), "leather wallet")
        self.assertEqual(keyword_from_hint("a visual of a padlock for security"), "padlock security")
        self.assertEqual(keyword_from_hint("depicting a network of nodes"), "network nodes")
        self.assertEqual(keyword_from_hint("synergy between teams"), "handshake")
        self.assertEqual(keyword_from_hint("innovative ideas"), "lightbulb")
        self.assertEqual(keyword_from_hint("infrastructure for the app"), "server")
        self.assertEqual(keyword_from_hint(""), "document")
        self.assertEqual(keyword_from_hint("shows nothing"), "document")

    def test_svg_normalization(self):
        raw_svg = '<svg viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg"><path d="M12 2L2 12h10v10l10-10H12V2z"/></svg>'
        normalized = normalize_svg(raw_svg)
        
        self.assertIn('viewBox="0 0 400 300"', normalized)
        self.assertIn('stroke="#1a1a1a"', normalized)
        self.assertIn('stroke-width="3"', normalized)
        self.assertIn('fill="none"', normalized)
        # Check centering transform
        self.assertIn('transform="translate(', normalized)
        self.assertIn('scale(', normalized)

if __name__ == "__main__":
    unittest.main()
