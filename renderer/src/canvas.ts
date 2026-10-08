import type {Scene} from './types.ts';

/**
 * A hand-designed scene visual: elements on a 1920x1080 frame, each revealed at a measured
 * time `t` (seconds into the scene), optionally hidden again at `tOut` and pulsed at `tPulse`.
 */
export type CanvasPoint = string | [number, number];
export type CanvasElement = {
  type: 'box'|'arrow'|'bubble'|'pill'|'check'|'cross'|'stamp'|'text'|'headline'|'bracket'|'ring'|'bar'|'icon'|'mover'|'line';
  id?: string; t: number; tOut?: number; tPulse?: number;
  x?: number; y?: number; w?: number; h?: number; r?: number; x1?: number; x2?: number;
  text?: string; sub?: string; label?: string; name?: string; icon?: string;
  color?: string; fill?: 'panel'|'tint'|'solid'|'none'; size?: string|number; align?: 'left'|'center'|'right'; side?: 'left'|'right';
  mono?: boolean; dashed?: boolean; curve?: number; dur?: number;
  from?: CanvasPoint; to?: CanvasPoint; points?: [number, number][];
};
export type Canvas = {elements: CanvasElement[]};

export const COLORS: Record<string, string> = {
  yellow: '#ffd23f', cyan: '#3ddcff', pink: '#ff5c8a', green: '#5be49b', red: '#ff5c5c',
  muted: '#a9b4d0', white: '#ffffff', line: '#2a3558', purple: '#a78bfa', orange: '#ff9f43',
};
export const BG = '#0b1020', PANEL = '#151d36';
export const SIZES: Record<string, [number, number]> = {title: [140, 900], h2: [64, 750], body: [34, 600], small: [28, 600]};
const TYPES = ['box','arrow','bubble','pill','check','cross','stamp','text','headline','bracket','ring','bar','icon','mover','line'];

export function validateCanvas(scene: Scene) {
  const c = scene.canvas;
  if (!c) return;
  const fail = (why: string) => {throw new Error(`Invalid scene canvas: ${why}`);};
  if (!Array.isArray(c.elements) || c.elements.length < 1 || c.elements.length > 40) fail('1-40 elements');
  const ids = new Set(c.elements.map(e => e.id).filter(Boolean));
  const finite = (v: unknown, lo: number, hi: number) => typeof v === 'number' && Number.isFinite(v) && v >= lo && v <= hi;
  for (const e of c.elements) {
    if (!TYPES.includes(e.type) || !finite(e.t, 0, scene.duration + 2)) fail(`${e.type} timing`);
    for (const k of ['x', 'x1', 'x2', 'w'] as const) if (e[k] !== undefined && !finite(e[k], 0, 1920)) fail(`${k} off frame`);
    for (const k of ['y', 'h', 'r'] as const) if (e[k] !== undefined && !finite(e[k], 0, 1080)) fail(`${k} off frame`);
    if (e.color !== undefined && !COLORS[e.color]) fail('colour');
    for (const p of [e.from, e.to]) if (p !== undefined && !(typeof p === 'string' ? ids.has(p) : Array.isArray(p) && finite(p[0], 0, 1920) && finite(p[1], 0, 1080))) fail('arrow end');
  }
}

/** Approximate rendered width of bold UI text. */
export const textWidth = (text: string, size: number) => text.length * size * .56;

/** Greedy word wrap to a pixel width. */
export function wrap(text: string, size: number, width: number) {
  const lines: string[] = [];
  let line = '';
  for (const word of text.split(/\s+/)) {
    const next = line ? `${line} ${word}` : word;
    if (line && textWidth(next, size) > width) {lines.push(line); line = word;} else line = next;
  }
  if (line) lines.push(line);
  return lines;
}

export const BOX_TITLE = 40, BOX_SUB = 28, BUBBLE = 34, PILL = 34;

