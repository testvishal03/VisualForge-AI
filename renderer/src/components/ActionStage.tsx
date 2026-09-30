import type {Scene} from '../types';
import {cueProgress,objectState} from '../choreography';
import {actionPosition,activeAction} from '../visual-actions';
import {easeInOut} from '../transitions';
import {idleOffset,mentionPulse,mentionTimes} from '../emphasis';
import {fitLabel,objectScale} from '../labels';

const ink='#173044',teal='#087e81',coral='#e7805e';
const colors=['#d9efea','#ffe5d5','#e8e3f8','#faedc5','#dce9f6','#e7efd9'];

function MiniGlyph({label}:{label:string}){
  const value=label.toLowerCase();
  const shape={stroke:ink,strokeWidth:2.5,strokeLinecap:'round' as const,strokeLinejoin:'round' as const,fill:'none'};
  if(/tokenizer|pieces|tokens|words/.test(value))return <g {...shape}><rect x="-12" y="-8" width="7" height="17" rx="2" fill="#fff0cf"/><rect x="-2" y="-8" width="7" height="17" rx="2" fill="#d9efea"/><rect x="8" y="-8" width="7" height="17" rx="2" fill="#f7dbd0"/></g>;
  if(/context|window|budget/.test(value))return <g {...shape}><rect x="-15" y="-11" width="30" height="22" rx="3"/><path d="M-15-4h30M-9 2h8M3 2h7"/></g>;
  if(/question|message|chat|prompt/.test(value))return <g {...shape}><path d="M-15-10h30v18H0l-8 6V8h-7z"/><path d="M-8-3h16M-8 3h10"/></g>;
  if(/document|evidence|source/.test(value))return <g {...shape}><path d="M-10-13h14l7 7v20h-21zM4-13v7h7M-5 0h11M-5 6h11"/></g>;
  if(/history|older|conversation/.test(value))return <g {...shape}><circle r="12"/><path d="M0-8v9l7 4"/></g>;
  if(/embedding|model|network/.test(value))return <g {...shape}><path d="M-11-8L10 0-11 9M-11-8L10 0"/>{[[-11,-8],[-11,9],[10,0]].map(([x,y])=><circle key={`${x}-${y}`} cx={x} cy={y} r="3" fill={teal}/>)}</g>;
  if(/ids?|identifier|number|code/.test(value))return <g {...shape}><path d="M-5-12l-4 24M5-12L1 12M-13-4h27M-15 5h27"/></g>;
  if(/text|punctuation/.test(value))return <g {...shape}><rect x="-14" y="-11" width="28" height="22" rx="3"/><path d="M-8-4h16M-8 2h11"/></g>;
  return <g {...shape}><circle cx="-9" r="3" fill={teal}/><circle r="3" fill={coral}/><circle cx="9" r="3" fill={teal}/></g>;
}

/** Different diagrams share the same cited objects and measured sentence cues. */
/** `exit` fades this scene's stage at the cut, except objects in `keep` (continued by the next scene) and,
 * with `keepStage`, the diagram frame the next scene shares. */
