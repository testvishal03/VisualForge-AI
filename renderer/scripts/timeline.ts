import {readFileSync} from 'node:fs';
import {buildTimeline, FPS, SCENE_END_PADDING_SECONDS} from '../src/timeline.ts';

const data = JSON.parse(readFileSync(process.argv[2] ?? new URL('../../data/video.generated.json', import.meta.url), 'utf8'));
console.log(JSON.stringify({fps: FPS, padding: SCENE_END_PADDING_SECONDS, ...buildTimeline(data.videoData ?? data, FPS)}));
