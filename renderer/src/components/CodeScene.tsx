import {useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
export function CodeScene({scene,accent,panel}:{scene:Scene;accent:string;panel:string}) {
  const frame=useCurrentFrame(),{fps}=useVideoConfig();const lines=scene.visual!.codeLines!;
  const active=Math.min(lines.length-1,Math.floor(frame/fps/Math.max(.1,scene.duration*.8/lines.length)));
  const start=Math.max(0,Math.min(lines.length-8,active-5));
  return <div style={{height:440,background:panel,borderRadius:20,padding:'28px 40px',boxSizing:'border-box',overflow:'hidden'}}>
    <div style={{fontSize:18,letterSpacing:3,color:accent,marginBottom:16}}>CODE WALKTHROUGH</div>
    {lines.slice(start,start+8).map((line,i)=><div key={i+start} style={{display:'flex',fontFamily:'Consolas, monospace',fontSize:22,lineHeight:1.65,opacity:i+start<=active?1:.3,background:i+start===active?`${accent}18`:undefined}}><span style={{width:50,color:accent}}>{i+start+1}</span><span style={{whiteSpace:'pre'}}>{line}</span></div>)}
  </div>;
}
