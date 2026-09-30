import {interpolate, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {Icon} from './VisualScene';

const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;

/** Every reveal is anchored to a measured sentence. Geometry is renderer-owned. */
export function Diagram({scene,accent,panel}: {scene:Scene;accent:string;panel:string}) {
  const frame=useCurrentFrame(); const {fps}=useVideoConfig(); const t=frame/fps;
  const v=scene.visual!;
  const reveals=v.items.map((_,i)=>interpolate(t,[v.revealAt?.[i]??0,(v.revealAt?.[i]??0)+.5],[0,1],clamp));
  const active=(i:number)=>{
    const at=v.revealAt?.[i]??0;
    return t>=at && t<(v.revealAt?.find(next=>next>at)??scene.duration);
  };
  if(v.kind==='chart') return <div style={{height:420,background:panel,borderRadius:28,padding:'24px 45px'}}>
    <div style={{fontSize:18,color:accent,marginBottom:18}}>PERCENTAGE · 0–100%</div>
    {v.items.map((label,i)=><div key={i} style={{display:'flex',gap:30,alignItems:'center',height:82,opacity:reveals[i]}}>
      <div style={{width:550,fontSize:24,lineHeight:1.2}}>{label}</div>
      <div style={{flex:1,height:28,background:'#ffffff12',borderRadius:8}}><div style={{width:`${v.values![i]*reveals[i]}%`,height:'100%',borderRadius:8,background:accent,opacity:active(i)?1:.65}}/></div>
      <div style={{width:100,fontSize:32,color:accent}}>{v.values![i]}%</div>
    </div>)}
  </div>;
  if(v.kind==='water_cycle') return <div style={{position:'relative',height:420,background:panel,borderRadius:28,overflow:'hidden'}}>
    <svg viewBox="0 0 1600 420" width="100%" height="100%">
      <defs><marker id="water-arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0 0L8 3L0 6" fill={accent}/></marker></defs>
      <circle cx="120" cy="90" r="40" fill="#ffd589"/><g stroke="#ffd589" strokeWidth="4">{Array.from({length:8},(_,i)=><path key={i} d="M120 30v-15" transform={`rotate(${i*45} 120 90)`}/>)}</g>
      <path d="M0 350 Q250 320 500 350T1000 350V420H0Z" fill="#257397"/>
      <path d="M930 355 1220 140 1420 355 1600 320V420H930Z" fill="#4d756d"/>
      <path d="M1172 185 1220 140 1263 187 1220 174Z" fill="#d6e6eb"/>
      <g opacity={reveals[0]} stroke={accent} fill="none" strokeWidth="5">
        {[280,370,460].map((x,i)=><path key={x} d={`M${x} 320 Q${x-40} 250 ${x} 180`} strokeDasharray="12 10" strokeDashoffset={-frame*(active(0)?1.2:0)} markerEnd="url(#water-arrow)"/>)}</g>
      <g opacity={reveals[1]} fill="#d8e9f1" transform={`translate(${(1-reveals[1])*70} 0)`}><ellipse cx="805" cy="105" rx="155" ry="42"/><circle cx="745" cy="80" r="47"/><circle cx="837" cy="70" r="62"/><ellipse cx="1080" cy="95" rx="105" ry="35"/></g>
      <g opacity={reveals[2]} stroke="#81c9f2" strokeWidth="5">{Array.from({length:12},(_,i)=>{const x=740+i*28;const y=160+((frame*3+i*17)%120);return <path key={i} d={`M${x} ${y}l-7 15`}/>;})}</g>
      <path opacity={reveals[3]} d="M1210 280Q1140 365 990 373H670" fill="none" stroke={accent} strokeWidth="7" strokeDasharray="700" strokeDashoffset={700*(1-reveals[3])} markerEnd="url(#water-arrow)"/>
    </svg>
    {v.items.map((label,i)=><div key={label} style={{position:'absolute',left:[210,610,1040,650][i],top:[215,12,215,350][i],opacity:reveals[i],padding:'10px 20px',borderRadius:12,background:panel,color:active(i)?accent:'#edf4fa',border:`1px solid ${active(i)?accent:'#4e6574'}`,fontSize:25}}>{i+1}. {label}</div>)}
  </div>;
  const n=v.items.length;
  const orbit=v.kind==='cycle'; const hub=v.kind==='components'; const timeline=v.kind==='timeline';
  const positions=v.items.map((_,i)=>{
    if(orbit) return n===2?[[330,210],[1250,210]][i]:n===4?[[330,95],[1250,95],[1250,325],[330,325]][i]:[800+570*Math.cos(-Math.PI/2+i*2*Math.PI/n),210+130*Math.sin(-Math.PI/2+i*2*Math.PI/n)];
    if(hub) return [240+i*(1120/Math.max(1,n-1)),v.variant?280+(i%2)*45:290];
    return [220+i*(1160/Math.max(1,n-1)),v.variant?125+(i%2)*140:210];
  });
  const width=n===2?530:340;
  return <div style={{height:420,position:'relative'}}>
    <svg viewBox="0 0 1600 420" preserveAspectRatio="none" width="100%" height="100%" style={{position:'absolute',inset:0}}>
      <defs><marker id="diagram-arrow" markerWidth="10" markerHeight="10" refX="8" refY="3" orient="auto"><path d="M0 0L8 3L0 6" fill={accent}/></marker></defs>
      {hub && <g><circle cx="800" cy="62" r="40" fill={panel} stroke={accent} strokeWidth="2"/><text x="800" y="70" textAnchor="middle" fill={accent} fontSize="20">PARTS</text></g>}
      {positions.map(([x,y],i)=>{
        if(!hub && i===n-1 && !orbit)return null;
        const next=positions[(i+1)%n];
        const dx=next[0]-x,dy=next[1]-y;
        const edge=Math.min((width/2/1.075+12)/Math.max(.001,Math.abs(dx)),(orbit?100:110)/Math.max(.001,Math.abs(dy)));
        const a=[x+dx*edge,y+dy*edge],b=[next[0]-dx*edge,next[1]-dy*edge];
        const d=hub?`M800 102 Q800 180 ${x} ${y-80}`:orbit&&n===2?`M${a[0]} ${a[1]} Q800 ${i?410:10} ${b[0]} ${b[1]}`:`M${a[0]} ${a[1]} L${b[0]} ${b[1]}`;
        const progress=hub?reveals[i]:reveals[(i+1)%n];
        return <g key={i}><path d={d} fill="none" stroke={accent} strokeWidth="3" pathLength="1" strokeDasharray="1" strokeDashoffset={1-progress} opacity={progress*.5} markerEnd="url(#diagram-arrow)"/>
          {progress===1&&<path d={d} fill="none" stroke={accent} strokeWidth="5" pathLength="1" strokeDasharray=".015 .16" strokeDashoffset={-t*.14}/>}</g>;
      })}
      {timeline && positions.map(([x,y],i)=><circle key={i} cx={x} cy={y+110} r="8" fill={accent} opacity={reveals[i]}/>)}
    </svg>
    {positions.map(([x,y],i)=><div key={i} style={{position:'absolute',left:`${x/16}%`,top:y,width,height:orbit?180:undefined,boxSizing:'border-box',transform:`translate(-50%,-50%) scale(${.9+.1*reveals[i]})`,opacity:reveals[i],padding:orbit?'16px 24px':'20px 24px',textAlign:'center'}}>
      <div style={{display:'flex',alignItems:'center',justifyContent:'center',gap:18,color:accent,marginBottom:orbit?8:12}}><div style={{padding:16,borderRadius:'50%',background:active(i)?`${accent}20`:`${accent}09`,transform:`translateY(${active(i)?Math.sin(t*1.4)*3:0}px)`}}><Icon kind={v.icons?.[i]??v.icon??'idea'} size={orbit?48:65}/></div>{timeline&&<span style={{fontSize:20,letterSpacing:2}}>{v.items[i].match(/\b\d{4}\b/)?.[0]??`0${i+1}`}</span>}</div>
      <div style={{fontSize:orbit?22:n>3?24:28,lineHeight:1.3,overflowWrap:'anywhere'}}>{v.items[i]}</div>
    </div>)}
  </div>;
}
