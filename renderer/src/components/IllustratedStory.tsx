import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {captionPhrases, sceneTransition} from '../presentation';
import {cueProgress, objectState} from '../choreography';
import {cameraAt,shotPosition} from '../shot-direction';
import {ActionStage} from './ActionStage';

const ink='#173044', teal='#087e81', coral='#e7805e', paper='#fbfaf5';
const clamp=(n:number)=>Math.max(0,Math.min(1,n));

/** These illustrations are drawn locally from editable SVG shapes. Labels and
 * action times come exclusively from the validated, sentence-cited plan. */
function Glyph({label}:{label:string}){
  const word=label.toLowerCase();
  const stroke={stroke:ink,strokeWidth:4,strokeLinecap:'round' as const,strokeLinejoin:'round' as const,fill:'none'};
  if(/question|prompt|chat|message/.test(word))return <g {...stroke}><path d="M-38-28h76v49h-39l-16 14V21h-21z" fill="#ddf1eb"/><path d="M-15-8h31M-15 5h20"/></g>;
  if(/tokenizer|split|pieces|tokens|words/.test(word))return <g {...stroke}><rect x="-46" y="-22" width="27" height="44" rx="5" fill="#fae6b1"/><rect x="-13" y="-22" width="27" height="44" rx="5" fill="#d7ece9"/><rect x="20" y="-22" width="27" height="44" rx="5" fill="#f9d9ca"/></g>;
  if(/context|capacity|window|budget/.test(word))return <g {...stroke}><rect x="-45" y="-30" width="90" height="60" rx="7" fill="#ddf1eb"/><path d="M-45-12h90M-30 0h25M-30 12h48"/></g>;
  if(/history|older|conversation|summary/.test(word))return <g {...stroke}><circle r="33" fill="#fff0dc"/><path d="M0-22v24l18 10M-27-28l-7 15 16-4"/></g>;
  if(/document|retriev|evidence|policy|source/.test(word))return <g {...stroke}><path d="M-30-34h44l17 17v51h-61z" fill="#fff0dc"/><path d="M14-34v18h17M-18-3h35M-18 10h35M-18 22h24"/></g>;
  if(/answer|output|generat|response/.test(word))return <g {...stroke}><path d="M-35-27h70v43h-35l-16 14V16h-19z" fill="#e8e3f8"/><path d="M0-13l4 9 9 4-9 4-4 9-4-9-9-4 9-4z"/></g>;
  if(/memory|database|store|data/.test(word))return <g {...stroke}><ellipse cx="0" cy="-21" rx="34" ry="11" fill="#e8e3f8"/><path d="M-34-21v42c0 17 68 17 68 0v-42M-34 0c0 16 68 16 68 0"/></g>;
  if(/model|weight|network|embedding/.test(word))return <g {...stroke}><path d="M-29-23L25 1M-29 19L25 1M-29-23L25-27M-29 19L25 27"/>{[[-29,-23],[-29,19],[25,-27],[25,1],[25,27]].map(([x,y])=><circle key={`${x}-${y}`} cx={x} cy={y} r="8" fill="#e8e3f8"/>)}</g>;
  if(/water|rain|cloud|river/.test(word))return <g {...stroke}><path d="M0-38C-11-14-28 4-28 15a28 28 0 0 0 56 0C28 4 11-14 0-38z" fill="#d7ece9"/></g>;
  if(/seed|plant|root|leaf|stem/.test(word))return <g {...stroke}><path d="M0 30V-7M0 4C-34-1-39-30-12-27 2-26 7-10 0 4zm0-12c25-30 51-12 31 6C21 7 10 7 0-8z" fill="#ddefd1"/></g>;
  return <g {...stroke}><rect x="-38" y="-30" width="76" height="60" rx="10" fill="#ddf1eb"/><circle cx="-17" cy="-7" r="5" fill={teal}/><path d="M-5-7h28M-22 9h45"/></g>;
}

