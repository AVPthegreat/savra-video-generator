import React from 'react';
import {Composition, registerRoot} from 'remotion';

import { Whiteboard } from './Whiteboard';
import type {RenderProps} from './types';

const defaultProps: RenderProps = {
  fps: 30,
  width: 1920,
  height: 1080,
  scenes: [],
};

const estimateDuration = (props: RenderProps): number => {
  const totalMs = props.scenes.reduce((sum, scene) => sum + scene.audio_duration_ms, 0);
  const totalFrames = Math.max(90, Math.ceil((totalMs / 1000) * props.fps));
  return totalFrames;
};

export const RemotionRoot: React.FC = () => {
  return (
    <Composition
      id="Whiteboard"
      component={Whiteboard}
      defaultProps={defaultProps}
      width={1920}
      height={1080}
      fps={30}
      durationInFrames={estimateDuration(defaultProps)}
      calculateMetadata={({props}: {props: unknown}) => {
        const typedProps = props as RenderProps;
        return {
          durationInFrames: estimateDuration(typedProps),
          fps: typedProps.fps || 30,
          width: typedProps.width || 1920,
          height: typedProps.height || 1080,
        };
      }}
    />
  );
};

registerRoot(RemotionRoot);
