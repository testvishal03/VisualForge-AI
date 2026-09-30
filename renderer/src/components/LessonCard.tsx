import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {Icon} from './VisualScene';

export function LessonCard({scene,accent,panel,hero=false}:{scene:Scene;accent:string;panel:string;hero?:boolean}) {
  const t=useCurrentFrame()/useVideoConfig().fps;
  const enter=interpolate(t,[0,.65],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  const kind=scene.visual!.kind;
  const beats=scene.beats??[];
  const active=beats.reduce((current,beat,index)=>t>=beat.start?index:current,0);
  const beat=beats[active];
  const detail=beat && beats.length>1 && beat.text.length<=180 && beat.text!==scene.body ? beat.text : undefined;
  const reveal=beat?interpolate(t-beat.start,[0,.35],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'}):1;
  const label=kind==='example'?'WORKED EXAMPLE':kind==='analogy'?'ANALOGY':kind==='takeaway'?'REMEMBER':kind==='title'?'THE BIG PICTURE':kind==='quote'?'KEY INSIGHT':'THE IDEA';
  return <div style={{width:'100%',boxSizing:'border-box',padding:hero?'55px 85px':'55px',borderRadius:28,background:panel,border:`1px solid ${accent}44`,opacity:enter,transform:`translateY(${(1-enter)*20}px)`,display:'flex',flexDirection:'column',gap:32}}>
    <div style={{color:accent,fontSize:20,letterSpacing:4,display:'flex',gap:22,alignItems:'center'}}><Icon kind={scene.visual?.icon??'idea'} size={hero?70:62}/>{label}</div>
    {hero&&<div style={{fontSize:scene.headline.length>60?64:80,fontWeight:650,lineHeight:1.1,maxWidth:1400}}>{scene.headline}</div>}
    <div style={{fontSize:hero?36:42,lineHeight:1.4,maxWidth:hero?1250:790}}>{scene.body}</div>
    {detail&&<div style={{maxWidth:hero?1250:790,minHeight:110,fontSize:hero?28:30,lineHeight:1.45,opacity:reveal*.85,borderLeft:`3px solid ${accent}`,paddingLeft:24}}>{detail}</div>}
    {beats.length>1&&<div style={{display:'flex',gap:10}}>{beats.map((_,i)=><div key={i} style={{width:i===active?48:20,height:4,borderRadius:4,background:accent,opacity:i===active?1:.25}}/>)}</div>}
    <div style={{width:hero?180:100,height:4,background:accent,marginTop:15}}/>
  </div>;
}
