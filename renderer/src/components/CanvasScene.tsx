import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {along, arrowEnds, BG, BOX_SUB, BOX_TITLE, boxSize, BUBBLE, bubbleSize, canvasCamera, COLORS, fitText, PANEL, PILL, placed, plotMapper, reveal, SIZES, tableSize, textWidth, wrap, type CanvasElement} from '../canvas';
import {Caption} from './Caption';
import {ConceptIcon, conceptIcon} from './ConceptIcon';
import {exitProgress, sceneSeconds} from '../transitions';

const FONT = "'Segoe UI', Selawik, Arial, sans-serif", MONO = "Consolas, 'DejaVu Sans Mono', monospace";
const color = (name?: string, fallback = 'cyan') => COLORS[name ?? fallback] ?? COLORS[fallback];
// A concept word ("cart") or a Lucide name ("shopping-cart"); null when neither exists.
const iconName = (name?: string) => name ? conceptIcon(name) : null;

/** One element at reveal progress `p` (0 hidden → 1 in place): fades in while rising 30 px. */
function Element({e, p, t, byId}: {e: CanvasElement; p: number; t: number; byId: Map<string, CanvasElement>}) {
  const x = e.x ?? 960, y = e.y ?? 540, rise = (1 - p)*30, c = color(e.color);
  if (e.type === 'box') {
    const {w, h} = boxSize(e), fill = e.fill ?? 'panel', solid = fill === 'solid';
    const lines = wrap(e.text ?? '', BOX_TITLE, w - 50), subs = e.sub ? wrap(e.sub, BOX_SUB, w - 50) : [];
    const icon = iconName(e.icon), total = lines.length*BOX_TITLE*1.2 + (subs.length ? subs.length*BOX_SUB*1.3 + 10 : 0) + (icon ? 70 : 0);
    const top = y - total/2, cy = top + (icon ? 70 : 0);
    return <g opacity={p} transform={`translate(0 ${rise})`}>
      <rect x={x - w/2} y={y - h/2} width={w} height={h} rx={24} fill={solid ? c : fill === 'tint' ? `${c}26` : fill === 'none' ? 'none' : PANEL} stroke={c} strokeWidth={5}/>
      {icon && <g transform={`translate(${x} ${top + 30})`}><ConceptIcon name={icon} size={56} color={solid ? BG : c} draw={Math.min(1, p*1.4)}/></g>}
      {lines.map((line, i) => <text key={i} x={x} y={cy + (i + .5)*BOX_TITLE*1.2} textAnchor="middle" dominantBaseline="central" fontSize={BOX_TITLE} fontWeight={700} fill={solid ? BG : '#ffffff'}>{line}</text>)}
      {subs.map((line, i) => <text key={`s${i}`} x={x} y={cy + lines.length*BOX_TITLE*1.2 + 10 + (i + .5)*BOX_SUB*1.3} textAnchor="middle" dominantBaseline="central" fontSize={BOX_SUB} fontWeight={600} fill={solid ? BG : COLORS.muted}>{line}</text>)}
    </g>;
  }
  if (e.type === 'arrow' || e.type === 'line') {
    const points = e.type === 'line' ? e.points! : arrowEnds(e, byId);
    const [a, b] = [points[0], points[points.length - 1]], bend = e.curve ?? 0;
    const mx = (a[0] + b[0])/2, my = (a[1] + b[1])/2, len = Math.hypot(b[0] - a[0], b[1] - a[1]) || 1;
    const ctrl: [number, number] = [mx - (b[1] - a[1])/len*bend, my + (b[0] - a[0])/len*bend];
    const d = e.type === 'line' ? `M${points.map(q => q.join(' ')).join('L')}` : bend ? `M${a[0]} ${a[1]}Q${ctrl[0]} ${ctrl[1]} ${b[0]} ${b[1]}` : `M${a[0]} ${a[1]}L${b[0]} ${b[1]}`;
    const tail = e.type === 'line' ? points[points.length - 2] : bend ? ctrl : a, angle = Math.atan2(b[1] - tail[1], b[0] - tail[0]), L = 26;
    const stroke = color(e.color, 'muted');
    return <g opacity={p > 0 ? 1 : 0}>
      <path d={d} fill="none" stroke={stroke} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round" pathLength={1}
        strokeDasharray={e.dashed ? '0.02 0.025' : '1'} strokeDashoffset={e.dashed ? 0 : 1 - p} opacity={e.dashed ? p : 1}/>
      {e.type === 'arrow' && p > .9 && <polygon fill={stroke} opacity={(p - .9)*10}
        points={`${b[0]},${b[1]} ${b[0] - L*Math.cos(angle - .45)},${b[1] - L*Math.sin(angle - .45)} ${b[0] - L*Math.cos(angle + .45)},${b[1] - L*Math.sin(angle + .45)}`}/>}
      {e.label && <text x={bend ? ctrl[0] : mx} y={(bend ? ctrl[1] : my) - 22} textAnchor="middle" fontSize={28} fontWeight={600} fill={COLORS.muted} opacity={p}>{e.label}</text>}
    </g>;
  }
  if (e.type === 'bubble') {
    const {w, h} = bubbleSize(e), size = e.mono ? 32 : BUBBLE, lines = wrap(e.text ?? '', size, w - 70);
    let left = typed(e, t);
    return <g opacity={p} transform={`translate(0 ${rise})`}>
      <rect x={x} y={y} width={w} height={h} rx={28} fill={PANEL} stroke={c} strokeWidth={5}/>
      {lines.map((line, i) => {const shown = line.slice(0, Math.max(0, left)); left -= line.length + 1;
        return <text key={i} x={x + 35} y={y + 30 + (i + .5)*size*1.35} dominantBaseline="central" fontSize={size} fontWeight={600} fontFamily={e.mono ? MONO : FONT} fill="#ffffff">{shown}</text>;})}
    </g>;
  }
  if (e.type === 'pill') {
    const w = textWidth(e.text ?? '', PILL) + 60, h = PILL + 34;
    return <g opacity={p} transform={`translate(0 ${rise})`}>
      <rect x={x - w/2} y={y - h/2} width={w} height={h} rx={h/2} fill={c}/>
      <text x={x} y={y} textAnchor="middle" dominantBaseline="central" fontSize={PILL} fontWeight={700} fill={['red', 'purple', 'line'].includes(e.color ?? '') ? '#ffffff' : BG}>{e.text}</text>
    </g>;
  }
  if (e.type === 'check' || e.type === 'cross') {
    const r = e.r ?? 36, k = r*.38, ink = color(e.color, e.type === 'check' ? 'green' : 'red');
    return <g opacity={p} transform={`translate(${x} ${y}) scale(${.6 + .4*p})`}>
      <circle r={r} fill={ink}/>
      {e.type === 'check'
        ? <path d={`M${-r*.45} 0L${-r*.1} ${r*.35}L${r*.5} ${-r*.35}`} fill="none" stroke={BG} strokeWidth={r*.22} strokeLinecap="round" strokeLinejoin="round"/>
        : <path d={`M${-k} ${-k}L${k} ${k}M${-k} ${k}L${k} ${-k}`} stroke={BG} strokeWidth={r*.22} strokeLinecap="round"/>}
    </g>;
  }
  if (e.type === 'stamp') {
    const ink = color(e.color, 'red'), scale = 1 + (1 - p)*.6, w = textWidth(e.text ?? '', 64) + 70;
    return <g opacity={p} transform={`translate(${x} ${y}) scale(${scale}) rotate(-4)`}>
      <rect x={-w/2} y={-55} width={w} height={110} rx={16} fill={BG} stroke={ink} strokeWidth={9}/>
      <text textAnchor="middle" dominantBaseline="central" fontSize={64} fontWeight={800} fill={ink}>{e.text}</text>
    </g>;
  }
  if (e.type === 'text' || e.type === 'headline') {
    const [wanted, weight] = SIZES[e.type === 'headline' ? 'h2' : String(e.size ?? 'body')] ?? SIZES.body;
    const anchor = e.align === 'left' ? 'start' : e.align === 'right' ? 'end' : 'middle', at = e.type === 'headline' ? 960 : x;
    const size = fitText(e.text ?? '', wanted, at, e.align);
    return <text x={at} y={(e.type === 'headline' ? e.y ?? 210 : y) + rise} textAnchor={anchor} dominantBaseline="central"
      fontSize={size} fontWeight={weight} letterSpacing={size > 100 ? -3 : 0} fill={color(e.color, 'white')} opacity={p}>{(e.text ?? '').slice(0, typed(e, t))}</text>;
  }
  if (e.type === 'bracket') {
    const ink = color(e.color, 'yellow'), x1 = e.x1!, x2 = e.x2!;
    return <g opacity={p}>
      <path d={`M${x1} ${y - 50}V${y}H${x2}V${y - 50}`} fill="none" stroke={ink} strokeWidth={6} pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p}/>
      {e.label && <text x={(x1 + x2)/2} y={y + 80} textAnchor="middle" dominantBaseline="central" fontSize={64} fontWeight={750} fill={ink}>{e.label}</text>}
    </g>;
  }
  if (e.type === 'ring') {
    return <g opacity={p}>
      <circle cx={x} cy={y} r={(e.r ?? 100)*(.85 + .15*p)} fill="none" stroke={c} strokeWidth={6}/>
      {e.text && <text x={x} y={y} textAnchor="middle" dominantBaseline="central" fontSize={64} fontWeight={750} fill={c}>{e.text}</text>}
    </g>;
  }
  if (e.type === 'bar') {
    const w = e.w ?? 100, h = e.h ?? 30;
    return <g opacity={p}>
      <rect x={x} y={y + h*(1 - p)} width={w} height={h*p} rx={Math.min(8, h/2)} fill={c}/>
      {e.text && <text x={x + w/2} y={y + h/2} textAnchor="middle" dominantBaseline="central" fontSize={28} fontWeight={700} fill={BG}>{e.text}</text>}
    </g>;
  }
  if (e.type === 'icon') {
    const name = iconName(e.name);
    return name ? <g opacity={p} transform={`translate(${x} ${y + rise})`}><ConceptIcon name={name} size={Number(e.size ?? 96)} color={c} draw={p}/></g> : null;
  }
  if (e.type === 'mover') {
    const [a, b] = arrowEnds(e, byId), m = reveal(t, e.t, e.dur ?? 1.2), px = a[0] + (b[0] - a[0])*m, py = a[1] + (b[1] - a[1])*m;
    const w = e.text ? textWidth(e.text, 30) + 50 : 0;
    // It delivers its message: a moment after arriving it fades, leaving the destination readable.
    const arrived = e.t + (e.dur ?? 1.2), gone = reveal(t, arrived + .35, .4);
    return <g opacity={Math.min(1, p*2)*(1 - gone)}>
      {e.text ? <><rect x={px - w/2} y={py - 26} width={w} height={52} rx={26} fill={c}/><text x={px} y={py} textAnchor="middle" dominantBaseline="central" fontSize={30} fontWeight={700} fill={BG}>{e.text}</text></>
        : <circle cx={px} cy={py} r={18} fill={c}/>}
    </g>;
  }
  // ---- Machine-learning visuals ----
  const plot = e.plot ? byId.get(e.plot) : undefined, map = plot ? plotMapper(plot) : (dx: number, dy: number): [number, number] => [dx, dy];
  const toPath = (pts: [number, number][]) => pts.map((q, i) => `${i ? 'L' : 'M'}${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join('');
  const clip = plot ? `url(#plot-${plot.id})` : undefined;
  if (e.type === 'plot') {
    const w = e.w ?? 800, h = e.h ?? 500, x0 = x - w/2, y0 = y - h/2, ink = color(e.color, 'muted');
    const grid = e.grid !== false ? [1, 2, 3, 4].map(k => k/5) : [];
    // Gridded plots also show their scale: six tick values along each axis.
    const ticks = e.grid !== false ? [0, 1, 2, 3, 4, 5].map(k => k/5) : [];
    const [ax, bx] = e.xRange ?? [0, 10], [ay, by] = e.yRange ?? [0, 10];
    const value = (low: number, high: number, f: number) => {const v = low + (high - low)*f; return Math.abs(high - low) >= 5 ? String(Math.round(v)) : String(Math.round(v*10)/10);};
    const below = ticks.length ? 30 : 0;
    return <g opacity={p}>
      {grid.map(f => <path key={`g${f}`} d={`M${x0 + f*w} ${y0}V${y0 + h}M${x0} ${y0 + f*h}H${x0 + w}`} stroke={COLORS.line} strokeWidth={2} opacity={.7}/>)}
      <path d={`M${x0} ${y0 - 10}V${y0 + h}H${x0 + w + 10}`} fill="none" stroke={ink} strokeWidth={5} strokeLinecap="round" pathLength={1} strokeDasharray="1" strokeDashoffset={1 - p}/>
      {ticks.map(f => <text key={`x${f}`} x={x0 + f*w} y={y0 + h + 30} textAnchor="middle" fontSize={22} fontWeight={600} fill={COLORS.muted} opacity={.85}>{value(ax, bx, f)}</text>)}
      {ticks.map(f => <text key={`y${f}`} x={x0 - 14} y={y0 + h - f*h} textAnchor="end" dominantBaseline="central" fontSize={22} fontWeight={600} fill={COLORS.muted} opacity={.85}>{value(ay, by, f)}</text>)}
      {e.xLabel && <text x={x0 + w/2} y={y0 + h + 48 + below} textAnchor="middle" fontSize={30} fontWeight={600} fill={COLORS.muted}>{e.xLabel}</text>}
      {e.yLabel && <text x={x0 - 40 - below*1.5} y={y0 + h/2} textAnchor="middle" fontSize={30} fontWeight={600} fill={COLORS.muted} transform={`rotate(-90 ${x0 - 40 - below*1.5} ${y0 + h/2})`}>{e.yLabel}</text>}
    </g>;
  }
  if (e.type === 'points') {
    const data = e.data ?? [], gap = e.stagger ?? Math.min(.08, 1.2/Math.max(1, data.length)), r = e.r ?? 13;
    return <g clipPath={clip}>{data.map((d, i) => {
      const q = reveal(t, e.t + i*gap, .35), [px, py] = map(d[0], d[1]);
      return q > 0 ? <circle key={i} cx={px} cy={py} r={r*(.4 + .6*q)} fill={color(e.classes?.[d[2] ?? 0] ?? e.color, 'cyan')} opacity={q} stroke={BG} strokeWidth={3}/> : null;
    })}</g>;
  }
  if (e.type === 'curve') {
    const data = e.data ?? [];
    const morph = e.start ? reveal(t, e.t + .5, e.dur ?? 1.4) : 1;
    const pts = data.map((d, i) => map(e.start ? e.start[i][0] + (d[0] - e.start[i][0])*morph : d[0], e.start ? e.start[i][1] + (d[1] - e.start[i][1])*morph : d[1]));
    const drawn = e.start ? 1 : reveal(t, e.t, e.dur ?? 1);
    return <g clipPath={clip} opacity={e.start ? p : 1}>
      <path d={toPath(pts)} fill="none" stroke={color(e.color, 'yellow')} strokeWidth={7} strokeLinecap="round" strokeLinejoin="round"
        pathLength={1} strokeDasharray={e.dashed ? '0.015 0.02' : '1'} strokeDashoffset={e.dashed ? 0 : 1 - drawn} opacity={e.dashed ? drawn : 1}/>
    </g>;
  }
  if (e.type === 'dot') {
    const route = e.path ? e.path.map(d => map(d[0], d[1])) : [map(e.x ?? 960, e.y ?? 540)];
    const [px, py] = along(route, reveal(t, e.t + .3, e.dur ?? 2.2)), ink = color(e.color, 'red'), r = e.r ?? 18;
    return <g opacity={p}>
      <circle cx={px} cy={py} r={r} fill={ink} stroke={BG} strokeWidth={4}/>
      <circle cx={px} cy={py} r={r + 12} fill="none" stroke={ink} strokeWidth={3} opacity={.45}/>
      {e.label && <text x={px} y={py - r - 26} textAnchor="middle" fontSize={28} fontWeight={700} fill={ink}>{e.label}</text>}
    </g>;
  }
  if (e.type === 'segments') {
    const rows = e.segments ?? [], gap = Math.min(.08, 1/Math.max(1, rows.length));
    return <g clipPath={clip}>{rows.map((seg, i) => {
      const q = reveal(t, e.t + i*gap, .4), [ax, ay] = map(seg[0], seg[1]), [bx, by] = map(seg[2], seg[3]);
      return q > 0 ? <path key={i} d={`M${ax} ${ay}L${ax + (bx - ax)*q} ${ay + (by - ay)*q}`} stroke={color(e.color, 'red')} strokeWidth={4}
        strokeDasharray={e.dashed === false ? undefined : '10 8'}/> : null;
    })}</g>;
  }
  if (e.type === 'region') {
    const pts = (e.polygon ?? []).map(d => map(d[0], d[1]));
    return <g clipPath={clip}><polygon points={pts.map(q => q.join(',')).join(' ')} fill={color(e.color, 'cyan')} opacity={.18*p}/></g>;
  }
  if (e.type === 'table') {
    const rows = e.rows ?? [], cw = e.colWidth ?? 220, rh = e.rowHeight ?? 72, gap = e.stagger ?? .15, {w} = tableSize(e);
    const marks = new Map((e.highlight ?? []).map(([r, c, col]) => [`${r},${c}`, color(col)]));
    return <g>{rows.map((row, r) => {
      const q = reveal(t, e.t + r*gap, .4), head = e.header && r === 0;
      return q > 0 ? <g key={r} opacity={q} transform={`translate(0 ${(1 - q)*20})`}>
        {head && <rect x={x} y={y} width={w} height={rh} rx={12} fill={color(e.color, 'line')} opacity={.9}/>}
        {row.map((cell, c) => {
          const mark = marks.get(`${r},${c}`);
          return <g key={c}>
            <rect x={x + c*cw + 3} y={y + r*rh + 3} width={cw - 6} height={rh - 6} rx={10} fill={mark ? `${mark}33` : head ? 'none' : PANEL} stroke={mark ?? COLORS.line} strokeWidth={mark ? 4 : 2}/>
            <text x={x + c*cw + cw/2} y={y + r*rh + rh/2} textAnchor="middle" dominantBaseline="central" fontSize={Math.min(32, rh*.42)}
              fontWeight={head || c === 0 ? 700 : 600} fill={mark ?? (head ? '#ffffff' : c === 0 ? COLORS.muted : '#ffffff')}>{cell}</text>
          </g>;
        })}
      </g> : null;
    })}</g>;
  }
  if (e.type === 'network') {
    const layers = e.layers ?? [2, 2], w = e.w ?? 800, h = e.h ?? 400, x0 = x - w/2, y0 = y - h/2, ink = color(e.color, 'cyan');
    const pos = layers.map((n, l) => Array.from({length: n}, (_, k) => [x0 + (layers.length === 1 ? w/2 : l*w/(layers.length - 1)), y0 + (k + .5)*h/n] as [number, number]));
    const layerP = (l: number) => reveal(t, e.t + l*.45, .45);
    return <g>
      {pos.slice(1).map((col, l) => col.map((b, k) => pos[l].map((a, j) => {
        const q = reveal(t, e.t + (l + 1)*.45 - .2, .4);
        return q > 0 ? <path key={`${l}-${k}-${j}`} d={`M${a[0]} ${a[1]}L${a[0] + (b[0] - a[0])*q} ${a[1] + (b[1] - a[1])*q}`} stroke={COLORS.line} strokeWidth={3}/> : null;
      })))}
      {pos.map((col, l) => col.map(([cx, cy], k) => {
        const q = layerP(l);
        return q > 0 ? <circle key={`${l}-${k}`} cx={cx} cy={cy} r={24*(.5 + .5*q)} fill={PANEL} stroke={l === 0 ? COLORS.cyan : l === layers.length - 1 ? COLORS.pink : ink} strokeWidth={5} opacity={q}/> : null;
      }))}
      {(e.labels ?? []).map((label, l) => pos[l] && <text key={`t${l}`} x={pos[l][0][0]} y={y0 + h + 50} textAnchor="middle" fontSize={28} fontWeight={600} fill={COLORS.muted} opacity={layerP(l)}>{label}</text>)}
    </g>;
  }
  if (e.type === 'counter') {
    const [size, weight] = SIZES[String(e.size ?? 'h2')] ?? SIZES.h2, from = e.begin ?? 0;
    const value = from + ((e.value ?? 0) - from)*reveal(t, e.t, e.dur ?? 1.5);
    return <text x={x} y={y + rise} textAnchor="middle" dominantBaseline="central" fontSize={size} fontWeight={weight} fill={color(e.color, 'yellow')} opacity={p}>
      {`${e.prefix ?? ''}${value.toFixed(e.decimals ?? 0)}${e.suffix ?? ''}`}
    </text>;
  }
  return null;
}

/** Characters of a typing element shown at time t (about 30 per second); everything otherwise. */
const typed = (e: CanvasElement, t: number) => e.typing ? Math.floor((e.text ?? '').length*Math.max(0, Math.min(1, (t - e.t)/Math.max(.6, (e.text ?? '').length*.033)))) : Infinity;

/** Elements usable for drawing: an icon that does not exist is dropped, so its box keeps no gap. */
export const drawable = (elements: CanvasElement[]) => elements.map(e => e.icon && !iconName(e.icon) ? {...e, icon: undefined} : e);

/** A canvas's elements as they stand at time `t` (seconds into the scene), in 1920x1080 SVG units. */
export function CanvasArt({elements: given, t, previous}: {elements: CanvasElement[]; t: number; previous?: CanvasElement[]}) {
  // An element shown at the end of the previous scene with the same id and type continues: it is on
  // screen from the first frame and glides to its new place, so the two scenes read as one story.
  const before = new Map((previous ?? []).filter(e => e.id && e.tOut === undefined).map(e => [`${e.id}:${e.type}`, e]));
  const carried = (e: CanvasElement) => e.id ? before.get(`${e.id}:${e.type}`) : undefined;
  const elements = drawable(given).map(e => placed(e, t, carried(e)));
  const byId = new Map(elements.filter(e => e.id).map(e => [e.id!, e]));
  return <>
    <defs>{elements.filter(e => e.type === 'plot' && e.id).map(e => {
      const w = e.w ?? 800, h = e.h ?? 500;
      return <clipPath key={e.id} id={`plot-${e.id}`}><rect x={(e.x ?? 960) - w/2 - 20} y={(e.y ?? 540) - h/2 - 20} width={w + 40} height={h + 40}/></clipPath>;
    })}</defs>
    {elements.map((e, i) => {
      const p = carried(e) ? 1 : reveal(t, e.t, e.type === 'stamp' ? .4 : e.type === 'arrow' || e.type === 'line' ? .6 : .5);
      const out = (e.tOut === undefined ? 1 : 1 - reveal(t, e.tOut, .4))*(e.tDim === undefined ? 1 : 1 - .65*reveal(t, e.tDim, .5));
      if (p <= 0 || out <= 0) return null;
      const glow = e.tPulse === undefined ? 0 : Math.max(0, 1 - Math.abs(t - e.tPulse - .4)/.6);
      return <g key={i} opacity={out} style={glow ? {filter: `drop-shadow(0 0 ${18*glow}px ${color(e.color)})`} : undefined}>
        <Element e={e} p={p} t={t} byId={byId}/>
      </g>;
    })}
  </>;
}

/** The stage's dot grid, as one CSS pattern rather than hundreds of SVG circles (which slowed rendering). */
export const GRID_BACKGROUND = `radial-gradient(circle, #1e2846 1.6px, transparent 2px) 10px 10px / 3.125% 5.556%, ${BG}`;

/** A scene drawn from its hand-designed canvas: dark stage, dot grid, timed elements, word captions. */
export function CanvasScene({scene, data, index, total, first, previous}: {scene: Scene; data: VideoData; index: number; total: number; first: boolean; previous?: Scene}) {
  const frame = useCurrentFrame(), {fps} = useVideoConfig(), t = frame/fps;
  const camera = canvasCamera(scene.canvas!.camera, t);
  const enter = first ? 1 : Math.min(1, t/.3), exit = exitProgress(t, sceneSeconds(scene, fps));
  return <AbsoluteFill style={{background: GRID_BACKGROUND, fontFamily: FONT, opacity: enter}}>
    <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <text x={80} y={64} dominantBaseline="central" fontSize={26} fontWeight={800} letterSpacing={1} fill={COLORS.cyan}>{(data.title ?? '').toUpperCase().slice(0, 60)}</text>
      <text x={1840} y={64} textAnchor="end" dominantBaseline="central" fontSize={26} fontWeight={800} fill={COLORS.muted}>{String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}</text>
      <g opacity={1 - exit} transform={`translate(960 540) scale(${camera.zoom}) translate(${-camera.x} ${-camera.y})`}>
        <CanvasArt elements={scene.canvas!.elements} t={t} previous={previous?.canvas?.elements}/>
      </g>
    </svg>
    <div style={{opacity: 1 - exit}}>
      <Caption scene={scene} t={t} highlight={COLORS.yellow}
        style={{position: 'absolute', bottom: 35, left: 140, right: 140, textAlign: 'center', fontSize: 40, lineHeight: 1.35, fontWeight: 600, color: '#ffffff'}}
        boxStyle={{background: '#05081280', backgroundColor: '#050812', padding: '14px 30px', borderRadius: 20}}/>
    </div>
  </AbsoluteFill>;
}