export function ActionStage({scene,previous,time,shotIndex,exit=0,keep=new Set<string>(),keepStage=false}:{scene:Scene;previous?:Scene;time:number;shotIndex:number;exit?:number;keep?:Set<string>;keepStage?:boolean}){
  const choreography=scene.choreography!,plan=scene.actions!,form=plan.form,n=choreography.objects.length;
  const action=activeAction(scene,time),states=choreography.objects.map((_,i)=>objectState(choreography,i,time));
  const shot=scene.shots?.[shotIndex],previousPlan=previous?.actions,previousObjects=previous?.choreography?.objects;
  const labels=choreography.objects.map(o=>o.label);
  const position=(i:number)=>actionPosition(form,i,n,labels);
  const splitChildren=choreography.objects.map((_,i)=>i).filter(i=>i>0&&!/\b(tokenizer|parser|splitter)\b/i.test(labels[i]));
  const splitXs=splitChildren.map(i=>position(i)[0]);
  const visible=choreography.objects.map((_,i)=>states[i].visible&&!states[i].removed);
  // Motion waits for its spoken verb and runs from the earlier-introduced object to the later one.
  const moving=action&&action.started&&['flow','transform','fill'].includes(action.verb)&&action.targets.length>=2;
  const route=action?[...action.targets].sort((a,b)=>a-b):[];
  const from=moving?position(route[0]):[0,0],to=moving?position(route.at(-1)!):[0,0];
  const motionY=form==='flow'?355:form==='mapping'?245:Math.min(from[1],to[1])-95;
  return <>
    <g opacity={keepStage?1:1-exit}>
    {form==='flow'&&<g><rect x="90" y="87" width="1420" height="305" rx="44" fill="#eef7f4"/><path d="M155 355H1445" stroke="#a9d0c8" strokeWidth="9" strokeLinecap="round"/><path d="M1430 341l25 14-25 14" fill="none" stroke={teal} strokeWidth="7"/></g>}
    {form==='split'&&<g><rect x="620" y="36" width="360" height="154" rx="24" fill="#e9f4f0" stroke="#b6d9d2" strokeWidth="3"/>{splitChildren.length>0&&<><path d={`M800 190V233M${Math.min(...splitXs)} 233H${Math.max(...splitXs)}`} stroke={coral} strokeWidth="4" strokeDasharray="11 9"/>{splitChildren.map(i=>{const [x]=position(i);return <path key={i} d={`M${x} 233V260`} stroke={coral} strokeWidth="4" strokeDasharray="11 9"/>;})}</>}</g>}
    {form==='mapping'&&<g><rect x="170" y="92" width="520" height="318" rx="25" fill="#ecf4f8"/><rect x="910" y="92" width="520" height="318" rx="25" fill="#f0eefa"/><path d="M705 245H885" stroke={coral} strokeWidth="6" strokeDasharray="13 10" strokeLinecap="round"/></g>}
    {form==='compare'&&<g><rect x="65" y="45" width="715" height="385" rx="28" fill="#e9f4f0"/><rect x="820" y="45" width="715" height="385" rx="28" fill="#fff0e7"/><path d="M800 65V420" stroke="#c5d7d5" strokeWidth="4" strokeDasharray="12 10"/></g>}
    {form==='window'&&<g><rect x="65" y="48" width="1470" height="385" rx="28" fill="#ecf7f3" stroke={teal} strokeWidth="4"/><rect x="66" y="48" width="1468" height="72" rx="28" fill="#d2eae3"/><text x="105" y="95" fontSize="25" fill={teal} fontWeight="700">INFORMATION AVAILABLE IN THIS REQUEST</text><rect x="130" y="380" width="1340" height="17" rx="8" fill="#d0e1dc"/><rect x="130" y="380" width={1340*visible.filter(Boolean).length/Math.max(1,n)} height="17" rx="8" fill={teal}/></g>}
    {form==='network'&&<g>{choreography.objects.map((_,i)=>{const [x,y]=position(i);return <path key={i} d={`M800 245L${x} ${y}`} stroke="#b7d8d1" strokeWidth="4"/>;})}<circle cx="800" cy="245" r="53" fill="#d9efea" stroke={teal} strokeWidth="4"/></g>}
    </g>
    <g opacity={1-exit}>
    {choreography.steps.filter(step=>step.action==='connect'&&step.start<=time).map((step,i)=>{
      const [a,b]=step.targets,[ax,ay]=position(a),[bx,by]=position(b),p=cueProgress(time,step.start,step.end);
      const arc=Math.min(ay,by)-90;
      return <g key={`connection-${i}`}><path d={`M${ax} ${ay-75} Q${(ax+bx)/2} ${arc-55} ${bx} ${by-75}`} fill="none" stroke={coral} strokeWidth="5" opacity={.65*p} pathLength="1" strokeDasharray="1" strokeDashoffset={1-p}/></g>;
    })}
    </g>
    {moving&&<g opacity={(action.progress<1?1:0)*(1-exit)}><circle cx={from[0]+(to[0]-from[0])*action.progress} cy={motionY} r="16" fill={coral}/><circle cx={from[0]+(to[0]-from[0])*action.progress} cy={motionY} r="27" fill="none" stroke={coral} strokeWidth="2" opacity=".4"/></g>}
    {choreography.objects.map((object,i)=>{
      const state=states[i],oldIndex=previousObjects?.findIndex(o=>o.label.toLowerCase()===object.label.toLowerCase())??-1;
      const oldState=previous?.choreography&&oldIndex>=0?objectState(previous.choreography,oldIndex,previous.duration):null;
      const carried=!!oldState?.visible&&!oldState.removed&&!!previousPlan;
      if(!state.visible&&!carried)return null;
      const [x,y]=position(i),[oldX,oldY]=carried?actionPosition(previousPlan!.form,oldIndex,previousObjects!.length,previousObjects!.map(o=>o.label)):[x,y];
      const blend=easeInOut(time/.7),arrived=carried?1:state.entrance;
      const leaving=keep.has(object.label.toLowerCase())?0:exit;
      const pulse=mentionPulse(mentionTimes(scene,object.label),time,object.at??0);
      const focused=shot?.mode!=='wide'&&shot?.focus===i;
      const dimmed=shot?.mode==='detail'&&shot.focus!==null&&!focused;
      const opacity=arrived*(1-state.removed)*(dimmed?.75:1)*(1-leaving);
      const size=(form==='split'?165:form==='window'?190:form==='mapping'?220:form==='compare'?180:205)*objectScale(n);
      const fit=fitLabel(object.label,size-30,form==='flow'?27:24,16);
      const nodeY=y+(1-arrived)*42-state.removed*100+idleOffset(time,i,state.active)*(1-leaving);
      const scale=(focused?1.07:1)*(1+.08*pulse),lit=focused||pulse>.05;
      return <g key={`${i}-${object.label}`} transform={`translate(${oldX+(x-oldX)*blend} ${oldY+(nodeY-oldY)*blend}) scale(${scale})`} opacity={opacity}>
        {focused&&<rect x={-size/2-10} y="-65" width={size+20} height="135" rx="23" fill="none" stroke={coral} strokeWidth="3" strokeDasharray="10 7"/>}
        {pulse>0&&<rect x={-size/2-6-10*pulse} y={-61-10*pulse} width={size+12+20*pulse} height={128+20*pulse} rx="26" fill="none" stroke={coral} strokeWidth="3" opacity={.55*pulse}/>}
        <rect x={-size/2} y="-55" width={size} height="116" rx={form==='split'?12:20} fill={colors[i%colors.length]} stroke={lit?coral:teal} strokeWidth={lit?4:2.5}/>
        <g transform={`translate(${-size/2+30} -27) scale(1.45)`}><MiniGlyph label={object.label}/></g>
        {fit.lines.map((line,k)=><text key={k} x="0" y={fit.lines.length===1?24:14+k*(fit.fontSize+3)} textAnchor="middle" fontSize={fit.fontSize} fill={ink} fontWeight="700">{line}</text>)}
      </g>;
    })}
    <text x="800" y="475" textAnchor="middle" fontSize="18" fill="#68818a" opacity={keepStage?1:1-exit}>Illustrative diagram; spacing and movement are not model measurements</text>
  </>;
}
