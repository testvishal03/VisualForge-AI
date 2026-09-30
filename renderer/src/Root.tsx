import {Composition, staticFile, type CalculateMetadataFunction} from 'remotion';
import {Video} from './Video';
import {Thumbnail} from './components/Thumbnail';
import {videoData} from './data/demo';
import {buildTimeline, FPS} from './timeline';
import type {VideoProps} from './types';

const calculateMetadata: CalculateMetadataFunction<VideoProps> = async ({props, abortSignal}) => {
  const timeline = buildTimeline(props.videoData, FPS);
  await Promise.all(props.videoData.scenes.map(async (scene) => {
    const response = await fetch(staticFile(scene.audio), {method: 'HEAD', signal: abortSignal});
    if (!response.ok || !response.headers.get('content-type')?.includes('audio/')) {
      throw new Error(`Scene ${scene.id}: missing WAV ${scene.audio}. Run npm run generate:audio before previewing or rendering.`);
    }
  }));
  return {durationInFrames: timeline.durationInFrames};
};

export const RemotionRoot = () => (
  <>
    <Composition
      id="VisualForgeVideo"
      component={Video}
      fps={FPS}
      width={1920}
      height={1080}
      durationInFrames={buildTimeline(videoData, FPS).durationInFrames}
      defaultProps={{videoData}}
      calculateMetadata={calculateMetadata}
    />
    {/* YouTube's recommended thumbnail size; rendered as a single still after export. */}
    <Composition id="VisualForgeThumbnail" component={Thumbnail} fps={FPS} width={1280} height={720} durationInFrames={1} defaultProps={{videoData}}/>
  </>
);
