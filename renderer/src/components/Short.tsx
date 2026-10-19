import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {CanvasArt, GRID_BACKGROUND} from './CanvasScene';
import {Caption} from './Caption';
import {SceneAudio} from './SceneAudio';
import {COLORS, contentBox, reveal, textWidth} from '../canvas';

export type ShortSpec = {hook: string; title?: string};
export type ShortProps = {videoData: VideoData; short: ShortSpec};

/** A short's scenes back to back: each scene's narration plus a small breath. */
export const shortFrames = (scene: Scene, fps: number) => Math.ceil((scene.duration + .35)*fps);
export const shortLength = (scenes: Scene[], fps: number) => scenes.reduce((sum, s) => sum + shortFrames(s, fps), 0) + Math.ceil(1.5*fps);

function ShortScene({scene, previous, first}: {scene: Scene; previous?: Scene; first: boolean}) {
  const frame = useCurrentFrame(), {fps} = useVideoConfig(), t = frame/fps;
  const enter = first ? 1 : Math.min(1, t/.25);
  // Zoom to the part of the stage this scene uses, filling the phone screen's width.
  const box = contentBox(scene.canvas!.elements);
  return <AbsoluteFill style={{opacity: enter}}>
    <svg viewBox={`${box.x} ${box.y} ${box.w} ${box.h}`} preserveAspectRatio="xMidYMid meet"
      style={{position: 'absolute', left: 30, top: 540, width: 1020, height: 820}}>
      <CanvasArt elements={scene.canvas!.elements} t={t} previous={previous?.canvas?.elements}/>
    </svg>
    <Caption scene={scene} t={t} highlight={COLORS.yellow}
      style={{position: 'absolute', left: 60, right: 60, top: 1420, textAlign: 'center', fontSize: 64, lineHeight: 1.25, fontWeight: 800, color: '#ffffff'}}
      boxStyle={{background: '#050812', padding: '10px 22px', borderRadius: 18}}/>
    <SceneAudio src={scene.audio}/>
  </AbsoluteFill>;
}

/**
 * 1080×1920 Short from one to three scenes of an episode: a big hook at the top, the real scene
 * animation in the middle, large captions below, and a closing card pointing to the full video.
 */
export function Short({videoData, short}: ShortProps) {
  const frame = useCurrentFrame(), {fps} = useVideoConfig(), t = frame/fps;
  const scenes = videoData.scenes;
  const starts: number[] = [];
  scenes.reduce((at, s) => {starts.push(at); return at + shortFrames(s, fps);}, 0);
  const end = starts[starts.length - 1] + shortFrames(scenes[scenes.length - 1], fps);
  const hook = reveal(t, 0, .4), card = reveal(frame/fps, end/fps, .4);
  return <AbsoluteFill style={{background: GRID_BACKGROUND, fontFamily: "'Segoe UI', Selawik, Arial, sans-serif", overflow: 'hidden'}}>
    <div style={{position: 'absolute', left: 70, right: 70, top: 170, textAlign: 'center', color: '#ffffff', fontSize: short.hook.length > 40 ? 78 : 92,
      fontWeight: 900, lineHeight: 1.08, letterSpacing: -2, opacity: hook, transform: `translateY(${(1 - hook)*30}px)`, textShadow: '0 6px 24px #000c'}}>
      {short.hook}
    </div>
    <div style={{position: 'absolute', left: 40, right: 40, top: 450, textAlign: 'center', color: COLORS.cyan, fontWeight: 800, letterSpacing: 2,
      fontSize: Math.min(34, 980/Math.max(1, textWidth(videoData.title ?? '', 1)*1.15)), whiteSpace: 'nowrap'}}>
      {(videoData.title ?? '').toUpperCase()}
    </div>
    {scenes.map((scene, i) => <Sequence key={scene.id} from={starts[i]} durationInFrames={shortFrames(scene, fps)}>
      <ShortScene scene={scene} previous={scenes[i - 1]} first={i === 0}/>
    </Sequence>)}
    {card > 0 && <AbsoluteFill style={{background: `rgba(11,16,32,${.92*card})`, display: 'flex', alignItems: 'center', justifyContent: 'center'}}>
      <div style={{textAlign: 'center', opacity: card}}>
        <div style={{color: COLORS.yellow, fontSize: 84, fontWeight: 900, lineHeight: 1.1}}>Full video</div>
        <div style={{color: '#ffffff', fontSize: 52, fontWeight: 700, marginTop: 24, padding: '0 80px'}}>{short.title ?? videoData.title}</div>
      </div>
    </AbsoluteFill>}
  </AbsoluteFill>;
}
