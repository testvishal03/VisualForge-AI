import type {Scene} from './types.ts';
import {clamp01, easeInOut} from './transitions.ts';

const normal = (word:string) => word.toLowerCase().replace(/[^\p{L}\p{N}]/gu, '');

/**
 * Measured start times of every spoken mention of a label, matching the backend's
 * phrase rule: exact words, with a short inflection allowed on the last ("tokens").
 * Beats without measured words contribute nothing, so nothing is guessed.
 */
export function mentionTimes(scene:Scene, label:string) {
  const target = label.split(/\s+/).map(normal).filter(Boolean);
  if (!target.length) return [];
  const times:number[] = [];
  for (const beat of scene.beats ?? []) {
    const words = beat.words ?? [];
    for (let i = 0; i + target.length <= words.length; i++) {
      const found = words.slice(i, i + target.length).map(w => normal(w.text));
      const last = found.at(-1)!, want = target.at(-1)!;
      if (found.slice(0, -1).join(' ') === target.slice(0, -1).join(' ') && last.startsWith(want) && last.length - want.length <= 3)
        times.push(words[i].start);
    }
  }
  return times;
}

/** A short swell when an object already on screen is named again; 0 otherwise. */
export function mentionPulse(times:number[], t:number, appearedAt:number) {
  let pulse = 0;
  for (const at of times) {
    if (at < appearedAt + .6) continue;
    const x = (t - (at - .12))/.7;
    if (x >= 0 && x <= 1) pulse = Math.max(pulse, Math.sin(Math.PI*x));
  }
  return pulse;
}

/** Gentle float so nothing on stage is ever fully frozen; objects drift out of phase. */
export const idleOffset = (t:number, index:number, active:boolean) => Math.sin(t*1.25 + index*1.9)*(active ? 5 : 3);

/** A slow push-in across the scene's narration, eased at both ends. */
export const sceneDrift = (t:number, duration:number) => 1 + .03*easeInOut(clamp01(t/Math.max(1, duration)));