/** Default box size: wide enough for its title, taller with a subtitle or icon. */
export function boxSize(e: CanvasElement) {
  const w = e.w ?? Math.min(760, Math.max(240, textWidth(e.text ?? '', BOX_TITLE) + 90));
  const lines = wrap(e.text ?? '', BOX_TITLE, w - 50).length, subs = e.sub ? wrap(e.sub, BOX_SUB, w - 50).length : 0;
  // A given height is a minimum: the box always grows to fit its text and icon.
  const needed = lines * BOX_TITLE * 1.2 + (subs ? subs * BOX_SUB * 1.3 + 10 : 0) + (e.icon ? 70 : 0) + 56;
  const h = Math.max(e.h ?? 120, needed);
  return {w, h};
}

export function bubbleSize(e: CanvasElement) {
  const w = e.w ?? 900, size = e.mono ? 32 : BUBBLE;
  return {w, h: wrap(e.text ?? '', size, w - 70).length * size * 1.35 + 60};
}

/** Bounds of an element, for arrows that connect to it by id. */
export function bounds(e: CanvasElement): {x0: number; y0: number; x1: number; y1: number} {
  const x = e.x ?? 960, y = e.y ?? 540;
  if (e.type === 'box') {const {w, h} = boxSize(e); return {x0: x - w/2, y0: y - h/2, x1: x + w/2, y1: y + h/2};}
  if (e.type === 'bubble') {const {w, h} = bubbleSize(e); return {x0: x, y0: y, x1: x + w, y1: y + h};}
  if (e.type === 'pill' || e.type === 'stamp') {const s = e.type === 'pill' ? PILL : 64, w = textWidth(e.text ?? '', s) + (e.type === 'pill' ? 60 : 70), h = e.type === 'pill' ? s + 34 : 110; return {x0: x - w/2, y0: y - h/2, x1: x + w/2, y1: y + h/2};}
  const r = e.type === 'ring' ? e.r ?? 100 : e.type === 'icon' ? Number(e.size ?? 96)/2 : e.type === 'check' || e.type === 'cross' ? e.r ?? 36 : 20;
  if (e.type === 'bar') return {x0: x, y0: y, x1: x + (e.w ?? 100), y1: y + (e.h ?? 30)};
  return {x0: x - r, y0: y - r, x1: x + r, y1: y + r};
}

/** Where a line from `toward` to the centre of a box leaves its border, with a small gap. */
export function edgePoint(b: ReturnType<typeof bounds>, toward: [number, number], gap = 12): [number, number] {
  const cx = (b.x0 + b.x1)/2, cy = (b.y0 + b.y1)/2, dx = toward[0] - cx, dy = toward[1] - cy;
  if (!dx && !dy) return [cx, cy];
  const sx = dx ? ((dx > 0 ? b.x1 : b.x0) - cx)/dx : Infinity, sy = dy ? ((dy > 0 ? b.y1 : b.y0) - cy)/dy : Infinity;
  const s = Math.min(sx, sy), len = Math.hypot(dx, dy);
  return [cx + dx*s + dx/len*gap, cy + dy*s + dy/len*gap];
}

/** Resolve an arrow's two ends: ids connect border to border, coordinates are used as given. */
export function arrowEnds(e: CanvasElement, byId: Map<string, CanvasElement>): [[number, number], [number, number]] {
  const centre = (p: CanvasPoint): [number, number] => {
    if (typeof p !== 'string') return p;
    const b = bounds(byId.get(p)!);
    return [(b.x0 + b.x1)/2, (b.y0 + b.y1)/2];
  };
  const a = centre(e.from!), b = centre(e.to!);
  const start = typeof e.from === 'string' ? edgePoint(bounds(byId.get(e.from)!), b) : a;
  const end = typeof e.to === 'string' ? edgePoint(bounds(byId.get(e.to)!), a) : b;
  return [start, end];
}

/** 0→1 cubic ease-out over `seconds` from `start`. */
export const reveal = (t: number, start: number, seconds = .5) => {
  const p = Math.max(0, Math.min(1, (t - start)/seconds));
  return 1 - (1 - p)**3;
};
