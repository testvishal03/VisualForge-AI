import type {Scene} from './types.ts';

/** Sentence cues take priority. Shared cues use illustrative pacing, never word timestamps. */
export function animationTiming(scene:Scene) {
  const count=scene.visual?.items.length??0;
  const cues=scene.visual?.revealAt;
  if(cues?.length===count && new Set(cues).size===count) return cues;
  return Array.from({length:count},(_,i)=>.3+i*Math.max(.2,(scene.duration*.68)/Math.max(1,count-1)));
}
export function activeConcept(scene:Scene,time:number) {
  return animationTiming(scene).reduce((a,at,i)=>time>=at?i:a,0);
}

export function sharedConcept(previous?:Scene,next?:Scene) {
  if(!previous?.visual || !next?.visual)return undefined;
  const index=previous.visual.items.findIndex(label=>next.visual!.items.some(other=>other.trim().toLowerCase()===label.trim().toLowerCase()));
  if(index<0)return undefined;
  return {label:previous.visual.items[index],icon:previous.visual.icons?.[index]??previous.visual.icon??'idea'};
}
