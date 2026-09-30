import {DirectedDemonstration} from './DirectedDemonstration';
import {IllustratedStory} from './IllustratedStory';
import {AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {Icon} from './VisualScene';
import {Diagram} from './Diagram';
import {EnvironmentArt} from './EnvironmentArt';
import {environmentFor, TRANSITION_SECONDS} from '../motion';
import {TeachingStage, stageLayout} from './TeachingStage';
import {sharedConcept} from '../animation';
import {ConceptMotion} from './ConceptMotion';
import {NeuralNetDiagram} from './NeuralNetDiagram';
import {CodeScene} from './CodeScene';
import {LessonCard} from './LessonCard';
import {palette,captionPhrases,sceneTransition} from '../presentation';
import {WorkedExample} from './WorkedExample';
import {StatCard} from './StatCard';
import {CodeDemonstration} from './CodeDemonstration';
import {TeachingDemo} from './TeachingDemo';
import {ContextWindow} from './ContextWindow';
import {isContextWindow} from '../context-window';

import {semanticMotion,semanticTransition} from '../semantic-motion';
import {SemanticDemonstration} from './SemanticDemonstration';

const clamp={extrapolateLeft:'clamp',extrapolateRight:'clamp'} as const;
export function MotionScene({scene,style,globalFrame,first,previous,next}:{scene:Scene;style?:VideoData['style'];globalFrame:number;first:boolean;previous?:Scene;next?:Scene}) {
  const frame=useCurrentFrame(); const {fps}=useVideoConfig(); const t=frame/fps;
  if(scene.choreography && !['intro','outro','budget'].includes(scene.choreography.layout))
    return <IllustratedStory scene={scene} style={style} previous={previous} first={first}/>;
  const {accent,base,panel,muted}=palette(style?.theme);
  const entrance=spring({frame,fps,config:{damping:24,stiffness:100}});
  const wipe=interpolate(frame,[0,fps*TRANSITION_SECONDS],[100,0],clamp);
  const mechanism=semanticMotion(scene);
  const teaching=!!scene.teaching&&!['explanation','python','sql'].includes(scene.teaching.component)&&!!scene.visual?.directed&&!scene.visual?.worked&&!['chart','stat_card','code','water_cycle'].includes(scene.visual?.kind??'');
  const environment=scene.choreography||mechanism||scene.demonstration||scene.visual?.worked||teaching?undefined:environmentFor(scene);
  const reverse=environment==='plant';
  const panorama=environment==='rain';
  const v=scene.visual!;
  const beat=captionPhrases(scene).find(b=>t>=b.start&&t<b.end);
  const items=v.items.length?v.items:[scene.body];
  const active=Math.max(0,items.reduce((a,_,i)=>t>=(v.revealAt?.[i]??i*2)?i:a,0));
  const stage=stageLayout(scene);
  const carry=scene.visualPlan?.carry?{label:scene.visualPlan.carry,icon:'network'}:t<1?sharedConcept(previous,scene):sharedConcept(scene,next);
  const expressive=v.items.length>=2 && ['process','relationship','components','comparison','timeline','quote','analogy'].includes(v.kind) && !!v.motion && v.motion!=='flow';
  const diagram=!!scene.choreography||!!mechanism||!!scene.demonstration||teaching||!!v.worked||!!stage||expressive||['cycle','timeline','components','process','relationship','chart','water_cycle','neural_net','code','stat_card'].includes(v.kind);
  const hero=!scene.choreography&&!mechanism&&!scene.demonstration&&!teaching&&!v.worked&&['title','takeaway'].includes(v.kind);
  const split=!!environment || !diagram;
  const tr = mechanism?semanticTransition(mechanism,previous?semanticMotion(previous):undefined):scene.visual?.transition ?? 'fade';
  const transition=tr==='continuous'?{opacity:1}:sceneTransition(tr,t/TRANSITION_SECONDS,first);
  return <AbsoluteFill style={{background:base,color:'#f4f3e9',fontFamily:'Segoe UI, Arial, sans-serif',overflow:'hidden',...transition}}>
    <AbsoluteFill style={{background:`radial-gradient(ellipse at ${68}% 38%, ${accent}19, transparent 65%)`}}/>
    <div style={{position:'absolute',width:950,height:950,border:`1px solid ${accent}16`,borderRadius:'50%',right:-170,top:-320,transform:'scale(1)'}}/>
    <div style={{position:'absolute',top:62,left:88,color:accent,fontSize:18,letterSpacing:5,fontWeight:600}}>{style?.brand??'VISUALFORGE / LEARN'}</div>
    {!hero&&<div style={{position:'absolute',left:reverse?1160:88,top:panorama?142:split?205:152,width:panorama?1710:reverse?670:split?650:1670,transform:`translateY(${(1-entrance)*35}px)`,opacity:entrance}}>
      <div style={{width:54,height:5,background:accent,marginBottom:28}}/>
      <h1 style={{fontSize:scene.headline.length>55?50:panorama?60:split?68:60,lineHeight:1.09,fontWeight:650,letterSpacing:-2.5,margin:0,overflowWrap:'anywhere'}}>{mechanism&&scene.visualPlan?scene.visualPlan.title:scene.headline}</h1>
      {(diagram||environment)&&<p style={{fontSize:28,lineHeight:1.5,color:muted,maxWidth:panorama?1600:split?580:1400,marginTop:30}}>{scene.body}</p>}
      {split && !panorama && <div style={{marginTop:42,display:'flex',gap:10}}>{items.map((_,i)=><div key={i} style={{height:4,width:i===active?76:24,background:i===active?accent:`${accent}33`}}/>)}</div>}
    </div>}
    {hero?<div style={{position:'absolute',left:100,right:100,top:195}}><LessonCard scene={scene} accent={accent} panel={panel} hero/></div>:environment ? <div style={{position:'absolute',left:reverse?0:panorama?330:720,top:panorama?305:135,width:panorama?1270:1190,height:panorama?590:735,transform:`scale(${1+t/Math.max(scene.duration,1)*.025})`}}><EnvironmentArt mode={environment} time={t} accent={accent}/></div>
      : diagram ? <div style={{position:'absolute',left:105,right:105,top:395,transform:`translateY(${mechanism?0:(1-entrance)*30}px)`}}>{scene.choreography ? <DirectedDemonstration scene={scene} accent={accent} previous={previous}/> : mechanism ? <SemanticDemonstration scene={scene} kind={mechanism} accent={accent} previous={previous}/> : scene.demonstration ? <CodeDemonstration scene={scene} accent={accent}/> : teaching ? <TeachingDemo scene={scene} accent={accent}/> : v.worked ? <WorkedExample scene={scene} accent={accent} panel={panel}/> : v.kind === 'neural_net' ? <NeuralNetDiagram scene={scene} accent={accent} panel={panel}/> : v.kind === 'code' ? <CodeScene scene={scene} accent={accent} panel={panel}/> : v.kind === 'stat_card' ? <StatCard scene={scene} accent={accent} panel={panel}/> : isContextWindow(scene)?<ContextWindow scene={scene} accent={accent}/>: stage?<TeachingStage scene={scene} accent={accent}/>:expressive?<ConceptMotion scene={scene} accent={accent}/>:<Diagram scene={scene} accent={accent} panel={`${accent}10`}/>}</div>
      : <div style={{position:'absolute',left:790,top:190,width:1010,height:620,display:'flex',alignItems:'center',justifyContent:'center'}}>
        {v.kind==='comparison'?items.map((item,i)=>{const r=interpolate(t,[v.revealAt?.[i]??i*.5,(v.revealAt?.[i]??i*.5)+.5],[0,1],clamp);return <div key={i} style={{flex:1,alignSelf:i%2?'flex-end':'flex-start',padding:36,opacity:r,transform:`translateY(${(1-r)*40}px)`,borderTop:`3px solid ${i? '#ffbd99':accent}`,background:`${accent}0a`,fontSize:32,lineHeight:1.4}}><div style={{color:i?'#ffbd99':accent,marginBottom:26}}><Icon kind={v.icons?.[i]??v.icon??'idea'} size={80}/></div>{item}</div>;})
          : <LessonCard scene={scene} accent={accent} panel={panel}/>}
      </div>}
    {carry && <div style={{position:'absolute',right:90,top:58,color:accent,fontSize:20,maxWidth:650,display:'flex',gap:14,alignItems:'center'}}><Icon kind={carry.icon} size={30}/>{carry.label}</div>}
    {beat && <div style={{position:'absolute',bottom:75,left:220,right:220,textAlign:'center',fontSize:29,lineHeight:1.4,color:'#e2eceb'}}><span style={{background:'#07151fc9',padding:'12px 24px',boxDecorationBreak:'clone',borderRadius:8}}>{beat.text}</span></div>}
    <div style={{position:'absolute',bottom:0,left:0,height:3,width:`${Math.min(100,t/scene.duration*100)}%`,background:accent,opacity:.5}}/>
  </AbsoluteFill>;
}
