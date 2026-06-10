"""Iconify SVG asset fetcher.

Fetches real, human-designed SVG icons from the Iconify public API
based on a keyword extracted from the LLM's metaphor hint.

Flow:
  metaphor_hint -> keyword_from_hint() -> fetch_icon_svg() -> normalize_svg()

Falls back gracefully to None on any network/parse failure so callers
can use existing hardcoded templates as a safety net.
"""

from __future__ import annotations

import logging
import os
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# Local disk cache for successful Iconify fetches (avoids repeat network calls)
_ICONIFY_CACHE_DIR = Path(os.environ.get("ASSET_CACHE_DIR", "/tmp/iconify_cache"))

# ---------------------------------------------------------------------------
# Preferred icon set prefixes (tried in order for search result selection)
# ---------------------------------------------------------------------------
_PREFERRED_PREFIXES = ("tabler", "lucide", "carbon", "material-symbols", "ph", "mdi")

# Icon set prefixes that contain brand logos, emoji, or game art — always skip
_EXCLUDED_PREFIXES = frozenset((
    "simple-icons", "logos", "game-icons", "circle-flags", "flag",
    "twemoji", "noto", "openmoji", "emojione", "fxemoji", "fa-brands",
))

# ---------------------------------------------------------------------------
# Abstract-word fallback map — for terms the LLM produces that have no
# direct icon equivalent. Maps to a more concrete, searchable keyword.
# ---------------------------------------------------------------------------
_ABSTRACT_MAP: dict[str, str] = {
    "synergy": "handshake",
    "paradigm": "lightbulb",
    "scalability": "expand",
    "infrastructure": "server",
    "framework": "grid",
    "ecosystem": "network",
    "innovation": "lightbulb",
    "innovative": "lightbulb",
    "transformation": "arrow-right",
    "alignment": "target",
    "collaboration": "users",
    "communication": "message",
    "disruption": "zap",
    "strategy": "map",
    "optimization": "settings",
    "automation": "robot",
    "integration": "plug",
    "analytics": "chart-bar",
    "visibility": "eye",
    "transparency": "eye",
    "efficiency": "bolt",
    "productivity": "trending-up",
    "resilience": "shield",
    "governance": "shield-check",
    "compliance": "clipboard-check",
    "architecture": "layout",
    "deployment": "upload",
    "monitoring": "activity",
    "pipeline": "git-merge",
    "workflow": "git-branch",
    "agility": "refresh",
    "sustainability": "leaf",
    "empowerment": "hand",
    "engagement": "heart",
    "onboarding": "user-plus",
    "stakeholder": "briefcase",
    "milestone": "flag",
    "insight": "lightbulb",
    "outcome": "check-circle",
    # Tech / software
    "container": "package",
    "containers": "package",
    "docker": "package",
    "image": "file-code",
    "images": "file-code",
    "volume": "database",
    "volumes": "database",
    "layer": "layers",
    "layers": "layers",
    "machine": "laptop",
    "machines": "server",
    "process": "cpu",
    "processes": "cpu",
    "portable": "laptop",
    "portability": "laptop",
    "isolation": "lock",
    "isolated": "lock",
    "isolate": "lock",
    "blueprint": "file-code",
    "blueprints": "file-code",
    "shipping": "package",
    "ship": "rocket",
    "lightweight": "feather",
    "application": "layout",
    "app": "layout",
    "service": "server",
    "services": "server",
    "data": "database",
    "storage": "hard-drive",
    "security": "shield",
    "performance": "activity",
    "scaling": "trending-up",
    "dependency": "link",
    "dependencies": "link",
    "configuration": "settings",
    "runtime": "play-circle",
    "cluster": "network",
    "orchestration": "git-branch",
    "microservice": "plug",
    "microservices": "plug",
    "registry": "archive",
    "version": "tag",
    "versioning": "tag",
    "rollback": "rotate-ccw",
    "backup": "save",
    "replication": "copy",
    "proxy": "shield",
    "authentication": "key",
    "encryption": "lock",
    "build": "tool",
    "builds": "tool",
    "test": "check-square",
    "testing": "check-square",
    "problem": "alert-circle",
    "solution": "check-circle",
    "environment": "globe",
    "environments": "globe",
    "resource": "box",
    "resources": "box",
    "deploy": "rocket",
    "deployment": "rocket",
    "package": "package",
    "packages": "package",
    "server": "server",
    "servers": "server",
    "cloud": "cloud",
    "network": "network",
    "api": "plug",
    "code": "code",
    "developer": "code",
    "system": "cpu",
}

# Words to strip when extracting the core keyword from a metaphor hint
_FILLER_WORDS = frozenset({
    "a", "an", "the", "this", "that", "these", "those",
    "represents", "represent", "depicting", "depicts", "shows", "show", "nothing",
    "visual", "visually", "metaphor", "of", "for", "with", "as", "in",
    "on", "at", "by", "to", "from", "is", "are", "concept", "concepts", "idea", "ideas",
    "notion", "notions", "illustration", "image", "icon", "symbol", "diagram",
    "showing", "showing", "demonstrates", "demonstrated", "scene", "scenes",
    "step", "steps", "internal", "mechanism", "mechanisms",
})


