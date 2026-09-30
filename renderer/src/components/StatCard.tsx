import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {animationTiming} from '../animation';
export function StatCard({scene,accent,panel}:{scene:Scene;accent:string;panel:string}) {
  const t=useCurrentFrame()/useVideoConfig().fps;const v=scene.visual!,times=animationTiming(scene);
  const values=v.values??v.statValues!;
  return <div style={{display:'flex',gap:28,height:410}}>{v.items.map((label,i)=>{
    const p=interpolate(t,[times[i],times[i]+.5],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
    const number=String(values[i]);
    return <div key={i} style={{flex:1,minWidth:0,background:panel,borderRadius:24,padding:32,opacity:p,transform:`translateY(${(1-p)*20}px)`,borderTop:`4px solid ${accent}`,display:'flex',flexDirection:'column',justifyContent:'center',gap:26}}>
      <div style={{fontSize:number.length>8?42:number.length>5?60:88,color:accent,fontWeight:650,overflowWrap:'anywhere'}}>{number}</div>
      <div style={{fontSize:28,lineHeight:1.4}}>{label}</div>
    </div>;
  })}</div>;
}
