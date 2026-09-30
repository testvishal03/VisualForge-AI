import {useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {demonstrationStep} from '../code-example';

export function CodeDemonstration({scene,accent}:{scene:Scene;accent:string}){
  const time=useCurrentFrame()/useVideoConfig().fps,demo=scene.demonstration!;
  const active=demonstrationStep(demo,time),started=time>=demo.at[0],step=demo.steps[active];
  const python=demo.spec.kind.startsWith('python_');
  const table=(columns:string[],rows:(string|number)[][],highlight?:number)=><table style={{borderCollapse:'collapse',width:'100%',fontSize:22}}><thead><tr>{columns.map(c=><th key={c} style={{textAlign:'left',padding:10,color:accent}}>{c}</th>)}</tr></thead><tbody>{rows.map((row,i)=><tr key={i} style={{background:started&&row[0]===highlight?`${accent}35`:'transparent'}}>{row.map((cell,j)=><td key={j} style={{padding:10,borderTop:'1px solid #ffffff22'}}>{String(cell)}</td>)}</tr>)}</tbody></table>;
  return <div style={{display:'flex',gap:40,height:455}}>
    <div style={{width:python?850:690,background:'#07151faa',borderRadius:20,padding:25,boxSizing:'border-box'}}>
      <div style={{color:accent,fontSize:20,letterSpacing:2,marginBottom:20}}>{python?'PYTHON EXECUTION':'SQL QUERY'}</div>
      {demo.code.map((line,i)=><div key={i} style={{fontFamily:'Consolas, monospace',whiteSpace:'pre',fontSize:python?27:20,lineHeight:1.7,background:started&&step.line===i+1?`${accent}30`:undefined,padding:'0 8px'}}><span style={{opacity:.4,marginRight:20}}>{i+1}</span>{line}</div>)}
      <div style={{fontSize:18,opacity:.6,marginTop:28}}>Computed example · Animation pacing is illustrative.</div>
    </div>
    {python?<div style={{flex:1,padding:20}}>
      <div style={{color:accent,fontSize:23,marginBottom:20}}>VARIABLES AFTER THIS STEP</div>
      {Object.entries(started?step.variables??{}:{}).map(([name,value])=><div key={name} style={{display:'flex',justifyContent:'space-between',fontSize:32,padding:'13px 20px',borderBottom:'1px solid #ffffff22'}}><span>{name}</span><span>{typeof value==='boolean'?(value?'True':'False'):value}</span></div>)}
      <div style={{marginTop:35,fontSize:23,color:accent}}>OUTPUT</div><pre style={{fontSize:34}}>{started?step.output?.join('\n'):''}</pre>
    </div>:<div style={{flex:1,display:'flex',gap:25}}>
      <div style={{flex:1}}><div style={{fontSize:23,color:accent}}>Orders</div>{table(['id','customer','amount'],demo.orders!,step.order_id)}
        {demo.spec.kind==='sql_join'&&<><div style={{fontSize:23,color:accent,marginTop:15}}>Customers</div>{table(['id','name'],demo.customers!,step.customer_id??undefined)}</>}
      </div>
      <div style={{flex:1}}><div style={{fontSize:23,color:accent}}>Result</div>{table(demo.columns!,started?step.rows??[]:[])}{started&&!step.rows?.length&&<p style={{fontSize:20,opacity:.7}}>No matching rows yet</p>}</div>
    </div>}
  </div>;
}
