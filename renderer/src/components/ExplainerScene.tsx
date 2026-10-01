import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {after, inside, noise, type Explainer} from '../explainer';
import {backgroundProgress, bridgedFrom, BRIDGE_HEADLINE_DELAY, easeInOut, easeOut, enterProgress, exitProgress, isIllustrated, sceneSeconds} from '../transitions';
import {fitLabel} from '../labels';
import {Caption} from './Caption';
import {Glyph} from './IllustratedStory';

const ink='#173044',teal='#087e81',coral='#e7805e',paper='#fbfaf5',muted='#54707b';
const chipTones=['#fae6b1','#d7ece9','#f9d9ca','#e8e3f8','#dce9f6'];
const pop=(p:number)=>{const e=easeOut(p);return e+Math.sin(Math.PI*Math.min(1,p))*.08;};

/** Light-board scene shell shared by every explainer: headline, stage, caption and transitions. */
export function ExplainerScene({scene,style,previous,first,guide}:{scene:Scene;style?:VideoData['style'];previous?:Scene;next?:Scene;first:boolean;guide:boolean}){
  const frame=useCurrentFrame(),{fps}=useVideoConfig(),t=frame/fps,e=scene.explainer!;
  const exit=exitProgress(t,sceneSeconds(scene,fps)),background=backgroundProgress(t,first);
  const lead=bridgedFrom(previous,scene,fps,guide)?BRIDGE_HEADLINE_DELAY:.12;
  const headline=enterProgress(t,lead,first),body=enterProgress(t,lead+.12,first);
  const stageIn=first||isIllustrated(previous)?1:enterProgress(t,.3,first);
  const move=(p:number)=>({opacity:p*(1-exit),transform:`translateY(${(1-p)*28-exit*18}px)`});
  return <AbsoluteFill style={{color:ink,fontFamily:'Segoe UI, Arial, sans-serif',overflow:'hidden'}}>
    <AbsoluteFill style={{background:paper,opacity:background}}/>
    <div style={{position:'absolute',top:0,left:0,right:0,height:16,background:teal,opacity:background}}/>
    <div style={{position:'absolute',top:52,left:95,fontSize:18,letterSpacing:3,fontWeight:700,color:teal,opacity:background}}>{style?.brand??'VISUALFORGE AI'}</div>
    <h1 style={{position:'absolute',top:113,left:95,right:95,margin:0,fontSize:65,lineHeight:1.12,letterSpacing:-2.5,fontWeight:750,...move(headline)}}>{scene.headline}</h1>
    <p style={{position:'absolute',top:212,left:98,right:98,margin:0,color:muted,fontSize:29,...move(body)}}>{scene.body}</p>
    <svg viewBox="0 0 1600 500" style={{position:'absolute',left:95,top:303,width:1730,height:540,opacity:stageIn*(1-exit)}} role="img" aria-label={`${e.kind} explainer synchronized to narration`}>
      <rect x="5" y="5" width="1590" height="485" rx="32" fill="#fff" stroke="#d7e3e0" strokeWidth="2"/>
      {e.kind==='next_token'&&<NextToken e={e} t={t}/>}
      {e.kind==='denoise'&&<Denoise e={e} t={t}/>}
      {e.kind==='contrast'&&<Contrast e={e} t={t}/>}
      {e.kind==='caveats'&&<Caveats e={e} t={t}/>}
      {e.kind==='steps'&&<Steps e={e} t={t}/>}
    </svg>
    <div style={{opacity:1-exit}}>
      <Caption scene={scene} t={t} highlight={teal} style={{position:'absolute',bottom:83,left:210,right:210,textAlign:'center',fontSize:29,lineHeight:1.35,fontWeight:550}} boxStyle={{background:'#fff',border:'1px solid #d7e3e0',boxShadow:'0 8px 22px #17304413',padding:'11px 22px',borderRadius:12}}/>
    </div>
    <div style={{position:'absolute',bottom:0,left:0,height:7,width:`${Math.min(100,t/scene.duration*100)}%`,background:teal,opacity:background}}/>
  </AbsoluteFill>;
}