function Person({x,y}:{x:number;y:number}){
  return <g transform={`translate(${x} ${y})`} stroke={ink} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round">
    <ellipse cx="0" cy="123" rx="70" ry="10" fill="#e5e9e4" stroke="none"/>
    <path d="M-33 116l8-56h54l10 56" fill="#5b9faa"/>
    <path d="M-20 64l-14 35 27 11M20 64l25 34-26 10" fill="none"/>
    <circle cx="0" cy="32" r="28" fill="#eac3a7"/>
    <path d="M-28 32q-7-43 30-40 35 2 26 45Q13 16 2 13q-10 15-30 19" fill="#374655"/>
    <path d="M-9 36h1m16 0h1M-7 48q8 7 17 0" fill="none"/>
    <path d="M-44 111h88l10 8H-54z" fill="#dbe9ee"/>
  </g>;
}

function labelLines(label:string){
  if(label.length<19)return [label];
  const words=label.split(' '),half=Math.ceil(words.length/2);
  return [words.slice(0,half).join(' '),words.slice(half).join(' ')];
}

export function IllustratedStory({scene,style,previous,first}:{scene:Scene;style?:VideoData['style'];previous?:Scene;first:boolean}){
  const frame=useCurrentFrame(),{fps}=useVideoConfig(),t=frame/fps,c=scene.choreography!;
  const layout=c.layout,workspace=layout==='workspace',n=c.objects.length;
  const beat=captionPhrases(scene).find(b=>t>=b.start&&t<b.end);
  const transition=sceneTransition(scene.visual?.transition,t/.5,first);
  const person=/\b(chat box|chatbot|typed|current question|your question)\b/i.test(scene.narration)&&layout==='sequence';
  const states=c.objects.map((_,i)=>objectState(c,i,t));
  const previousPlan=previous?.choreography;
  const camera=cameraAt(scene,t);
  const currentShot=scene.shots?.[camera.index];
  return <AbsoluteFill style={{background:paper,color:ink,fontFamily:'Segoe UI, Arial, sans-serif',overflow:'hidden',...transition}}>
    <div style={{position:'absolute',top:0,left:0,right:0,height:16,background:teal}}/>
    <div style={{position:'absolute',top:52,left:95,right:95,display:'flex',justifyContent:'space-between',fontSize:18,letterSpacing:3,fontWeight:700,color:teal}}><span>{style?.brand??'VISUALFORGE AI'}</span><span>EXPLAINED VISUALLY</span></div>
    <h1 style={{position:'absolute',top:113,left:95,right:95,margin:0,fontSize:65,lineHeight:1.12,letterSpacing:-2.5,fontWeight:750}}>{scene.headline}</h1>
    <p style={{position:'absolute',top:212,left:98,right:98,margin:0,color:'#54707b',fontSize:29}}>{scene.body}</p>
    <svg viewBox="0 0 1600 500" style={{position:'absolute',left:95,top:303,width:1730,height:540}} role="img" aria-label={`${layout} illustration synchronized to spoken sentences`}>
      <defs><marker id="story-arrow" markerWidth="12" markerHeight="12" refX="9" refY="6" orient="auto"><path d="M2 2l8 4-8 4" fill="none" stroke={coral} strokeWidth="2"/></marker><clipPath id={`story-stage-${scene.id}`}><rect x="6" y="6" width="1588" height="483" rx="30"/></clipPath></defs>
      <rect x="5" y="5" width="1590" height="485" rx="32" fill="#fff" stroke="#d7e3e0" strokeWidth="2"/>
      <path d="M65 458H1535" stroke="#e5eeeb" strokeWidth="2"/>
      <g clipPath={`url(#story-stage-${scene.id})`}><g transform={`translate(${camera.x} ${camera.y}) scale(${camera.scale})`}>
      {scene.actions?<ActionStage scene={scene} previous={previous} time={t} shotIndex={camera.index}/>:<>
      {workspace&&<g><rect x="95" y="55" width="1410" height="390" rx="28" fill="#e9f4f0" stroke={teal} strokeWidth="3"/><path d="M95 120H1505" stroke={teal} strokeOpacity=".35" strokeWidth="2"/><text x="135" y="99" fontSize="26" fill={teal} fontWeight="700">CONTEXT AVAILABLE TO THIS REQUEST</text></g>}
      {layout==='comparison'&&<path d="M800 70V435" stroke="#cbdad7" strokeDasharray="9 12" strokeWidth="3"/>}
      {layout==='connections'&&<circle cx="800" cy="225" r="55" fill="#e9f4f0" stroke={teal} strokeWidth="3"/>}
      {person&&<Person x={100} y={350}/>}
      {c.steps.filter(s=>s.action==='connect'&&s.start<=t).map((step,i)=>{
        const [a,b]=step.targets,[ax,ay]=shotPosition(layout,a,n),[bx,by]=shotPosition(layout,b,n);
        const progress=cueProgress(t,step.start,step.end);
        const distance=Math.max(1,Math.hypot(bx-ax,by-ay)),ux=(bx-ax)/distance,uy=(by-ay)/distance;
        const sx=ax+ux*79,sy=ay+uy*79,ex=bx-ux*85,ey=by-uy*85;
        return <path key={`path-${i}`} d={`M${sx} ${sy} Q${(sx+ex)/2} ${Math.min(sy,ey)-55} ${ex} ${ey}`} fill="none" stroke={coral} strokeWidth="5" pathLength="1" strokeDasharray="1" strokeDashoffset={1-progress} markerEnd="url(#story-arrow)"/>;
      })}
      {c.objects.map((object,i)=>{
        const s=states[i],oldIndex=previousPlan?.objects.findIndex(o=>o.label.toLowerCase()===object.label.toLowerCase())??-1;
        const oldState=previousPlan&&oldIndex>=0?objectState(previousPlan,oldIndex,previous!.duration):null;
        const carried=!!oldState?.visible&&!oldState.removed&&previousPlan?.layout===layout;
        if(!s.visible&&!carried)return null;
        const [x,y]=shotPosition(layout,i,n),[oldX,oldY]=carried?shotPosition(layout,oldIndex,previousPlan!.objects.length):[x,y];
        const blend=clamp(t/.65),shown=carried?1:s.entrance,opacity=shown*(1-s.removed*.72);
        const lines=labelLines(object.label),radius=workspace?60:72;
        const focused=currentShot?.mode!=='wide'&&currentShot?.focus===i;
        const dimmed=currentShot?.mode==='detail'&&currentShot.focus!==null&&!focused;
        const emphasis=focused?1.12:1;
        return <g key={`${object.label}-${i}`} transform={`translate(${oldX+(x-oldX)*blend} ${oldY+(y-oldY)*blend-s.removed*125+(1-shown)*40})`} opacity={opacity*(dimmed?.48:1)}>
          <g transform={`scale(${emphasis})`}>
            {focused&&<circle cy="-23" r={radius+13} fill="none" stroke={coral} strokeWidth="3" strokeDasharray="9 7"/>}
            <circle cy="-23" r={radius} fill={focused||s.active?'#fff0e7':'#e9f4f0'} stroke={focused||s.active?coral:'#a4cfca'} strokeWidth={focused||s.active?4:2.5}/>
            <g transform="translate(0 -23)"><Glyph label={object.label}/></g>
            {lines.map((line,k)=><text key={k} x="0" y={(workspace?44:77)+k*(workspace?22:24)} textAnchor="middle" fontSize={line.length>19?19:23} fontWeight="700" fill={ink}>{line}</text>)}
            {s.removed>0&&<text x="0" y="-113" textAnchor="middle" fontSize="20" fill={coral}>OUTSIDE THIS REQUEST</text>}
          </g>
        </g>;
      })}
      </>}
      </g></g>
      {!scene.actions&&<text x="800" y="481" textAnchor="middle" fontSize="18" fill="#68818a">{c.note}{workspace?'  |  Spacing does not represent token counts':''}</text>}
    </svg>
    {beat&&<div style={{position:'absolute',bottom:83,left:210,right:210,textAlign:'center',fontSize:29,lineHeight:1.35,fontWeight:550}}><span style={{background:'#fff',border:'1px solid #d7e3e0',boxShadow:'0 8px 22px #17304413',padding:'11px 22px',borderRadius:12,boxDecorationBreak:'clone'}}>{beat.text}</span></div>}
    <div style={{position:'absolute',bottom:0,left:0,height:7,width:`${Math.min(100,t/scene.duration*100)}%`,background:teal}}/>
  </AbsoluteFill>;
}
