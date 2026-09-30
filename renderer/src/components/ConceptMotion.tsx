import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {Icon} from './VisualScene';
import {animationTiming,activeConcept} from '../animation';

const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
/** Shared visual verbs operate on the planner's source-grounded concepts. */
export function ConceptMotion({scene,accent}:{scene:Scene;accent:string}) {
  const t=useCurrentFrame()/useVideoConfig().fps;
  const v=scene.visual!;const n=v.items.length;const times=animationTiming(scene);
  const focus=v.motion==='focus';const assembly=v.motion==='assemble';
  const active=activeConcept(scene,t);const width=n>3?290:365;
  const xs=v.items.map((_,i)=>200+i*1200/Math.max(1,n-1));
  const reveal=(i:number)=>interpolate(t,[times[i],times[i]+.7],[0,1],clamp);
  return <div style={{height:440,position:'relative'}}>
    <svg viewBox="0 0 1600 440" width="100%" height="100%" preserveAspectRatio="none" style={{position:'absolute',inset:0}}>
      {xs.slice(1).map((x,i)=><g key={i} opacity={focus? .6:reveal(i+1)}>
        <path d={`M${xs[i]+125} 180H${x-125}`} fill="none" stroke={accent} strokeOpacity=".25" strokeWidth="2"/>
        <path d={`M${xs[i]+125} 180H${x-125}`} fill="none" stroke={accent} strokeWidth="5" pathLength="1" strokeDasharray=".03 .2" strokeDashoffset={-t*.2}/>
      </g>)}
      {assembly&&xs.map((x,i)=><rect key={i} x={x-70} y="110" width="140" height="140" rx="26" fill="none" stroke={accent} strokeDasharray="5 8" opacity=".2"/>)}
    </svg>
    {v.items.map((label,i)=>{
      const r=reveal(i);const selected=active===i;
      const x=assembly?120+(xs[i]-120)*r:xs[i];
      const y=assembly?40+140*r:180;
      const visibility=focus?1:r;
      return <div key={i} style={{position:'absolute',left:`${x/16}%`,top:y-66,width,transformOrigin:'50% 66px',transform:`translateX(-50%) scale(${focus?(selected?1.13:.88):.8+.2*r})`,opacity:visibility*(focus&&!selected ? .45 : 1),textAlign:'center'}}>
        <div style={{display:'inline-flex',padding:26,borderRadius:assembly?24:100,border:`2px solid ${accent}`,color:accent,background:'#163a48',boxShadow:selected?`0 0 65px ${accent}20`:undefined}}><Icon kind={v.icons?.[i]??v.icon??'idea'} size={76}/></div>
        <div style={{fontSize:n>3?25:30,lineHeight:1.35,marginTop:22,overflowWrap:'anywhere'}}>{label}</div>
      </div>;
    })}
    <div style={{position:'absolute',bottom:8,left:0,right:0,textAlign:'center',color:accent,fontSize:19,letterSpacing:3}}>{focus?'FOLLOW THE CONNECTION':assembly?'BUILD THE EXPLANATION':'ONE IDEA AT A TIME'}</div>
  </div>;
}