/** "the cat sat on the ___": tokens appear, likely next pieces rise, one joins, and the loop repeats. */
function NextToken({e,t}:{e:Extract<Explainer,{kind:'next_token'}>;t:number}){
  const words=e.prompt.split(/\s+/),start=e.at.type??0,guess=e.at.guess,repeat=e.at.repeat;
  const widths=words.map(w=>Math.max(70,w.length*24+36));
  const chosen=e.candidates[0];
  const joined=guess!==undefined&&chosen?after(t,guess+1.4,.6):0;
  const extra=repeat===undefined?0:Math.min(6,Math.floor(Math.max(0,t-repeat)/.35)+1);
  let x=100;
  const chips=words.map((w,i)=>{const at=x;x+=widths[i]+14;return {w,at,width:widths[i],p:after(t,start+i*.22,.35)};});
  const slot=x;
  return <g>
    <text x="100" y="72" fontSize="22" fontWeight="700" letterSpacing="3" fill={teal}>{e.source==='example'?'EXAMPLE PROMPT':'PROMPT'}</text>
    {chips.map((c,i)=><g key={i} transform={`translate(${c.at} ${150+(1-easeOut(c.p))*30})`} opacity={c.p}>
      <rect width={c.width} height="78" rx="14" fill={chipTones[i%chipTones.length]} stroke={ink} strokeWidth="3"/>
      <text x={c.width/2} y="51" textAnchor="middle" fontSize="36" fontWeight="700" fill={ink}>{c.w}</text>
    </g>)}
    {/* The slot the model fills: a pulsing "?" until the guess joins the sentence. */}
    <g transform={`translate(${slot} 150)`} opacity={after(t,start+words.length*.22,.3)*(1-joined)}>
      <rect width="110" height="78" rx="14" fill="#fff0e7" stroke={coral} strokeWidth="3" strokeDasharray="10 8"/>
      <text x="55" y="53" textAnchor="middle" fontSize="40" fontWeight="800" fill={coral} opacity={.55+.45*Math.sin(t*5)**2}>?</text>
    </g>
    {chosen&&joined>0&&<g transform={`translate(${slot} ${150+(1-easeInOut(joined))*170})`}>
      <rect width={Math.max(70,chosen.length*24+36)} height="78" rx="14" fill="#fff0e7" stroke={coral} strokeWidth="4"/>
      <text x={Math.max(70,chosen.length*24+36)/2} y="51" textAnchor="middle" fontSize="36" fontWeight="800" fill={ink}>{chosen}</text>
    </g>}
    {guess!==undefined&&(e.candidates.length?<g>
      <text x="100" y="292" fontSize="22" fontWeight="700" letterSpacing="3" fill={muted}>{e.measured?`NEXT-TOKEN ODDS · MEASURED WITH ${e.model!.toUpperCase()}`:'LIKELY NEXT PIECES (ILLUSTRATIVE)'}</text>
      {e.candidates.map((c,i)=>{const p=after(t,guess+i*.18,.5),share=e.measured&&e.probs?e.probs[i]:[1,.56,.32][i],len=Math.max(6,share*620);
        return <g key={c} transform={`translate(100 ${318+i*52})`} opacity={p*(i===0?1-joined*.5:1)}>
          <text x="0" y="30" fontSize="28" fontWeight="700" fill={ink}>{c}</text>
          <rect x="170" y="8" width={len*easeOut(p)} height="30" rx="8" fill={i===0?coral:'#a4cfca'}/>
          {e.measured&&e.probs&&<text x={182+len*easeOut(p)} y="32" fontSize="24" fontWeight="700" fill={muted} opacity={p}>{(e.probs[i]*100).toFixed(e.probs[i]<.1?1:0)}%</text>}
        </g>;})}
    </g>:<text x="100" y="330" fontSize="30" fill={muted} opacity={after(t,guess)}>The model picks the most likely next piece.</text>)}
    {extra>0&&<g>
      {Array.from({length:extra},(_,i)=><rect key={i} x={slot+(chosen?Math.max(70,chosen.length*24+36):110)+16+i*42} y="172" width="30" height="34" rx="7" fill={chipTones[i%chipTones.length]} stroke={ink} strokeWidth="2.5" opacity={after(t,repeat!+i*.35,.25)}/>)}
      <g transform="translate(1180 300)" opacity={after(t,repeat)}>
        <path d="M0 40a60 60 0 1 1 30 52" fill="none" stroke={teal} strokeWidth="8" strokeLinecap="round" transform={`rotate(${(t-repeat!)*140} 60 40)`}/>
        <text x="60" y="160" textAnchor="middle" fontSize="26" fontWeight="700" fill={teal}>repeat</text>
      </g>
    </g>}
  </g>;
}

