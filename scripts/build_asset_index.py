"""
Build a semantic search index from local SVG assets.

One-time script — re-run only when the asset library changes.

Usage:
    python scripts/build_asset_index.py [--asset-dir assets/undraw] [--out assets/index.json]

Output:
    assets/index.json — list of {"id", "path", "text", "embedding"} objects

After building, upload to GCS:
    gsutil cp assets/index.json gs://savra-video-assets/assets/index.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="Build semantic asset index")
parser.add_argument(
    "--asset-dir",
    default="assets/undraw",
    help="Directory containing .svg files to index (default: assets/undraw)",
)
parser.add_argument(
    "--out",
    default="assets/index.json",
    help="Output path for the index JSON (default: assets/index.json)",
)
args = parser.parse_args()

asset_dir = Path(args.asset_dir)
index_out = Path(args.out)

if not asset_dir.exists():
    print(f"ERROR: asset directory not found: {asset_dir}", file=sys.stderr)
    sys.exit(1)

svg_files = sorted(asset_dir.glob("*.svg"))
if not svg_files:
    print(f"ERROR: no .svg files found in {asset_dir}", file=sys.stderr)
    sys.exit(1)

print(f"Found {len(svg_files)} SVG files in {asset_dir}")

# ---------------------------------------------------------------------------
# Load model
# ---------------------------------------------------------------------------
print("Loading sentence-transformers/all-MiniLM-L6-v2 ...")
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    print("ERROR: sentence-transformers not installed. Run: pip install sentence-transformers", file=sys.stderr)
    sys.exit(1)

model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
print("Model loaded.")

# ---------------------------------------------------------------------------
# Build descriptors and embed
# ---------------------------------------------------------------------------
entries = []
descriptors = []

for svg_file in svg_files:
    # "team-collaboration.svg" → "team collaboration"
    descriptor = svg_file.stem.replace("-", " ").replace("_", " ").strip()
    descriptors.append(descriptor)
    entries.append({
        "id":   svg_file.stem,
        "path": svg_file.name,   # filename only — matches /app/assets/undraw/<name>.svg at runtime
        "text": descriptor,
    })

print(f"Encoding {len(descriptors)} descriptors ...")
embeddings = model.encode(
    descriptors,
    normalize_embeddings=True,
    show_progress_bar=True,
    batch_size=64,
)

# Attach embeddings and write index
for entry, emb in zip(entries, embeddings):
    entry["embedding"] = emb.tolist()

index_out.parent.mkdir(parents=True, exist_ok=True)
index_out.write_text(json.dumps(entries, indent=2), encoding="utf-8")

print(f"\n✅ Index written: {index_out}  ({len(entries)} entries)")
print(f"\nNext step — upload to GCS:")
print(f"  gsutil cp {index_out} gs://savra-video-assets/assets/index.json")
