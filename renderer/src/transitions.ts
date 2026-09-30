import type {Scene} from './types.ts';
import {sceneFrames} from './timeline.ts';

/**
 * Scene changes are exit-then-enter over a solid background: the outgoing
 * content leaves inside its own silent end padding, then the incoming content
 * arrives in order. Two scenes' text is never drawn on top of each other.
 */
export const EXIT_SECONDS = .35;
export const ENTER_SECONDS = .5;
export const BACKGROUND_SECONDS = .3;
/** The "Up next" card appears this long before narration ends. */
export const TEASER_SECONDS = 2.4;
export const BRIDGE_SECONDS = .6;
/** After a bridge, the headline waits until the travelling card has dissolved. */
export const BRIDGE_HEADLINE_DELAY = .3;

/** True when this scene opens with the previous scene's "Up next" card travelling in. */
export const bridgedFrom = (previous:Scene|undefined, scene:Scene, fps:number, guide:boolean) =>
  guide && !!previous && !!teaserWindow(previous, scene, fps);

export const clamp01 = (x:number) => Math.max(0, Math.min(1, x));
export const easeOut = (x:number) => 1 - (1 - clamp01(x)) ** 3;
export const easeInOut = (x:number) => { const p = clamp01(x); return p < .5 ? 4*p**3 : 1 - (-2*p + 2)**3/2; };

/** Seconds the scene owns before the next one starts. */
export const sceneSeconds = (scene:Scene, fps:number) => sceneFrames(scene, fps)/fps;

/** 0 while the scene plays, rising to 1 as its content leaves at the end of its padding. */
export function exitProgress(t:number, total:number) {
  return easeOut((t - (total - EXIT_SECONDS))/EXIT_SECONDS);
}

/** 0 → 1 as an element enters, `delay` seconds after the scene starts. The first scene shows at once. */
export function enterProgress(t:number, delay:number, first:boolean) {
  return first ? 1 : easeOut((t - delay)/ENTER_SECONDS);
}

/** The incoming background covers the previous scene quickly, but never with its text on top. */
export const backgroundProgress = (t:number, first:boolean) => first ? 1 : easeOut(t/BACKGROUND_SECONDS);

/** The light illustrated stage; everything else uses the dark motion stage. */
export function isIllustrated(scene?:Scene) {
  return !!scene?.choreography && !['intro','outro','budget'].includes(scene.choreography.layout);
}

/** Lower-case object labels this scene hands to the next one; those stay on stage through the cut. */
export function carriedLabels(scene:Scene, next?:Scene) {
  const own = new Set(scene.choreography?.objects.map(o => o.label.toLowerCase()) ?? []);
  return new Set((next?.choreography?.objects ?? []).map(o => o.label.toLowerCase()).filter(label => own.has(label)));
}

/** When the next topic is previewed, or null when there is no next scene or no room for it. */
export function teaserWindow(scene:Scene, next:Scene|undefined, fps:number) {
  if (!next || scene.duration < 8) return null;
  return {start: Math.max(scene.duration*.6, scene.duration - TEASER_SECONDS), end: sceneSeconds(scene, fps)};
}
