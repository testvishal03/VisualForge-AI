import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {Icon} from './VisualScene';
import {animationTiming,activeConcept} from '../animation';

export function stageLayout(scene:Scene) {
  const v=scene.visual;
  if(!v || v.items.length<2)return undefined;
  return v.layout && v.layout!=='auto'?v.layout:({process:'pipeline',relationship:'branching',components:'layers',comparison:'contrast',timeline:'timeline'} as Record<string,string>)[v.kind];
}
const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
/** Source labels are the only diagram data. Movement illustrates, not simulates, a mechanism. */
export function TeachingStage({scene,accent}:{scene:Scene;accent:string}) {
  const t=useCurrentFrame()/useVideoConfig().fps,v=scene.visual!,layout=stageLayout(scene);
  const times=animationTiming(scene),active=activeConcept(scene,t),n=v.items.length;
  const reveal=(i:number)=>interpolate(t,[times[i],times[i]+.65],[0,1],clamp);
  const positions=v.items.map((_,i)=>{
    if(layout==='branching')return i===0?[340,205]:[1160,110+(i-1)*220];
    if(layout==='layers')return [650+i*95,58+i*100];
    if(layout==='contrast')return [420+i*760,200];
    if(layout==='timeline')return [160+i*1280/(n-1),i%2?280:100];
    return [180+i*1240/(n-1),205];
  });
  if(layout==='detail')return <div style={{height:440,display:'flex',gap:90,alignItems:'center'}}>
    <div style={{width:460,display:'flex',flexDirection:'column',gap:18}}>{v.items.map((label,i)=><div key={i} style={{padding:18,borderLeft:`4px solid ${i===active?accent:'#ffffff22'}`,opacity:i===active?1:.45,fontSize:26}}>{label}</div>)}</div>
    <div style={{flex:1,textAlign:'center',color:accent,transform:`scale(${1+Math.min(.08,Math.max(0,t-times[active])*.015)})`}}><Icon kind={v.icons?.[active]??v.icon??'idea'} size={175}/><div style={{fontSize:42,color:'#f4f3e9',marginTop:28}}>{v.items[active]}</div></div>
  </div>;
  return <div style={{height:440,position:'relative'}}>
    <svg preserveAspectRatio="none" viewBox="0 0 1600 440" style={{position:'absolute',width:'100%',height:'100%'}}>
      {layout==='contrast' && <path d="M800 20V420" stroke={accent} strokeOpacity=".35"/>}
      {layout==='timeline' && <path d="M100 205H1500" stroke={accent} strokeWidth="4"/>}
      {['pipeline','branching'].includes(layout!) && positions.slice(1).map(([x,y],i)=>{const [sx,sy]=positions[layout==='branching'?0:i];return <g key={i} opacity={reveal(i+1)}><path d={`M${sx+100} ${sy} C800 ${sy},800 ${y},${x-100} ${y}`} fill="none" stroke={accent} strokeOpacity=".35" strokeWidth="3"/>{Array.from({length:3},(_,j)=>{const p=(t*.18+j/3)%1;return <circle key={j} cx={(1-p)**3*(sx+100)+3*(1-p)**2*p*800+3*(1-p)*p*p*800+p**3*(x-100)} cy={sy+(y-sy)*(3*p*p-2*p*p*p)} r="6" fill={accent}/>;})}</g>;})}
      {layout==='timeline' && positions.map(([x,y],i)=><path key={i} d={`M${x} 205V${y}`} stroke={accent} opacity={reveal(i)}/>)}
    </svg>
    {v.items.map((label,i)=>{
      const r=reveal(i),[x,y]=positions[i];const layer=layout==='layers';
      const visible=v.motion==='focus'||v.motion==='flow'?1:r;
      const emphasis=v.motion==='focus'&&active!==i?.5:1;
      return <div key={i} style={{position:'absolute',left:`${x/16}%`,top:y,transform:`translate(-50%,-50%) translateY(${v.motion==='assemble'?(1-r)*65:0}px)`,width:layer?1000:layout==='contrast'?600:310,display:layer?'flex':'block',alignItems:'center',gap:35,padding:layer?'16px 32px':18,borderRadius:layer?16:26,background:layer||layout==='contrast'?`${accent}12`:undefined,border:layer?`1px solid ${accent}55`:undefined,opacity:visible*emphasis,textAlign:layer?'left':'center'}}>
        <div style={{color:accent,display:'inline-block',transform:`scale(${active===i?1.07:1})`}}><Icon kind={v.icons?.[i]??v.icon??'idea'} size={layer?56:90}/></div>
        <div style={{fontSize:layer?29:layout==='contrast'?34:27,lineHeight:1.3,marginTop:layer?0:18,overflowWrap:'anywhere'}}>{label}</div>
      </div>;
    })}
  </div>;
}
