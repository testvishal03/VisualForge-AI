import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {contextCues} from '../context-window';
import {Icon} from './VisualScene';

export function ContextWindow({scene,accent}:{scene:Scene;accent:string}) {
  const time=useCurrentFrame()/useVideoConfig().fps;
  const visual=scene.visual!, cues=contextCues(scene);
  const latest=Math.max(...cues.filter(cue=>cue<=time),-1);
  return <div style={{display:'flex',alignItems:'center',gap:75,height:440}}>
    <div style={{width:1020,border:`2px solid ${accent}88`,borderRadius:28,padding:24,boxSizing:'border-box'}}>
      <div style={{color:accent,fontSize:21,letterSpacing:3,marginBottom:20}}>CONTEXT WINDOW</div>
      {visual.items.map((label,i)=>{
        const reveal=interpolate(time,[cues[i],cues[i]+.5],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
        const active=cues[i]===latest;
        return <div key={label} style={{height:61,marginTop:10,borderRadius:12,display:'flex',alignItems:'center',gap:20,padding:'0 22px',background:`${accent}${active?'30':'12'}`,border:`1px solid ${accent}${active?'99':'33'}`,opacity:reveal,transform:`translateX(${(1-reveal)*-20}px)`}}>
          <Icon kind={visual.icons?.[i]??'layers'} size={35}/><span style={{fontSize:27}}>{label}</span>
        </div>;
      })}
    </div>
    <div style={{maxWidth:460}}>
      <Icon kind="layers" size={100}/>
      <div style={{fontSize:34,lineHeight:1.3,marginTop:25}}>Selected context contents</div>
      <div style={{fontSize:22,lineHeight:1.4,opacity:.6,marginTop:20}}>Illustrative view. Band sizes do not represent token counts.</div>
    </div>
  </div>;
}
