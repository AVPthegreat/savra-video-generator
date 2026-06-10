/**
 * render_worker.mjs
 *
 * Node.js render worker using @remotion/renderer API.
 * Called by the Python backend in production instead of the `remotion render` CLI.
 *
 * Advantages over CLI:
 *  - Uses a pre-built static bundle (baked into Docker image at build time)
 *  - Skips esbuild re-compilation on every call (~60-90s saved)
 *  - selectComposition() auto-detects durationInFrames from the input props
 *
 * Usage:
 *   node render_worker.mjs <props.json> <output.mp4>
 *
 * Environment variables:
 *   REMOTION_BUNDLE_DIR      Path to the pre-built bundle (default: ../renderer-bundle)
 *   REMOTION_CHROMIUM_PATH   Path to Chromium binary (default: /usr/bin/chromium)
 *   REMOTION_CONCURRENCY     Number of parallel browser tabs (default: 1)
 */

import { renderMedia } from '@remotion/renderer';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, resolve } from 'node:path';

const __dirname = dirname(fileURLToPath(import.meta.url));

// ── Args ─────────────────────────────────────────────────────────────────────
const [, , propsPath, outputPath] = process.argv;

if (!propsPath || !outputPath) {
  process.stderr.write(
    'Usage: node render_worker.mjs <props.json> <output.mp4>\n'
  );
  process.exit(1);
}

// ── Config ───────────────────────────────────────────────────────────────────
const props = JSON.parse(readFileSync(propsPath, 'utf-8'));

const bundleDir =
  process.env.REMOTION_BUNDLE_DIR ??
  resolve(__dirname, '..', 'renderer-bundle');

const browserExecutable =
  process.env.REMOTION_CHROMIUM_PATH ?? '/usr/bin/chromium';

const concurrency = Number(process.env.REMOTION_CONCURRENCY ?? '1');

process.stderr.write(
  `[render_worker] bundle=${bundleDir} concurrency=${concurrency} output=${outputPath}\n`
);

// ── Compute duration locally (mirrors estimateDuration in Root.tsx) ───────────
// This eliminates the selectComposition() browser-launch overhead (~25-40s saved).
const TRANSITION_MS = 450;
const totalMs = props.scenes.reduce(
  (sum, s) => sum + (s.audio_duration_ms ?? 0) + TRANSITION_MS,
  0
);
const fps = props.fps || 30;
const durationInFrames = Math.max(90, Math.ceil((totalMs / 1000) * fps));

process.stderr.write(
  `[render_worker] ${props.scenes.length} scenes → ${durationInFrames} frames @ ${fps}fps\n`
);

// ── Render ───────────────────────────────────────────────────────────────────
await renderMedia({
  composition: {
    id: 'Whiteboard',
    durationInFrames,
    fps,
    width: props.width || 1920,
    height: props.height || 1080,
    defaultProps: {},
  },
  serveUrl: bundleDir,
  codec: 'h264',
  outputLocation: outputPath,
  inputProps: props,
  chromiumOptions: { disableSandbox: true },
  browserExecutable,
  concurrency,
  timeoutInMilliseconds: 900_000,
  onProgress: ({ progress }) => {
    process.stderr.write(`\r[render_worker] ${Math.round(progress * 100)}%  `);
  },
});

process.stderr.write('\n[render_worker] Complete → ' + outputPath + '\n');
