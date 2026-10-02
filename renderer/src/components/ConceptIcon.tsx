import iconNodes from 'lucide-static/icon-nodes.json';
import {iconFor, type IconNode} from '../icon-match';

const nodes = iconNodes as unknown as Record<string, IconNode>;
const ink = '#173044';

/** The Lucide icon chosen for a concept label, or null; see icon-match for how it is chosen. */
export const conceptIcon = (label: string) => iconFor(label, nodes);

/** 0..1 drawing progress for an icon whose concept is spoken at `cue` seconds. */
export const drawProgress = (t: number, cue: number, seconds = .9) => Math.max(0, Math.min(1, (t - cue) / seconds));

/**
 * A Lucide line icon (24-unit grid) centred on the origin, drawn stroke by stroke as `draw` goes
 * from 0 to 1: every shape gets pathLength 1 so its outline can be revealed, and shapes start one
 * after another so the icon sketches itself the way a presenter would draw it.
 */
export function ConceptIcon({name, draw = 1, size = 72, color = ink}: {name: string; draw?: number; size?: number; color?: string}) {
  const shapes = nodes[name];
  if (!shapes) return null;
  const k = size / 24, step = shapes.length > 1 ? .45 / (shapes.length - 1) : 0;
  return <g transform={`scale(${k}) translate(-12 -12)`} fill="none" stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
    {shapes.map(([tag, attrs], i) => {
      const local = Math.max(0, Math.min(1, (draw - i * step) / .55));
      if (local <= 0) return null;
      const Tag = tag as 'path';
      const drawing = local < 1 ? {pathLength: 1, strokeDasharray: 1, strokeDashoffset: 1 - local} : {};
      return <Tag key={i} {...attrs} {...drawing}/>;
    })}
  </g>;
}
