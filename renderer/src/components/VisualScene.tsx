import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {Diagram} from './Diagram';

const ink = '#edf4fa';
const muted = '#b9c8d7';
const accent = '#75e5cd';
const line = '#2e4354';

export function Icon({kind,size=70}: {kind: string;size?:number}) {
  const paths: Record<string, React.ReactNode> = {
    sun: <><circle cx="32" cy="32" r="13"/><path d="M32 2v9M32 53v9M2 32h9M53 32h9M10 10l7 7M47 47l7 7M10 54l7-7M47 17l7-7"/></>,
    cloud: <path d="M15 49C-3 44 3 26 17 26C15 3 47 3 48 25C65 23 68 49 50 49Z"/>,
    water: <><path d="M32 4C25 19 10 30 10 41a22 22 0 0044 0C54 30 39 19 32 4Z"/><path d="M20 40c0 8 5 12 12 12"/></>,
    rain: <><path d="M13 35C0 30 8 14 20 20C25 0 49 5 48 20C66 17 65 36 50 36Z"/><path d="m18 44-5 12M33 44l-5 12M48 44l-5 12"/></>,
    network: <><circle cx="32" cy="12" r="8"/><circle cx="12" cy="50" r="8"/><circle cx="52" cy="50" r="8"/><path d="m28 20-12 22M36 20l12 22M20 50h24"/></>,
    gear: <><circle cx="32" cy="32" r="10"/><path d="m24 6 16 0 2 10 9 4 8 8-6 9 1 12-12 3-10 7-9-8-12-3 1-12-6-9 9-8 8-3Z"/></>,
    battery: <><rect x="7" y="17" width="47" height="30" rx="4"/><path d="M55 26h5v12h-5M18 32h10M23 27v10M36 32h10"/></>,
    globe: <><circle cx="32" cy="32" r="27"/><ellipse cx="32" cy="32" rx="12" ry="27"/><path d="M6 23h52M6 41h52"/></>,
    book: <><path d="M32 14c-9-7-20-6-25-3v40c7-3 16-3 25 3 9-6 18-6 25-3V11c-5-3-16-4-25 3Z"/><path d="M32 14v40"/></>,
    database: <><ellipse cx="32" cy="13" rx="23" ry="8"/><path d="M9 13v38c0 11 46 11 46 0V13M9 31c0 11 46 11 46 0"/></>,
    chip: <><rect x="15" y="15" width="34" height="34" rx="5"/><path d="M25 3v12M39 3v12M25 49v12M39 49v12M3 25h12M3 39h12M49 25h12M49 39h12"/><rect x="25" y="25" width="14" height="14"/></>,
    shield: <><path d="M32 5 9 15v17c0 14 23 27 23 27s23-13 23-27V15Z"/><path d="m20 31 9 9 16-19"/></>,
    clock: <><circle cx="32" cy="32" r="26"/><path d="M32 15v18l13 8"/></>,
    leaf: <><path d="M54 8C18 4 4 24 13 43c12 19 45 7 41-35Z"/><path d="m8 57 35-35M22 42V28M32 32h14"/></>,
    people: <><circle cx="23" cy="20" r="10"/><circle cx="46" cy="24" r="8"/><path d="M5 56v-8c0-19 36-19 36 0v8M43 38c12-2 17 6 17 18"/></>,
    chart: <><path d="M7 6v50h51M17 44V30h8v14M32 44V21h8v23M47 44V11h8v33"/></>,
    idea: <><path d="M22 43C-1 23 20 2 37 8c23 8 17 25 5 35M22 44h20M24 51h16M27 58h10"/></>,
  };
  return <svg viewBox="0 0 64 64" width={size} height={size} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
    {paths[kind] ?? (kind === 'takeaway' ? <><circle cx="32" cy="32" r="25"/><path d="m20 32 8 8 17-19"/></> : kind === 'example' ? <><rect x="9" y="12" width="46" height="40" rx="7"/><circle cx="24" cy="25" r="4"/><path d="m12 47 15-14 11 9 7-7 9 10"/></> : <><rect x="7" y="8" width="21" height="21" rx="5"/><rect x="36" y="35" width="21" height="21" rx="5"/><path d="M38 18h10v10M16 39v10h10M48 18 32 34"/></>)}
  </svg>;
}

