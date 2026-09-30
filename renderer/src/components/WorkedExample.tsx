import {useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {exampleStage} from '../worked-example';

const titles={tokens:'Split text into tokens',ids:'Each token has an ID',process:'Use context to predict what comes next',generate:'One measured continuation'};
export function WorkedExample({scene,accent,panel}:{scene:Scene;accent:string;panel:string}) {
  const frame=useCurrentFrame(),{fps}=useVideoConfig();
  const spec=scene.visual!.worked!,data=scene.visual!.workedData!;
  const {action,progress}=exampleStage(scene,frame/fps);
  const count=action==='tokens'?Math.ceil(progress*data.tokens.length):data.tokens.length;
  const prefix=action==='generate'?data.prefixes[Math.ceil(progress*data.prefixes.length)-1]??'':'';
  return <div style={{height:470,background:panel,borderRadius:24,padding:'24px 34px',boxSizing:'border-box',border:`1px solid ${accent}44`}}>
    <div style={{display:'flex',justifyContent:'space-between',fontSize:20,color:accent}}><span>{spec.label}</span><span>{action?titles[action]:'Example input'}</span></div>
    <div style={{fontSize:32,margin:'14px 0 20px',whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{spec.input}</div>
    <div style={{display:'flex',flexWrap:'wrap',gap:9,minHeight:90}}>
      {action && data.tokens.map((token,i)=><div key={i} style={{opacity:i<count?1:0,background:`hsl(${(i*47+190)%360} 40% 24%)`,border:'1px solid #ffffff33',borderRadius:9,padding:'8px 12px',fontSize:23,maxWidth:300,overflowWrap:'anywhere',whiteSpace:'pre-wrap'}}>
        {typeof token.piece==='string'?token.piece.replace(/ /g,'\u00b7'): 'bytes '+token.piece.map(b=>b.toString(16).padStart(2,'0')).join(' ')}
        {action!=='tokens'&&<div style={{fontSize:17,color:'#d3dedf',marginTop:6}}>ID {token.id}</div>}
      </div>)}
    </div>
    {action==='process'&&<div style={{display:'flex',gap:22,alignItems:'center',marginTop:22}}>{['Context','Model layers','Next-token output'].map((label,i)=><div key={label} style={{display:'flex',gap:22,alignItems:'center',flex:1}}>{i>0&&<span style={{color:accent}}>→</span>}<div style={{padding:20,flex:1,border:`2px solid ${progress>=i/3?accent:'#ffffff33'}`,borderRadius:12,fontSize:26}}>{label}</div></div>)}</div>}
    {action==='generate'&&<div style={{fontSize:data.continuation.length>240?23:32,lineHeight:1.45,color:accent,whiteSpace:'pre-wrap',overflowWrap:'anywhere',maxHeight:160,overflow:'hidden'}}>{prefix || (progress===1?'(No visible text returned)':'…')}</div>}
    <div style={{position:'absolute',bottom:22,left:140,right:140,fontSize:17,color:'#aebfc8'}}>{action==='process'?'Schematic: no measured activations or weights.':action==='generate'?'Actual local-model output; illustrative reveal speed. This continuation is not a factual guarantee.':'Actual tokenizer output. Dots show spaces; byte pieces are labeled.'}<div style={{marginTop:5}}>Model: {data.model.model}</div></div>
  </div>;
}