/** Static resolves into the requested picture, one denoising step at a time. */
function Denoise({e,t}:{e:Extract<Explainer,{kind:'denoise'}>;t:number}){
  const n=26,size=15,ox=980,oy=50,steps=30;
  const shown=after(t,e.at.noise,.5);
  const clean=e.at.clean===undefined?0:easeInOut(Math.max(0,Math.min(1,(t-e.at.clean)/Math.max(1.5,e.end-e.at.clean))));
  const step=Math.round(clean*steps),churn=Math.floor(t*8);
  const cells=[];
  for(let i=0;i<n;i++)for(let j=0;j<n;j++){
    const target=inside(e.subject,(i+.5)/n*2-1,(j+.5)/n*2-1)?1:0;
    const v=target*clean+noise(i,j,churn)*(1-clean);
    cells.push(<rect key={`${i}-${j}`} x={ox+i*size} y={oy+j*size} width={size-1} height={size-1} fill={v>.5?coral:'#e8eeec'} opacity={.25+.75*Math.abs(v-.5)*2}/>);
  }
  return <g opacity={shown}>
    <text x="100" y="110" fontSize="22" fontWeight="700" letterSpacing="3" fill={teal}>PROMPT</text>
    <g transform="translate(100 135)"><rect width="420" height="84" rx="16" fill="#fff0e7" stroke={coral} strokeWidth="3"/>
      <text x="28" y="54" fontSize="34" fontWeight="700" fill={ink}>{e.named?`“a ${e.subject}”`:'your prompt'}</text></g>
    <text x="100" y="300" fontSize="30" fontWeight="700" fill={ink}>{clean<.02?'Start: pure static':clean>.98?'Matches the prompt':'Cleaning up the static…'}</text>
    <text x="100" y="345" fontSize="24" fill={muted}>denoising step {step} / {steps} (illustrative)</text>
    <rect x="100" y="372" width="420" height="14" rx="7" fill="#e5eeeb"/><rect x="100" y="372" width={420*clean} height="14" rx="7" fill={teal}/>
    <path d="M610 250h260" stroke={teal} strokeWidth="6" strokeLinecap="round" strokeDasharray="4 16"/><path d="M856 236l18 14-18 14" fill="none" stroke={teal} strokeWidth="6" strokeLinecap="round"/>
    <rect x={ox-12} y={oy-12} width={n*size+23} height={n*size+23} rx="18" fill="#fff" stroke="#d7e3e0" strokeWidth="3"/>
    {cells}
  </g>;
}

