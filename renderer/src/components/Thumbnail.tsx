import {AbsoluteFill} from 'remotion';
import type {Scene, VideoData} from '../types';
import {palette} from '../presentation';
import {isIllustrated} from '../transitions';
import {fitLabel} from '../labels';
import {Glyph} from './IllustratedStory';
import {Icon} from './VisualScene';

const font = "'Segoe UI', Selawik, Arial, sans-serif";
const coral = '#e7805e';

/**
 * The lesson's own concepts, most-used first: illustrated object labels, then diagram items.
 * The thumbnail shows only labels the narration itself introduced.
 */
export function keyConcepts(scenes:Scene[], limit = 3) {
  const counts = new Map<string, {label:string;count:number;first:number}>();
  scenes.forEach((scene, order) => {
    const labels = scene.choreography?.objects.map(o => o.label) ?? [];
    for (const label of labels) {
      const key = label.toLowerCase(), row = counts.get(key);
      if (row) row.count++; else counts.set(key, {label, count:1, first:order});
    }
  });
  return [...counts.values()].sort((a, b) => b.count - a.count || a.first - b.first).slice(0, limit).map(r => r.label);
}

function minutes(data:VideoData) {
  const seconds = data.scenes.reduce((sum, s) => sum + s.duration + .5, 0) + (data.style?.showIntro ? 3 : 0) + (data.style?.showOutro ? 5 : 0);
  return seconds < 60 ? `${Math.max(1, Math.round(seconds))} SEC` : `${Math.round(seconds/60)} MIN`;
}

/** 1280×720 cover: a bold title, the lesson's key concepts as a small diagram, and its scope. */
export function Thumbnail({videoData}:{videoData:VideoData}) {
  const light = videoData.scenes.filter(isIllustrated).length*2 >= videoData.scenes.length;
  const p = palette(videoData.style?.theme);
  const colors = light
    ? {base:'#fbfaf5', ink:'#173044', muted:'#54707b', accent:'#087e81', node:'#e9f4f0', ring:'#a4cfca'}
    : {base:p.base, ink:'#f4f3e9', muted:p.muted, accent:p.accent, node:p.panel, ring:`${p.accent}88`};
  const title = fitLabel(videoData.title, 640, 92, 54);
  const concepts = keyConcepts(videoData.scenes);
  const topics = (videoData.style?.agenda?.length ?? 0) > 1 ? videoData.style!.agenda!.length : videoData.scenes.length;
  const icons = videoData.scenes.flatMap(s => s.visual?.icons ?? []).filter((v, i, all) => all.indexOf(v) === i).slice(0, 3);
  // Diagonal arrangement so the eye travels from the first concept to the last, like the lesson.
  const spots = [[250, 210], [470, 400], [250, 590]].slice(0, Math.max(concepts.length, 1));
  return <AbsoluteFill style={{background:colors.base, fontFamily:font, color:colors.ink, overflow:'hidden'}}>
    <div style={{position:'absolute', right:-160, top:-160, width:760, height:760, borderRadius:'50%', background:`${colors.accent}14`}}/>
    <div style={{position:'absolute', left:0, top:0, bottom:0, width:14, background:colors.accent}}/>
    <div style={{position:'absolute', left:70, top:62, fontSize:22, letterSpacing:5, fontWeight:700, color:colors.accent}}>{videoData.style?.brand ?? 'VISUALFORGE / LEARN'}</div>
    <div style={{position:'absolute', left:70, top:0, bottom:0, width:660, display:'flex', flexDirection:'column', justifyContent:'center'}}>
      <div style={{fontSize:title.fontSize, lineHeight:1.02, fontWeight:800, letterSpacing:-2.5}}>
        {title.lines.map((line, i) => <div key={i}>{line}</div>)}
      </div>
      <div style={{width:150, height:9, borderRadius:5, background:coral, marginTop:30}}/>
    </div>
    <div style={{position:'absolute', left:70, bottom:58, display:'flex', gap:14}}>
      {[`${topics} TOPIC${topics === 1 ? '' : 'S'}`, minutes(videoData), 'EXPLAINED VISUALLY'].map(text =>
        <div key={text} style={{padding:'10px 18px', borderRadius:10, border:`2px solid ${colors.accent}66`, fontSize:20, fontWeight:700, letterSpacing:2, color:colors.accent}}>{text}</div>)}
    </div>
    <svg viewBox="0 0 640 800" style={{position:'absolute', right:30, top:-40, width:560, height:700}}>
      {concepts.length > 1 && spots.slice(1).map(([x, y], i) => {
        const [px, py] = spots[i];
        return <path key={i} d={`M${px + 70} ${py + 70}Q${(px + x)/2 + 120} ${(py + y)/2} ${x - 20} ${y - 90}`} fill="none" stroke={coral} strokeWidth="9" strokeLinecap="round" strokeDasharray="2 22"/>;
      })}
      {concepts.length
        ? concepts.map((label, i) => {
            const [x, y] = spots[i], fit = fitLabel(label, 250, 34, 22);
            return <g key={label} transform={`translate(${x} ${y})`}>
              <circle r="112" fill={i === concepts.length - 1 ? '#fff0e7' : colors.node} stroke={i === concepts.length - 1 ? coral : colors.ring} strokeWidth="6"/>
              <g transform="scale(1.7)"><Glyph label={label}/></g>
              {fit.lines.map((line, k) => <text key={k} y={150 + k*(fit.fontSize + 4)} textAnchor="middle" fontSize={fit.fontSize} fontWeight="800" fill={colors.ink}>{line}</text>)}
            </g>;
          })
        : <g transform="translate(330 400)"><circle r="190" fill={colors.node} stroke={colors.ring} strokeWidth="6"/></g>}
    </svg>
    {!concepts.length && icons.length > 0 && <div style={{position:'absolute', right:190, top:250, color:colors.accent}}><Icon kind={icons[0]} size={220}/></div>}
  </AbsoluteFill>;
}
