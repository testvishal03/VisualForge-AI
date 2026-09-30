import type {Scene} from './types.ts';

export type Environment = 'evaporation' | 'clouds' | 'rain' | 'ground' | 'plant';
/** Prefer the teaching headline so background mentions do not hijack the scene. */
export function environmentFor(scene: Scene): Environment | null {
  if (scene.visual?.planned) return null;
  const text = `${scene.headline} ${scene.narration}`.toLowerCase();
  if (scene.visual?.kind === 'chart' || !/\b(water|rain|evaporation|transpiration|groundwater)\b/.test(text)) return null;
  const classify = (s: string): Environment | null =>
    /\b(plant\w*|tree\w*|root\w*|leaves|transpiration)\b/i.test(s) ? 'plant' :
    /\b(runoff|soil|groundwater|infiltration|aquifer\w*|pavement|cities|rivers?)\b/i.test(s) ? 'ground' :
    /\b(rain\w*|drizzle|downpour\w*|thunderstorm\w*|precipitation)\b/i.test(s) ? 'rain' :
    /\b(cloud\w*|condensation|condense\w*|cool\w*|dew)\b/i.test(s) ? 'clouds' :
    /\b(evaporation|evaporate\w*|sun\w*|vapor|warm\w*)\b/i.test(s) ? 'evaporation' : null;
  return classify(scene.headline) ?? classify(scene.narration);
}

export const TRANSITION_SECONDS = .4;
