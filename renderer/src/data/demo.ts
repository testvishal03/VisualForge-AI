import generated from '../../../data/video.generated.json';
import type {VideoData} from '../types';

// Narration is authored only in data/video.json; Python enriches it for rendering.
export const videoData: VideoData = generated;