/** One kind of AI sorts what it sees into boxes; the other makes something new. */
function Contrast({e,t}:{e:Extract<Explainer,{kind:'contrast'}>;t:number}){
  const left=after(t,e.at.left,.6),right=after(t,e.at.right,.6);
  const drop=easeInOut(after(t,(e.at.left??0)+.9,1)),draw=easeInOut(after(t,(e.at.right??0)+.7,1.6));
  const subject=e.bins.find(b=>/cat|dog|bird|fish|car|house|tree|flower/i.test(b))?.toLowerCase();
  const panel=(x:number,p:number,title:string,verb:string,color:string)=><g opacity={p} transform={`translate(${x} ${(1-easeOut(p))*30})`}>
    <rect width="660" height="410" rx="26" fill={`${color}14`} stroke={color} strokeWidth="3"/>
    <text x="36" y="62" fontSize={fitLabel(title,420,40,28).fontSize} fontWeight="800" fill={ink}>{title}</text>
    <rect x="490" y="28" width="140" height="48" rx="24" fill={color}/><text x="560" y="61" textAnchor="middle" fontSize="24" fontWeight="800" fill="#fff">{verb.toUpperCase()}</text>
  </g>;
  return <g>
    {panel(60,left,e.left.title,e.left.verb,teal)}
    {panel(880,right,e.right.title,e.right.verb,coral)}
    <g opacity={left}>
      {/* An input travels down into the box it belongs to. */}
      <g transform={`translate(${330-drop*130} ${140+drop*150})`}><rect x="-55" y="-45" width="110" height="90" rx="12" fill="#fff" stroke={ink} strokeWidth="3"/>
        <g transform="scale(.9)"><Doodle kind={subject??'image'}/></g></g>
      {(e.bins.length?e.bins:['?','?']).map((b,i)=><g key={i} transform={`translate(${140+i*260} 330)`}>
        <path d="M0 0h200l-20 100H20z" fill="#fff" stroke={i===0&&drop>.95?teal:'#a4cfca'} strokeWidth={i===0&&drop>.95?5:3}/>
        <text x="100" y="62" textAnchor="middle" fontSize="30" fontWeight="700" fill={ink}>{b}</text></g>)}
    </g>
    <g opacity={right} transform="translate(1210 270)">
      {/* Something new is drawn line by line, with sparkles. */}
      <circle r="120" fill="#fff0e7" stroke={coral} strokeWidth="3" strokeDasharray="14 10"/>
      <g transform="scale(2.2)"><Doodle kind={subject??'star'} draw={draw} hoodie={subject==='cat'&&!!e.hoodie}/></g>
      {[0,1,2,3].map(i=>{const a=i*Math.PI/2+t*1.4,s=Math.sin(t*4+i)*.5+.5;return <path key={i} d="M0-14l4 10 10 4-10 4-4 10-4-10-10-4 10-4z" fill={coral} opacity={draw*s} transform={`translate(${Math.cos(a)*150} ${Math.sin(a)*150}) scale(${.8+s*.6})`}/>;})}
    </g>
    <path d="M760 270h90" stroke={muted} strokeWidth="6" strokeLinecap="round" opacity={right}/><path d="M840 256l18 14-18 14" fill="none" stroke={muted} strokeWidth="6" opacity={right}/>
  </g>;
}

/** Simple line drawings for subjects a contrast names; `hoodie` adds the hood from "a cat in a hoodie". */
function Doodle({kind,draw=1,hoodie=false}:{kind:string;draw?:number;hoodie?:boolean}){
  const line={fill:'none',stroke:ink,strokeWidth:4,strokeLinecap:'round' as const,strokeLinejoin:'round' as const,pathLength:1,strokeDasharray:1,strokeDashoffset:1-draw};
  if(kind==='dog')return <g><path d="M-30-8a30 30 0 1 0 60 0a30 30 0 1 0-60 0M-30-14q-18 2-16 26M30-14q18 2 16 26M-10-6h1M10-6h1M-6 10q6 6 12 0" {...line}/><ellipse cy="4" rx="7" ry="5" fill={ink} opacity={draw}/></g>;
  if(kind==='cat')return <g>
    {hoodie&&<path d="M-48 30q0-70 48-74q48 4 48 74q-48 18-96 0z" fill="#f9d9ca" stroke={coral} strokeWidth="4" opacity={draw}/>}
    <path d="M-30 4a30 30 0 1 0 60 0a30 30 0 1 0-60 0M-26-12l-6-28 22 14M26-12l6-28-22 14M-10 0h1M10 0h1M-4 12l4 4 4-4M-34 10h-18M34 10h18" {...line}/>
  </g>;
  return <Glyph label={kind}/>;
}

