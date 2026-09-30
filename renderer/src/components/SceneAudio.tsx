import {Html5Audio, staticFile} from 'remotion';

export const SceneAudio = ({src}: {src: string}) => (
  // Untrimmed local audio; encoding and muxing are configured separately.
  <Html5Audio src={staticFile(src)} onError={(error) => {
    throw new Error(`Cannot play narration ${src}. Run npm run generate:audio. ${error.message}`);
  }} />
);
