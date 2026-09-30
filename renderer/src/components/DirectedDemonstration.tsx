import {useCurrentFrame,useVideoConfig} from 'remotion';
import {scalePoint} from 'd3-scale';
import {linkHorizontal} from 'd3-shape';
import type {Scene} from '../types';
import {cueProgress,objectState} from '../choreography';

function ObjectGlyph({label,color}:{label:string;color:string}){
  if(/token ids/i.test(label))return <text y="12" textAnchor="middle" fontSize="38" fill={color}>#</text>;
  if(/tokenizer/i.test(label))return <path d="M-35 -22H35 M-35 0H-8 M8 0H35 M-35 22H35 M0 -32V32" stroke={color} strokeWidth="4"/>;
  if(/tokens|pieces|words|punctuation/i.test(label))return <g stroke={color} fill={`${color}25`} strokeWidth="2">{[-27,0,27].map(x=><rect key={x} x={x-10} y="-17" width="20" height="34" rx="3"/>)}</g>;
  if(/history|older/i.test(label))return <g stroke={color} fill="none" strokeWidth="3"><circle r="28"/><path d="M0 -19V0L16 9 M-32 -24L-39 -5L-20 -9"/></g>;
  if(/weights|training/i.test(label))return <g stroke={color} fill={color}>{[-22,22].map(x=>[-20,20].map(y=><circle key={`${x}-${y}`} cx={x} cy={y} r="6"/>))}<path d="M-22 -20L22 20M-22 20L22 -20M-22 -20H22M-22 20H22" fill="none"/></g>;
  if(/context window/i.test(label))return <path d="M-20 -30H-35V30H-20 M20 -30H35V30H20" stroke={color} strokeWidth="4" fill="none"/>;
  if(/question/i.test(label))return <text y="14" textAnchor="middle" fontSize="43" fill={color}>?</text>;
  return <path d="M-23 -30H23V30H-23Z M-13 -13H13 M-13 0H13 M-13 13H5" stroke={color} strokeWidth="3" fill={`${color}10`}/>;
}

