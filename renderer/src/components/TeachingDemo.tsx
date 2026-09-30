import {interpolate,useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {teachingStage} from '../teaching-plan';

export function TeachingDemo({scene,accent}:{scene:Scene;accent:string}){
  const time=useCurrentFrame()/useVideoConfig().fps,plan=scene.teaching!;
  const active=teachingStage(plan,time);
  const reveal=(i:number)=>interpolate(time,[plan.at[i],plan.at[i]+.4],[0,1],{extrapolateLeft:'clamp',extrapolateRight:'clamp'});
  if(plan.component==='rag'){
    const stages=plan.steps.map((step,i)=>({...step,index:i})).filter((step,i,all)=>step.action!=='explain'&&all.findIndex(s=>s.action===step.action)===i).slice(0,4);
    return <div style={{height:440,display:'flex',alignItems:'center',gap:25}}>{stages.map((step,i)=><div key={step.index} style={{display:'flex',alignItems:'center',gap:25,flex:1,opacity:reveal(step.index)}}>
      {i>0&&<span style={{fontSize:48,color:accent}}>&rarr;</span>}
      <div style={{flex:1,minHeight:230,padding:25,borderRadius:22,border:`2px solid ${accent}${active===step.index?'dd':'44'}`,background:`${accent}12`}}>
        <div style={{fontSize:20,color:accent,textTransform:'uppercase',letterSpacing:2}}>{step.action==='retrieve'?'Find sources':step.action==='context'?'Provide context':'Generate response'}</div>
        <div style={{fontSize:38,marginTop:35}}>{step.label}</div>
        <div style={{fontSize:21,opacity:.65,marginTop:25}}>Step {i+1}</div>
      </div>
    </div>)}</div>;
  }
  const data=plan.example!,search=plan.component==='vector_search';
  const compared=plan.steps.some((step,i)=>step.action==='compare'&&time>=plan.at[i]);
  const encoded=plan.steps.some((step,i)=>step.action==='encode'&&time>=plan.at[i])||compared;
  return <div style={{display:'flex',gap:65,height:455,alignItems:'center'}}>
    <div style={{width:780,height:430,borderRadius:24,border:`1px solid ${accent}55`,background:`${accent}09`,padding:22,boxSizing:'border-box'}}>
      <div style={{fontSize:21,letterSpacing:2,color:accent}}>ILLUSTRATIVE TWO-DIMENSIONAL VECTORS</div>
      <svg viewBox="0 0 700 330" style={{width:'100%',height:350}}>
        <path d="M100 35V270H620" fill="none" stroke="#ffffff66" strokeWidth="2"/>
        <text x="540" y="310" fill="#fff" fontSize="18">Dimension 1</text><text x="10" y="22" fill="#fff" fontSize="18">Dimension 2</text>
        {data.points.map((point,i)=>{const x=100+point.vector[0]*440,y=270-point.vector[1]*210;return <g key={point.label} opacity={encoded?1:.12}>
          <path d={`M100 270L${x} ${y}`} stroke={i===0?accent:'#ffffff55'} strokeWidth={i===0?4:2}/>
          <circle cx={x} cy={y} r="9" fill={i===0?accent:'#ffbe92'}/>
          <text x={x+14} y={y-12} fill="#fff" fontSize="22">{point.label} [{point.vector.join(', ')}]</text>
        </g>;})}
      </svg>
    </div>
    <div style={{flex:1}}>
      <div style={{fontSize:34,marginBottom:24}}>{search?'Compare direction with a query':'Text becomes a numerical representation'}</div>
      <div style={{fontSize:25,color:accent,marginBottom:22}}>{search?'Example query: [1, 0]':'Example vector: [0.8, 0.6]'}</div>
      {search&&<div style={{opacity:compared?1:.2}}>{[...data.points].sort((a,b)=>b.cosine-a.cosine).map(point=><div key={point.label} style={{fontSize:27,display:'flex',justifyContent:'space-between',padding:'12px 20px',borderBottom:'1px solid #ffffff22'}}><span>Vector {point.label}</span><span>{point.cosine.toFixed(2)}</span></div>)}<div style={{fontSize:20,marginTop:12,opacity:.65}}>Cosine similarity, calculated from these vectors</div></div>}
      <div style={{fontSize:21,opacity:.65,lineHeight:1.5,marginTop:25}}>Toy coordinates, not model embeddings. These axes do not represent named meanings.</div>
    </div>
  </div>;
}
