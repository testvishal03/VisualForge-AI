import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig, spring, interpolate} from 'remotion';
import {TextScene} from './components/TextScene';
import {SceneAudio} from './components/SceneAudio';
import {MotionScene} from './components/MotionScene';
import {TRANSITION_SECONDS} from './motion';
import {buildTimeline} from './timeline';
import {palette} from './presentation';
import type {VideoProps} from './types';

const IntroScene = ({brand, title,theme}: {brand: string; title: string;theme?:string}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const entrance = spring({frame, fps, config: {damping: 14, stiffness: 60}});
  const lineReveal = interpolate(spring({frame: Math.max(0, frame - 10), fps, config: {damping: 20, stiffness: 80}}), [0, 1], [0, 100]);
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: 'Segoe UI, Arial, sans-serif',background:palette(theme).base}}>
      <div style={{transform: `scale(${entrance})`, opacity: entrance, display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{fontSize: 48, fontWeight: 700, color: palette(theme).accent, letterSpacing: 8, marginBottom: 20}}>{brand}</div>
        <div style={{fontSize: 72, fontWeight: 600, color: '#fff', textAlign: 'center', maxWidth: 1200}}>{title}</div>
        <div style={{width: `${lineReveal}%`, height: 4, background: palette(theme).accent, marginTop: 40}}/>
      </div>
    </AbsoluteFill>
  );
};

const OutroScene = ({brand,theme}: {brand: string;theme?:string}) => {
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const o1 = spring({frame, fps, config: {damping: 14, stiffness: 60}});
  const o2 = spring({frame: Math.max(0, frame - 30), fps, config: {damping: 14, stiffness: 60}});
  const o3 = spring({frame: Math.max(0, frame - 60), fps, config: {damping: 14, stiffness: 60}});
  return (
    <AbsoluteFill style={{justifyContent: 'center', alignItems: 'center', fontFamily: 'Segoe UI, Arial, sans-serif',background:palette(theme).base}}>
      <div style={{display: 'flex', flexDirection: 'column', alignItems: 'center'}}>
        <div style={{fontSize: 80, fontWeight: 700, color: palette(theme).accent, opacity: o1, transform: `translateY(${(1-o1)*20}px)`, marginBottom: 40}}>Thanks for watching</div>
        <div style={{fontSize: 40, fontWeight: 600, color: '#fff', opacity: o2, transform: `translateY(${(1-o2)*20}px)`, marginBottom: 15}}>{brand}</div>
        <div style={{fontSize: 28, color: '#b9c8d7', opacity: o3, transform: `translateY(${(1-o3)*20}px)`}}>Subscribe for more</div>
      </div>
    </AbsoluteFill>
  );
};

export const Video = ({videoData}: VideoProps) => {
  const {fps} = useVideoConfig();
  const globalFrame = useCurrentFrame();
  const timeline = buildTimeline(videoData, fps);
  
  const showIntro = !!videoData.style?.showIntro;
  const showOutro = !!videoData.style?.showOutro;
  const introOffset = timeline.introFrames;
  const brand = videoData.style?.brand ?? 'VISUALFORGE / LEARN';
  
  const lastScene = timeline.scenes[timeline.scenes.length - 1];
  const outroFrom = timeline.outroFrom;

  return (
    <AbsoluteFill style={{backgroundColor: palette(videoData.style?.theme).base}}>
      {showIntro && (
        <Sequence key="intro" from={0} durationInFrames={timeline.introFrames}>
          <IntroScene brand={brand} title={videoData.title} theme={videoData.style?.theme}/>
        </Sequence>
      )}
      {timeline.scenes.map(({scene, from, durationInFrames}, index) => (
        <Sequence key={scene.id} name={scene.headline} from={from} durationInFrames={durationInFrames+Math.ceil(fps*TRANSITION_SECONDS)}>
          {scene.visual ? <MotionScene scene={scene} style={videoData.style} globalFrame={globalFrame} first={from===timeline.introFrames} previous={timeline.scenes[index-1]?.scene} next={timeline.scenes[index+1]?.scene}/> : <TextScene headline={scene.headline} body={scene.body} />}
          <SceneAudio src={scene.audio} />
        </Sequence>
      ))}
      {showOutro && (
        <Sequence key="outro" from={outroFrom} durationInFrames={timeline.outroFrames}>
          <OutroScene brand={brand} theme={videoData.style?.theme}/>
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