/** D3 computes geometry only. Remotion's frame is the sole animation clock. */
export function DirectedDemonstration({scene,accent,previous}:{scene:Scene;accent:string;previous?:Scene}){
  const t=useCurrentFrame()/useVideoConfig().fps,c=scene.choreography!;
  const workspace=c.layout==='workspace',bookend=['intro','outro'].includes(c.layout),compare=c.layout==='comparison';
  const position=scalePoint<number>().domain(c.objects.map((_,i)=>i)).range([140,1460]).padding(.35);
  const x=(i:number)=>compare?(i%2?1160:440):position(i)!;
  const y=(i:number)=>compare?135+Math.floor(i/2)*105:bookend?210+Math.sin(i)*45:235;
  const curve=linkHorizontal().x(d=>d[0]).y(d=>d[1]);
  const states=c.objects.map((_,i)=>objectState(c,i,t));
  if(c.layout==='budget'){
    const values=c.objects.map(o=>Number(o.label.split(' ')[0].replaceAll(',',''))),width=1300;
    return <svg viewBox="0 0 1600 450" style={{width:'100%',height:455}} role="img" aria-label="Illustrative input and output token budget">
      <text x="800" y="40" fill={accent} textAnchor="middle" fontSize="20" letterSpacing="3">TOY EXAMPLE — NOT YOUR MODEL'S LIMIT</text>
      <text x="800" y="115" fill="white" textAnchor="middle" fontSize="36">{states[0].visible?`${c.objects[0].label} total capacity`:''}</text>
      <path d="M150 170H1450V280H150Z" fill="none" stroke={accent} strokeWidth="2"/>
      {[1,2].map((i)=>{const w=width*values[i]/values[0],left=i===1?1450-w:150;return <g key={i} opacity={states[i].entrance}>
        <rect x={left} y="171" width={w*states[i].entrance} height="108" fill={i===1?'#ffca99':accent} fillOpacity=".55"/>
        <text x={left+w/2} y="225" fill="white" textAnchor="middle" fontSize="28">{values[i]}</text>
        <text x={left+w/2} y="335" fill="white" textAnchor="middle" fontSize="25">{i===1?'Reserved output':'Available input'}</text>
      </g>;})}
      <text x="800" y="425" fill="#a9c0ca" textAnchor="middle" fontSize="23">Input + reserved output must fit this illustrative shared limit</text>
    </svg>;
  }
  return <svg viewBox="0 0 1600 450" style={{width:'100%',height:455}} role="img" aria-label={`${c.layout} demonstration synchronized to narration`}>
    <text x="800" y="20" fill={accent} textAnchor="middle" fontSize="18" letterSpacing="3">{bookend?(c.layout==='intro'?'THE QUESTION WE WILL ANSWER':'TAKE THESE IDEAS WITH YOU'):workspace?'WHAT THE MODEL CAN USE NOW':'FOLLOW THE EXPLANATION'}</text>
    {workspace&&<><path d="M70 110V325H1530V110 M70 110H1530" fill={`${accent}08`} stroke={accent} strokeWidth="2"/><text x="800" y="85" fill="#e3eeeb" textAnchor="middle" fontSize="25">Finite context capacity</text></>}
    {compare&&<path d="M800 70V390" stroke={accent} strokeOpacity=".3" strokeDasharray="5 12"/>}
    {bookend&&<ellipse cx="800" cy="225" rx="710" ry="120" fill="none" stroke={accent} strokeOpacity=".16"/>}
    {c.steps.filter(s=>s.action==='connect'&&s.start<=t).map((s,j)=>{
      const [a,b]=s.targets,p=cueProgress(t,s.start,s.end);
      return <path key={j} d={curve({source:[x(a),y(a)],target:[x(b),y(b)]})??''} pathLength="1" strokeDasharray="1" strokeDashoffset={1-p} stroke={accent} strokeWidth="3" fill="none" opacity={states[a].visible&&states[b].visible?.7:0}/>;
    })}
    {c.objects.map((o,i)=>{
      const s=states[i];
      const prior=previous?.choreography;
      const oldIndex=prior?.objects.findIndex(o=>o.label.toLowerCase()===c.objects[i].label.toLowerCase())??-1;
      const oldState=prior&&oldIndex>=0?objectState(prior,oldIndex,previous!.duration):null;
      const carried=!!oldState?.visible&&!oldState.removed&&prior?.layout===c.layout&&!['intro','outro','budget','comparison'].includes(c.layout);
      const oldX=carried?scalePoint<number>().domain(prior!.objects.map((_,j)=>j)).range([140,1460]).padding(.35)(oldIndex)!:x(i);
      const blend=Math.min(1,t/.6);
      if(!s.visible&&!carried)return null;
      const color=s.active?'#ffca99':accent;
      const lines=o.label.length>18?o.label.split(/\s(?=\S+$)/):[o.label];
      return <g key={o.label} opacity={(carried?1:s.entrance)*(1-s.removed*.7)} transform={`translate(${oldX+(x(i)-oldX)*blend} ${y(i)-s.removed*165+(carried?0:(1-s.entrance)*35)})`}>
        <ObjectGlyph label={o.label} color={color}/>
        {s.active&&<circle r={workspace?66:53} fill="none" stroke={color} strokeWidth="1" opacity=".5"/>}
        {lines.map((line,k)=><text key={k} y={82+k*30} fill="#f4f3e9" fontSize="25" textAnchor="middle">{line}</text>)}
        {s.removed>0&&<text y="-78" fill="#ffca99" textAnchor="middle" fontSize="20">Outside this request</text>}
      </g>;
    })}
    <text x="800" y="433" fill="#a9c0ca" textAnchor="middle" fontSize="20">{c.note}{workspace?' • Equal spacing does not represent token counts':''}</text>
  </svg>;
}
