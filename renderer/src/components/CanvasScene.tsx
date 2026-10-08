import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {arrowEnds, BG, BOX_SUB, BOX_TITLE, boxSize, BUBBLE, bubbleSize, COLORS, PANEL, PILL, reveal, SIZES, textWidth, wrap, type CanvasElement} from '../canvas';
import {Caption} from './Caption';
import {ConceptIcon, conceptIcon} from './ConceptIcon';
import {exitProgress, sceneSeconds} from '../transitions';

const FONT = "'Segoe UI', Selawik, Arial, sans-serif", MONO = "Consolas, 'DejaVu Sans Mono', monospace";
const color = (name?: string, fallback = 'cyan') => COLORS[name ?? fallback] ?? COLORS[fallback];
const iconName = (name?: string) => name ? (conceptIcon(name) ?? name) : null;

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
    return <g opacity={p} transform={`translate(0 ${rise})`}>
      <rect x={x} y={y} width={w} height={h} rx={28} fill={PANEL} stroke={c} strokeWidth={5}/>
      {lines.map((line, i) => <text key={i} x={x + 35} y={y + 30 + (i + .5)*size*1.35} dominantBaseline="central" fontSize={size} fontWeight={600} fontFamily={e.mono ? MONO : FONT} fill="#ffffff">{line}</text>)}
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
    const [size, weight] = SIZES[e.type === 'headline' ? 'h2' : String(e.size ?? 'body')] ?? SIZES.body;
    const anchor = e.align === 'left' ? 'start' : e.align === 'right' ? 'end' : 'middle';
    return <text x={e.type === 'headline' ? 960 : x} y={(e.type === 'headline' ? e.y ?? 210 : y) + rise} textAnchor={anchor} dominantBaseline="central"
      fontSize={size} fontWeight={weight} letterSpacing={size > 100 ? -3 : 0} fill={color(e.color, 'white')} opacity={p}>{e.text}</text>;
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
  return null;
}

/** A scene drawn from its hand-designed canvas: dark stage, dot grid, timed elements, word captions. */
export function CanvasScene({scene, data, index, total, first}: {scene: Scene; data: VideoData; index: number; total: number; first: boolean}) {
  const frame = useCurrentFrame(), {fps} = useVideoConfig(), t = frame/fps;
  const elements = scene.canvas!.elements, byId = new Map(elements.filter(e => e.id).map(e => [e.id!, e]));
  const enter = first ? 1 : Math.min(1, t/.3), exit = exitProgress(t, sceneSeconds(scene, fps));
  // The dot grid is one CSS pattern rather than hundreds of SVG circles, which kept rendering slow.
  const grid = `radial-gradient(circle, #1e2846 1.6px, transparent 2px) 10px 10px / 3.125% 5.556%`;
  return <AbsoluteFill style={{background: `${grid}, ${BG}`, fontFamily: FONT, opacity: enter}}>
    <svg viewBox="0 0 1920 1080" style={{position: 'absolute', inset: 0, width: '100%', height: '100%'}}>
      <text x={80} y={64} dominantBaseline="central" fontSize={26} fontWeight={800} letterSpacing={1} fill={COLORS.cyan}>{(data.title ?? '').toUpperCase().slice(0, 60)}</text>
      <text x={1840} y={64} textAnchor="end" dominantBaseline="central" fontSize={26} fontWeight={800} fill={COLORS.muted}>{String(index + 1).padStart(2, '0')} / {String(total).padStart(2, '0')}</text>
      <g opacity={1 - exit}>
        {elements.map((e, i) => {
          const p = reveal(t, e.t, e.type === 'stamp' ? .4 : e.type === 'arrow' || e.type === 'line' ? .6 : .5);
          const out = e.tOut === undefined ? 1 : 1 - reveal(t, e.tOut, .4);
          if (p <= 0 || out <= 0) return null;
          const glow = e.tPulse === undefined ? 0 : Math.max(0, 1 - Math.abs(t - e.tPulse - .4)/.6);
          return <g key={i} opacity={out} style={glow ? {filter: `drop-shadow(0 0 ${18*glow}px ${color(e.color)})`} : undefined}>
            <Element e={e} p={p} t={t} byId={byId}/>
          </g>;
        })}
      </g>
    </svg>
    <div style={{opacity: 1 - exit}}>
      <Caption scene={scene} t={t} highlight={COLORS.yellow}
        style={{position: 'absolute', bottom: 35, left: 140, right: 140, textAlign: 'center', fontSize: 40, lineHeight: 1.35, fontWeight: 600, color: '#ffffff'}}
        boxStyle={{background: '#05081280', backgroundColor: '#050812', padding: '14px 30px', borderRadius: 20}}/>
    </div>
  </AbsoluteFill>;
}
