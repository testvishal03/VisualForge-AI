import {Config} from '@remotion/cli/config';

Config.setEntryPoint('./src/index.ts');
Config.setVideoImageFormat('jpeg');
Config.setCodec('h264');
Config.setPixelFormat('yuv420p');

// MP3 preserves encoder-delay metadata through this Remotion version's
// intermediate audio file. Raw AAC introduced a measured ~43 ms offset.
Config.setAudioCodec('mp3');
Config.setAudioBitrate('192k');
Config.setDefaultCodingAgent('codex');