export const VisualScene = ({scene, total, title, style}: {scene: Scene; total: number; title: string; style?:VideoData["style"]}) => {
  const theme=style?.theme??'ocean';
  const accent=theme==='forest'?'#b9e28c':theme==='sunset'?'#ffb18f':'#75e5cd';
  const background=theme==='forest'?'#11251e':theme==='sunset'?'#261d2e':'#0b1825';
  const panel=theme==='forest'?'#20392c':theme==='sunset'?'#392b41':'#132738';
  const frame = useCurrentFrame();
  const {fps} = useVideoConfig();
  const kind = scene.visual!.kind;
  const entrance = spring({frame, fps, config: {damping: 22, stiffness: 90}});
  const end = Math.ceil((scene.duration+.5)*fps);
  const opacity = interpolate(frame, [0, fps*.3], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'}) * (!!scene.visual?.transition ? interpolate(frame, [end-fps*.35, end-1], [1,0], {extrapolateLeft:'clamp',extrapolateRight:'clamp'}) : 1);
  const cardStyle = {background: panel, border: `1px solid ${line}`, borderRadius: 28, padding: 42};
  const rich = ['cycle','timeline','components','water_cycle','process','relationship','chart'].includes(kind) && scene.visual!.variant!==undefined;
  const isDiagram = rich || kind === 'process' || kind === 'comparison' || kind === 'relationship';
  const beat = scene.beats?.find(b => frame/fps >= b.start && frame/fps < b.end);
  return <AbsoluteFill style={{background, color: ink, fontFamily: 'Segoe UI, Arial, sans-serif', padding: '62px 100px'}}>
    <div style={{display: 'flex', justifyContent: 'space-between', alignItems: 'center', color: muted, fontSize: 22, letterSpacing: 2}}>
      <span style={{color: accent, fontWeight: 700}}>{style?.brand??'VISUALFORGE / LEARN'}</span>
      <span style={{maxWidth: 1100, overflow: 'hidden', whiteSpace: 'nowrap', textOverflow: 'ellipsis'}}>{title}</span>
    </div>
    <div style={{height: 1, background: line, marginTop: 25}}/>
    <div style={{flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', opacity, transform: `translate(${scene.visual?.transition==='slide'?(1-entrance)*70:0}px, ${(1-entrance)*28}px)`}}>
      <div style={{fontSize: 20, color: accent, textTransform: 'uppercase', letterSpacing: 4, marginBottom: 20}}>{kind==='chart'?'Compare the numbers':kind==='neural_net'?'Neural Network Architecture':kind==='code'?'The Algorithm & Logic':kind==='stat_card'?'Key Metrics & Numbers':kind==='quote'?'Key Takeaway':kind==='analogy'?'Think of it like':kind==='water_cycle'?'Water in motion':kind==='cycle'?'A repeating cycle':kind==='timeline'?'Across time':kind==='components'?'Inside the system':kind === 'comparison' ? (scene.visual!.directed ? 'Compare the ideas' : 'Benefits & limitations') : kind === 'relationship' ? 'Connected ideas' : kind === 'process' ? 'Step by step' : kind === 'takeaway' ? 'Remember this' : kind === 'example' ? 'In practice' : 'The core idea'}</div>
      <h1 style={{fontSize: isDiagram ? 58 : 76, lineHeight: 1.12, letterSpacing: -2, maxWidth: 1550, margin: '0 0 26px', overflowWrap: 'anywhere'}}>{scene.headline}</h1>
      {rich ? <Diagram scene={scene} accent={accent} panel={panel}/> : isDiagram ? <>
        {kind !== 'comparison' && <p style={{fontSize: 30, lineHeight: 1.45, color: muted, maxWidth: 1400, margin: '0 0 38px'}}>{scene.body}</p>}
        <div style={{display: 'flex', gap: 26, alignItems: 'stretch'}}>
          {scene.visual!.items.map((item, i) => {
            const at = scene.visual!.revealAt?.[i] ?? (.35+i*.15);
            const reveal = interpolate(frame, [fps*at, fps*(at+.25)], [0, 1], {extrapolateLeft: 'clamp', extrapolateRight: 'clamp'});
            const active = scene.visual!.directed && frame/fps >= at && frame/fps < (scene.visual!.revealAt?.find(next=>next>at) ?? scene.duration);
            return <div key={i} style={{...cardStyle, position:'relative', flex: 1, minWidth: 0, opacity: reveal, minHeight: kind === 'comparison' ? 260 : 210, borderColor:active ? accent : line, transform:`translateY(${(1-reveal)*16}px)`}}>
              <div style={{fontSize: 22, letterSpacing: 2, color: i === 1 && kind === 'comparison' ? '#f4c990' : accent, marginBottom: 30}}>{kind !== 'comparison' ? `0${i+1} ${i < scene.visual!.items.length-1 ? '→' : '✓'}` : scene.visual!.directed ? `VIEW ${i+1}` : i === 0 ? 'POSSIBILITIES' : 'LIMITATIONS'}</div>
              {kind === 'relationship' && i < scene.visual!.items.length-1 && <span style={{position:'absolute',right:-24,top:'45%',color:accent,zIndex:2}}>→</span>}
              <div style={{fontSize: kind === 'comparison' ? 33 : 34, lineHeight: 1.35, overflowWrap: 'anywhere'}}>{item}</div>
            </div>;
          })}
        </div>
      </> : <div style={{...cardStyle, display: 'flex', flexDirection:scene.visual!.variant===1?'column':'row', alignItems:scene.visual!.variant===1?'flex-start':'center', gap: 38, maxWidth: scene.visual!.variant===1?1300:1510, borderLeft: `5px solid ${accent}`}}>
        <div style={{color: accent, flexShrink: 0}}><Icon kind={scene.visual!.icon ?? kind} size={scene.visual!.variant===1?100:70}/></div>
        <p style={{fontSize: kind === 'title' ? 40 : 37, lineHeight: 1.5, margin: 0, color: muted, overflowWrap: 'anywhere'}}>{scene.body}</p>
      </div>}
      {scene.visual!.directed && <div style={{marginTop:24, height:110, color:muted, fontSize:25, lineHeight:1.45, borderTop:`1px solid ${line}`,paddingTop:20,display:'flex',gap:22}}><div style={{color:accent,transform:'scale(.65)',transformOrigin:'top left',width:52,flexShrink:0}}><Icon kind={scene.visual!.icon ?? 'idea'}/></div><div>{beat?.text ?? ''}</div></div>}
    </div>
    <div style={{display: 'flex', alignItems: 'center', gap: 30, color: muted, fontSize: 20}}>
      <span>{String(scene.id).padStart(2, '0')} / {String(total).padStart(2, '0')}</span>
      <div style={{height: 3, background: line, flex: 1}}><div style={{height: '100%', background: accent, width: `${Math.min(100, frame/(scene.duration*fps)*100)}%`}}/></div>
      <span>VISUAL EXPLAINER</span>
    </div>
  </AbsoluteFill>;
};