def keyword_from_hint(metaphor_hint: str) -> str:
    """Extract the most relevant 1–2 word search keyword from a metaphor hint.

    Strategy:
    1. Strip filler/meta words
    2. Check remaining words against abstract fallback map
    3. Return first concrete noun/verb phrase found
    4. If still abstract, return the first two non-filler words
    """
    if not metaphor_hint:
        return "document"

    # Lowercase, remove punctuation except hyphens
    cleaned = re.sub(r"[^\w\s-]", " ", metaphor_hint.lower())
    words = [w for w in cleaned.split() if w and w not in _FILLER_WORDS and len(w) > 2]

    if not words:
        return "document"

    # Check each word against abstract map
    for word in words:
        if word in _ABSTRACT_MAP:
            return _ABSTRACT_MAP[word]

    # Return first 1–2 meaningful words as the search term
    return " ".join(words[:2]) if len(words) >= 2 else words[0]


def fetch_icon_svg(
    keyword: str,
    base_url: str = "https://api.iconify.design",
    exclude_names: set[str] | None = None,
) -> Optional[tuple[str, str]]:
    """Search Iconify for keyword and return (icon_name, raw_svg).

    Returns None on any failure (network error, timeout, no results, bad SVG).
    Successful fetches are cached to disk to avoid repeat network calls.
    Pass exclude_names to skip already-used icon identifiers (e.g. "tabler:container").
    """
    if not keyword or not keyword.strip():
        return None

    excluded = exclude_names or set()
    cache_key = re.sub(r"[^\w-]", "_", keyword.strip().lower())
    cache_file = _ICONIFY_CACHE_DIR / f"{cache_key}.svg"
    name_file = _ICONIFY_CACHE_DIR / f"{cache_key}.name"

    # Check disk cache (skip if cached icon is excluded or from a blocked prefix)
    if cache_file.exists():
        cached_name = name_file.read_text(encoding="utf-8").strip() if name_file.exists() else ""
        if cached_name:
            cached_prefix = cached_name.split(":")[0] if ":" in cached_name else ""
            if cached_name not in excluded and cached_prefix not in _EXCLUDED_PREFIXES:
                logger.debug("icon_fetcher: cache hit for '%s'", keyword)
                return (cached_name, cache_file.read_text(encoding="utf-8"))
            logger.debug("icon_fetcher: cache hit for '%s' blocked (%s), re-fetching", keyword, cached_name)
        elif not excluded:
            # Old cache without .name file — safe to use when dedup is not active
            logger.debug("icon_fetcher: cache hit (legacy) for '%s'", keyword)
            return (keyword, cache_file.read_text(encoding="utf-8"))
        # Old cache + active exclusions/blocked prefix: fall through to network fetch

    prefixes = ",".join(_PREFERRED_PREFIXES)
    search_url = f"{base_url}/search"

    try:
        resp = requests.get(
            search_url,
            params={"query": keyword, "prefixes": prefixes, "limit": 10},
            timeout=3.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("icon_fetcher: search request failed for '%s': %s", keyword, exc)
        return None

    icons: list[str] = data.get("icons", [])
    if not icons:
        logger.debug("icon_fetcher: no results for keyword '%s'", keyword)
        return None

    # Pick the first non-excluded result matching a preferred prefix (in priority order)
    chosen: str | None = None
    for prefix in _PREFERRED_PREFIXES:
        for icon_name in icons:
            if icon_name.startswith(f"{prefix}:") and icon_name not in excluded:
                chosen = icon_name
                break
        if chosen:
            break

    # Fallback to first non-excluded result — still block brand/emoji sets
    if not chosen:
        for icon_name in icons:
            prefix_part = icon_name.split(":")[0] if ":" in icon_name else ""
            if icon_name not in excluded and prefix_part not in _EXCLUDED_PREFIXES:
                chosen = icon_name
                break

    if not chosen:
        logger.debug("icon_fetcher: all results excluded for keyword '%s'", keyword)
        return None

    # Fetch the SVG file
    prefix_part, name_part = chosen.split(":", 1)
    svg_url = f"{base_url}/{prefix_part}/{name_part}.svg"

    try:
        svg_resp = requests.get(svg_url, timeout=3.0)
        svg_resp.raise_for_status()
        raw_svg = svg_resp.text.strip()
    except Exception as exc:
        logger.warning("icon_fetcher: SVG fetch failed for '%s': %s", chosen, exc)
        return None

    if not raw_svg.startswith("<"):
        logger.warning("icon_fetcher: unexpected response format for '%s'", chosen)
        return None

    logger.info("icon_fetcher: fetched %s for keyword '%s'", chosen, keyword)

    # Write to disk cache for future requests
    try:
        _ICONIFY_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file.write_text(raw_svg, encoding="utf-8")
        name_file.write_text(chosen, encoding="utf-8")
    except Exception as cache_exc:
        logger.debug("icon_fetcher: cache write failed: %s", cache_exc)

    return (chosen, raw_svg)


def normalize_svg(raw_svg: str) -> str:
    """Normalize a fetched Iconify SVG for the whiteboard animation pipeline.

    Transformations applied:
    - Rescale and center to viewBox "0 0 400 300"
    - Strip fill; set stroke attrs to whiteboard style
    - Remove <defs>, <style>, <mask>, <clipPath>
    - Remove paint-server and class attributes
    """
    # Register namespaces to avoid ns0: prefixes in output
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

    try:
        root = ET.fromstring(raw_svg)
    except ET.ParseError as exc:
        logger.warning("icon_fetcher: SVG parse error during normalization: %s", exc)
        return raw_svg  # return as-is; SvgDrawer will handle best-effort

    ns = {"svg": "http://www.w3.org/2000/svg"}
    svg_ns = "http://www.w3.org/2000/svg"

    # -- Parse original viewBox to compute centering transform ----------------
    orig_viewbox = root.get("viewBox", "0 0 24 24")
    try:
        vb_parts = [float(v) for v in orig_viewbox.replace(",", " ").split()]
        if len(vb_parts) == 4:
            _, _, vb_w, vb_h = vb_parts
        else:
            vb_w, vb_h = 24.0, 24.0
    except ValueError:
        vb_w, vb_h = 24.0, 24.0

    # Target canvas: 400x300, with 40px padding each side
    target_w, target_h = 320.0, 220.0
    scale = min(target_w / vb_w, target_h / vb_h)
    scaled_w = vb_w * scale
    scaled_h = vb_h * scale
    tx = (400 - scaled_w) / 2
    ty = (300 - scaled_h) / 2

    # -- Update root SVG attributes ------------------------------------------
    root.set("viewBox", "0 0 400 300")
    root.set("xmlns", svg_ns)
    for attr in ("width", "height", "class", "style", "id"):
        root.attrib.pop(attr, None)

    # -- Remove unwanted structural elements ----------------------------------
    _STRIP_TAGS = {
        f"{{{svg_ns}}}defs",
        f"{{{svg_ns}}}style",
        f"{{{svg_ns}}}mask",
        f"{{{svg_ns}}}clipPath",
        f"{{{svg_ns}}}filter",
        f"{{{svg_ns}}}linearGradient",
        f"{{{svg_ns}}}radialGradient",
        f"{{{svg_ns}}}pattern",
        f"{{{svg_ns}}}symbol",
        f"{{{svg_ns}}}title",
        f"{{{svg_ns}}}desc",
    }
    for elem in root.findall(".//*"):
        if elem.tag in _STRIP_TAGS:
            parent = _find_parent(root, elem)
            if parent is not None:
                parent.remove(elem)

    # -- Wrap all children in a scaling <g> -----------------------------------
    # Collect current direct children
    children = list(root)
    wrapper = ET.SubElement(root, f"{{{svg_ns}}}g")
    wrapper.set("transform", f"translate({tx:.2f},{ty:.2f}) scale({scale:.4f})")

    # Move children into wrapper (must remove then re-add since ET has no reparent)
    for child in children:
        root.remove(child)
        wrapper.append(child)

    # -- Normalize stroke/fill on all shape elements --------------------------
    _SHAPE_TAGS = {
        f"{{{svg_ns}}}path",
        f"{{{svg_ns}}}circle",
        f"{{{svg_ns}}}rect",
        f"{{{svg_ns}}}line",
        f"{{{svg_ns}}}polyline",
        f"{{{svg_ns}}}polygon",
        f"{{{svg_ns}}}ellipse",
        f"{{{svg_ns}}}g",
    }
    _REMOVE_ATTRS = {"fill-rule", "clip-rule", "clip-path", "mask", "filter", "class", "id", "style"}

    for elem in root.iter():
        if elem.tag not in _SHAPE_TAGS:
            continue

        # Remove unwanted attributes
        for attr in list(elem.attrib):
            if attr in _REMOVE_ATTRS:
                del elem.attrib[attr]

        # Only apply stroke/fill to actual shape elements (not <g> wrappers)
        if elem.tag != f"{{{svg_ns}}}g":
            current_fill = elem.get("fill", "").strip().lower()
            # Preserve non-white, non-black color fills (e.g. #2563eb blue)
            # Only override fill to "none" if it's missing, white, or black
            if not current_fill or current_fill in ("none", "#000", "#000000", "#fff", "#ffffff", "black", "white", "currentcolor"):
                elem.set("fill", "none")
            elem.set("stroke", "#1a1a1a")
            elem.set("stroke-width", "1.5")
            elem.set("stroke-linecap", "round")
            elem.set("stroke-linejoin", "round")

    return ET.tostring(root, encoding="unicode", xml_declaration=False)


def _find_parent(root: ET.Element, target: ET.Element) -> ET.Element | None:
    """Find the parent element of target within the tree rooted at root."""
    for parent in root.iter():
        if target in list(parent):
            return parent
    return None
