import React from 'react';
import {
  AbsoluteFill,
  Audio,
  Sequence,
  staticFile,
  useVideoConfig,
} from 'remotion';
import {AnimatedText} from 'remotion-bits';
import {MeshGradientBg} from './components/remocn/mesh-gradient-bg';

import type {RenderProps, SceneChoreography} from './types';

const SCENE_PALETTES = [
  {bg: '#0f0c29', colors: ['#302b63', '#24243e', '#1a1a3e', '#3d2b63']},
  {bg: '#000428', colors: ['#004e92', '#0a1628', '#1a3a6e', '#0055aa']},
  {bg: '#0d0d0d', colors: ['#1a1a2e', '#16213e', '#2d2d44', '#1f1f3a']},
  {bg: '#0d0d0d', colors: ['#1c1c3d', '#2a1a3e', '#3d1f3d', '#2d1a3e']},
  {bg: '#0a0a23', colors: ['#141450', '#232368', '#28287a', '#1a1a5e']},
  {bg: '#1a0a2e', colors: ['#2d1b69', '#4a2c8a', '#3b1f6e', '#5a3a9a']},
  {bg: '#0a1f2e', colors: ['#1b4a6b', '#2a6b9e', '#1a3a5e', '#3a7aae']},
];

const SCENE_W = 1920;
const SCENE_H = 1080;

const msToFrames = (ms: number, fps: number): number => Math.max(1, Math.round((ms / 1000) * fps));

const toStaticAsset = (assetPath: string): string => {
  if (assetPath.startsWith('http')) return assetPath;
  const cleaned = assetPath.replace(/^\/+/, '');
  const withoutPublic = cleaned.startsWith('public/') ? cleaned.slice('public/'.length) : cleaned;
  return staticFile(withoutPublic);
};

const extractViewBox = (markup: string): string => {
  const m = markup.match(/viewBox\s*=\s*["']([^"']*)["']/i);
  return m ? m[1] : '0 0 800 600';
};

const extractInnerSvg = (markup: string): string => {
  const start = markup.indexOf('>');
  if (start === -1) return '';
  const end = markup.lastIndexOf('</svg>');
  if (end <= start) return markup.slice(start + 1);
  return markup.slice(start + 1, end);
};

function buildTimeline(scenes: SceneChoreography[], fps: number) {
  const sceneFrames = scenes.map(s => msToFrames(s.audio_duration_ms, fps));
  const startFrames: number[] = [];
  let cumulative = 0;
  for (const f of sceneFrames) {
    startFrames.push(cumulative);
    cumulative += f;
  }
  return {sceneFrames, startFrames};
}

export const Whiteboard: React.FC<RenderProps> = ({fps, scenes}) => {
  const {fps: configFps} = useVideoConfig();
  const validFps = fps || configFps || 30;

  if (!scenes.length) {
    return (
      <AbsoluteFill
        style={{
          background: '#0f0c29',
          color: '#ffffff',
          justifyContent: 'center',
          alignItems: 'center',
          fontSize: 48,
          fontFamily: 'system-ui, sans-serif',
        }}
      >
        Waiting for pipeline...
      </AbsoluteFill>
    );
  }

  const {sceneFrames, startFrames} = buildTimeline(scenes, validFps);

  return (
    <AbsoluteFill style={{background: '#0f0c29', overflow: 'hidden'}}>
      {scenes.map((scene, i) => {
        const palette = SCENE_PALETTES[i % SCENE_PALETTES.length];

        return (
          <Sequence
            key={scene.scene_id}
            from={startFrames[i]}
            durationInFrames={sceneFrames[i]}
            layout="none"
          >
            <AbsoluteFill>
              <MeshGradientBg
                colors={palette.colors}
                background={palette.bg}
                blur={16}
                speed={0.5}
              />

              <div
                style={{
                  position: 'absolute',
                  inset: 0,
                  display: 'flex',
                  padding: '80px',
                  gap: '60px',
                  alignItems: 'center',
                }}
              >
                <div
                  style={{
                    flex: scene.svg_content ? '0 0 55%' : '0 0 100%',
                    display: 'flex',
                    flexDirection: 'column',
                    justifyContent: 'center',
                    gap: '16px',
                  }}
                >
                  <AnimatedText
                    transition={{
                      y: [-20, 0],
                      opacity: [0, 1],
                      split: 'word',
                      splitStagger: 3,
                      easing: 'easeOutCubic',
                    }}
                    style={{
                      color: '#b8a0ff',
                      fontSize: '36px',
                      fontWeight: 300,
                      lineHeight: 1.2,
                      fontFamily: 'system-ui, -apple-system, sans-serif',
                      textShadow: '0 2px 20px rgba(0,0,0,0.4)',
                      letterSpacing: '0.04em',
                      textTransform: 'uppercase',
                    }}
                  >
                    {scene.scene_title || ''}
                  </AnimatedText>
                  <AnimatedText
                    transition={{
                      y: [40, 0],
                      opacity: [0, 1],
                      split: 'word',
                      splitStagger: 4,
                      easing: 'easeOutCubic',
                    }}
                    style={{
                      color: '#ffffff',
                      fontSize: '64px',
                      fontWeight: 600,
                      lineHeight: 1.4,
                      fontFamily: 'system-ui, -apple-system, sans-serif',
                      textShadow: '0 2px 30px rgba(0,0,0,0.4)',
                      letterSpacing: '-0.02em',
                    }}
                  >
                    {scene.on_screen_text || scene.narration}
                  </AnimatedText>
                </div>

                {scene.svg_content && (
                  <div
                    style={{
                      flex: '0 0 35%',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <div
                      style={{
                        width: '100%',
                        maxWidth: 480,
                        background: 'rgba(255,255,255,0.06)',
                        borderRadius: 20,
                        padding: 28,
                        backdropFilter: 'blur(12px)',
                        border: '1px solid rgba(255,255,255,0.1)',
                      }}
                    >
                      <svg
                        viewBox={extractViewBox(scene.svg_content)}
                        xmlns="http://www.w3.org/2000/svg"
                        style={{width: '100%', height: 'auto', display: 'block'}}
                        dangerouslySetInnerHTML={{__html: extractInnerSvg(scene.svg_content)}}
                      />
                    </div>
                  </div>
                )}
              </div>
            </AbsoluteFill>
          </Sequence>
        );
      })}

      {scenes.map((scene, i) => (
        <Sequence
          key={`audio-${scene.scene_id}`}
          from={startFrames[i]}
          durationInFrames={sceneFrames[i]}
          layout="none"
        >
          <Audio src={toStaticAsset(scene.audio_path)} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};