function CaveatIcon({kind}:{kind:string}){
  const s={fill:'none',stroke:ink,strokeWidth:5,strokeLinecap:'round' as const,strokeLinejoin:'round' as const};
  if(kind==='wrong')return <g {...s}><path d="M0-48L52 42H-52z" fill="#fae6b1"/><path d="M0-14v28M0 28v1"/></g>;
  if(kind==='bias')return <g {...s}><path d="M0-46v84M-40 38h80M-50-30h100"/><path d="M-50-30l-18 40h36zM50-30l-18 40h36z" fill="#e8e3f8"/></g>;
  if(kind==='editor')return <g {...s}><rect x="-40" y="-46" width="80" height="92" rx="10" fill="#d7ece9"/><path d="M-20 0l14 14 28-30"/></g>;
  return <g {...s}><rect x="-38" y="-6" width="76" height="56" rx="10" fill="#f9d9ca"/><path d="M-22-6v-16a22 22 0 0 1 44 0v16"/></g>;
}

/** Limitation cards pop in as each limitation is named. */
function Caveats({e,t}:{e:Extract<Explainer,{kind:'caveats'}>;t:number}){
  const n=e.cards.length,width=Math.min(400,(1440-(n-1)*40)/n),x0=(1600-(n*width+(n-1)*40))/2;
  return <g>{e.cards.map((c,i)=>{
    const p=after(t,e.at[c.key],.55),shake=c.key==='wrong'&&p>0&&p<1?Math.sin(p*30)*6*(1-p):0;
    return <g key={c.key} transform={`translate(${x0+i*(width+40)+width/2+shake} 250) scale(${.6+.4*pop(p)})`} opacity={Math.min(1,p*1.5)}>
      <rect x={-width/2} y="-185" width={width} height="370" rx="28" fill={i%2?'#fff0e7':'#e9f4f0'} stroke={i%2?coral:teal} strokeWidth="4"/>
      <g transform="translate(0 -60)"><CaveatIcon kind={c.key}/></g>
      <text y="90" textAnchor="middle" fontSize={fitLabel(c.title,width-40,40,26).fontSize} fontWeight="800" fill={ink}>{c.title}</text>
    </g>;})}</g>;
}

function StepIcon({kind,t}:{kind:string;t:number}){
  const s={fill:'none',stroke:ink,strokeWidth:5,strokeLinecap:'round' as const,strokeLinejoin:'round' as const};
  if(kind==='feed')return <g {...s}>{[0,1,2].map(i=><rect key={i} x={-44+i*10} y={-40+i*14} width="70" height="52" rx="8" fill={chipTones[i]}/>)}</g>;
  if(kind==='patterns')return <g {...s}>{[-34,0,34].map((x,i)=><g key={i} transform={`translate(${x} 0)`}><circle r="15" fill="#e8e3f8"/><path d={`M0 0L${Math.cos(t*2+i*2)*13} ${Math.sin(t*2+i*2)*13}`}/></g>)}<path d="M-50 30h100"/></g>;
  if(kind==='prompt')return <g {...s}><path d="M-46-34h92v54H4l-20 18v-18h-30z" fill="#fff0dc"/>{[-18,0,18].map((x,i)=><circle key={i} cx={x} cy="-7" r="4" fill={ink} opacity={.35+.65*(Math.sin(t*6-i)*.5+.5)}/>)}</g>;
  return <g {...s}><circle r="38" fill="#d7ece9"/></g>;
}

/** Numbered stage cards that appear as the narration reaches each step. */
function Steps({e,t}:{e:Extract<Explainer,{kind:'steps'}>;t:number}){
  const n=e.steps.length,width=Math.min(380,(1400-(n-1)*70)/n),x0=(1600-(n*width+(n-1)*70))/2;
  return <g>{e.steps.map((st,i)=>{
    const p=after(t,e.at[`s${i}`],.55),x=x0+i*(width+70);
    const detail=fitLabel(st.detail,width-40,26,18);
    return <g key={i}>
      {i>0&&<g opacity={p}><path d={`M${x-58} 250h46`} stroke={muted} strokeWidth="6" strokeLinecap="round"/><path d={`M${x-24} 236l14 14-14 14`} fill="none" stroke={muted} strokeWidth="6" strokeLinecap="round"/></g>}
      <g transform={`translate(${x+width/2} 250) scale(${.7+.3*pop(p)})`} opacity={Math.min(1,p*1.5)}>
        <rect x={-width/2} y="-195" width={width} height="390" rx="28" fill={i%2?'#fff0e7':'#e9f4f0'} stroke={i%2?coral:teal} strokeWidth="4"/>
        <circle cx={-width/2+44} cy="-151" r="26" fill={i%2?coral:teal}/><text x={-width/2+44} y="-141" textAnchor="middle" fontSize="28" fontWeight="800" fill="#fff">{i+1}</text>
        <g transform="translate(0 -60) scale(1.3)"><StepIcon kind={st.key} t={t}/></g>
        <text y="55" textAnchor="middle" fontSize={fitLabel(st.title,width-40,38,26).fontSize} fontWeight="800" fill={ink}>{st.title}</text>
        {detail.lines.map((line,k)=><text key={k} y={105+k*(detail.fontSize+6)} textAnchor="middle" fontSize={detail.fontSize} fill={muted}>{line}</text>)}
      </g>
    </g>;})}</g>;
}

