import {
  interpolate,
  interpolateColors,
  useCurrentFrame,
  useVideoConfig,
} from 'remotion';

export interface InlineHighlightProps {
  before: string;
  highlight: string;
  after?: string;
  baseColor?: string;
  highlightColor?: string;
  fontSize?: number;
  fontWeight?: number;
  speed?: number;
  className?: string;
}

export function InlineHighlight({
  before,
  highlight,
  after = '',
  baseColor = '#ffffff',
  highlightColor = '#60a5fa',
  fontSize = 48,
  fontWeight = 600,
  speed = 1,
  className,
}: InlineHighlightProps) {
  const frame = useCurrentFrame() * speed;
  const {durationInFrames} = useVideoConfig();

  const progress = interpolate(
    frame,
    [durationInFrames * 0.2, durationInFrames * 0.7],
    [0, 1],
    {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'},
  );

  const color = interpolateColors(progress, [0, 1], [baseColor, highlightColor]);

  return (
    <span
      className={className}
      style={{
        fontSize,
        fontWeight,
        color: baseColor,
        letterSpacing: '-0.02em',
        fontFamily: 'system-ui, -apple-system, sans-serif',
      }}
    >
      {before}
      <span style={{color}}>{highlight}</span>
      {after}
    </span>
  );
}
