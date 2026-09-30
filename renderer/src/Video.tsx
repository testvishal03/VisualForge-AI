import {AbsoluteFill, Sequence, useCurrentFrame, useVideoConfig} from 'remotion';
import {TextScene} from './components/TextScene';
import {SceneAudio} from './components/SceneAudio';
import {MotionScene} from './components/MotionScene';
import {TRANSITION_SECONDS} from './motion';
import {buildTimeline} from './timeline';
import {palette} from './presentation';
import type {Scene, VideoProps} from './types';
import {TopicGuide} from './components/TopicGuide';
import {isIllustrated} from './transitions';
import {IntroScene, OutroScene} from './components/Bookends';

/** The topic guide follows each scene's stage: light for illustrated boards, themed dark otherwise. */
function guideColors(scene: Scene, theme?: string) {
  if (isIllustrated(scene)) return {ink: '#173044', muted: '#54707b', accent: '#087e81', card: '#ffffff', line: '#d7e3e0'};
  const {accent, panel, muted} = palette(theme);
  return {ink: '#f4f3e9', muted, accent, card: panel, line: `${accent}33`};
}

export const Video = ({videoData}: VideoProps) => {
  const {fps} = useVideoConfig();
  const globalFrame = useCurrentFrame();
  const timeline = buildTimeline(videoData, fps);
  
  const showIntro = !!videoData.style?.showIntro;
  const showOutro = !!videoData.style?.showOutro;
  const outroFrom = timeline.outroFrom;
  const guide = videoData.style?.topicMap !== false && videoData.scenes.length > 1;

  return (
    <AbsoluteFill style={{backgroundColor: palette(videoData.style?.theme).base}}>
      {showIntro && (
        <Sequence key="intro" from={0} durationInFrames={timeline.introFrames}>
          <IntroScene data={videoData}/>
        </Sequence>
      )}
      {timeline.scenes.map(({scene, from, durationInFrames}, index) => (
        <Sequence key={scene.id} name={scene.headline} from={from} durationInFrames={durationInFrames+Math.ceil(fps*TRANSITION_SECONDS)}>
          {scene.visual ? <MotionScene scene={scene} style={videoData.style} globalFrame={globalFrame} first={from===0} previous={timeline.scenes[index-1]?.scene} next={timeline.scenes[index+1]?.scene} guide={guide}/> : <TextScene headline={scene.headline} body={scene.body} />}
          {guide && scene.visual && <TopicGuide scenes={videoData.scenes} index={index} colors={guideColors(scene, videoData.style?.theme)}/>}
          <SceneAudio src={scene.audio} />
        </Sequence>
      ))}
      {showOutro && (
        <Sequence key="outro" from={outroFrom} durationInFrames={timeline.outroFrames}>
          <OutroScene data={videoData}/>
        </Sequence>
      )}
    </AbsoluteFill>
  );
};