/** Title and takeaway cards on the light board, so a light video does not flip to the dark stage. */
export function LightCard({scene,style,previous,first,guide}:{scene:Scene;style?:VideoData['style'];previous?:Scene;first:boolean;guide:boolean}){
  const frame=useCurrentFrame(),{fps}=useVideoConfig(),t=frame/fps;
  const exit=exitProgress(t,sceneSeconds(scene,fps)),background=backgroundProgress(t,first);
  const lead=bridgedFrom(previous,scene,fps,guide)?BRIDGE_HEADLINE_DELAY:.12;
  const headline=enterProgress(t,lead,first),body=enterProgress(t,lead+.25,first),mark=enterProgress(t,lead+.45,first);
  const takeaway=scene.visual?.kind==='takeaway';
  const title=fitLabel(scene.headline,1500,takeaway?72:86,48);
  const move=(p:number)=>({opacity:p*(1-exit),transform:`translateY(${(1-p)*30-exit*18}px)`});
  return <AbsoluteFill style={{color:ink,fontFamily:'Segoe UI, Arial, sans-serif',overflow:'hidden'}}>
    <AbsoluteFill style={{background:paper,opacity:background}}/>
    <div style={{position:'absolute',top:0,left:0,right:0,height:16,background:teal,opacity:background}}/>
    <div style={{position:'absolute',top:52,left:95,fontSize:18,letterSpacing:3,fontWeight:700,color:teal,opacity:background}}>{style?.brand??'VISUALFORGE AI'}</div>
    <div style={{position:'absolute',left:150,right:150,top:takeaway?250:300}}>
      {takeaway&&<div style={{display:'flex',alignItems:'center',gap:16,fontSize:24,letterSpacing:5,fontWeight:800,color:coral,marginBottom:28,...move(mark)}}>
        <svg width="44" height="44" viewBox="0 0 44 44"><circle cx="22" cy="22" r="20" fill={coral}/><path d="M12 23l7 7 13-15" fill="none" stroke="#fff" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round"/></svg>KEY TAKEAWAY</div>}
      <div style={{fontSize:title.fontSize,lineHeight:1.08,fontWeight:800,letterSpacing:-2.5,...move(headline)}}>{title.lines.map((l,i)=><div key={i}>{l}</div>)}</div>
      <div style={{width:`${easeOut(mark)*220}px`,height:8,borderRadius:4,background:coral,margin:'34px 0',opacity:1-exit}}/>
      <p style={{fontSize:34,lineHeight:1.45,color:muted,maxWidth:1300,margin:0,...move(body)}}>{scene.body}</p>
    </div>
    <div style={{opacity:1-exit}}>
      <Caption scene={scene} t={t} highlight={teal} style={{position:'absolute',bottom:83,left:210,right:210,textAlign:'center',fontSize:29,lineHeight:1.35,fontWeight:550}} boxStyle={{background:'#fff',border:'1px solid #d7e3e0',boxShadow:'0 8px 22px #17304413',padding:'11px 22px',borderRadius:12}}/>
    </div>
    <div style={{position:'absolute',bottom:0,left:0,height:7,width:`${Math.min(100,t/scene.duration*100)}%`,background:teal,opacity:background}}/>
  </AbsoluteFill>;
}
