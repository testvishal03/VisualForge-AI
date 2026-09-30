import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';

export type TextSceneProps = {
  headline: string;
  body: string;
};

export const TextScene = ({headline, body}: TextSceneProps) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const seconds = frame / fps;
  const entrance = spring({frame, fps, config: {damping: 18, stiffness: 100, mass: 0.8}});
  const clamp = {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'} as const;
  const headlineOpacity = interpolate(seconds, [0, 0.5], [0, 1], clamp);
  const bodyOpacity = interpolate(seconds, [0.4, 1], [0, 1], clamp);
  const bodyY = interpolate(seconds, [0.4, 1], [30, 0], clamp);

  return (
    <AbsoluteFill style={{
      background: '#0b1120', color: '#f4f7fc',
      fontFamily: 'Segoe UI, Arial, sans-serif',
      alignItems: 'center', justifyContent: 'center', padding: '120px 180px',
    }}>
      <div style={{width: '100%', maxWidth: 1480, textAlign: 'center'}}>
        <h1 style={{
          margin: 0, fontSize: 100, lineHeight: 1.12, fontWeight: 700,
          letterSpacing: -3, overflowWrap: 'anywhere',
          opacity: headlineOpacity, transform: `translateY(${(1 - entrance) * 48}px)`,
        }}>{headline}</h1>
        <p style={{
          margin: '44px auto 0', maxWidth: 1280, fontSize: 42,
          lineHeight: 1.5, fontWeight: 400, color: '#b8c5db',
          overflowWrap: 'anywhere', opacity: bodyOpacity, transform: `translateY(${bodyY}px)`,
        }}>{body}</p>
      </div>
    </AbsoluteFill>
  );
};
