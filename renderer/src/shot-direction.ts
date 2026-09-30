import type {Scene} from './types.ts';
import {actionPosition} from './visual-actions.ts';

export function shotPosition(layout:string,index:number,count:number):[number,number]{
  if(layout==='workspace')return [300+(index%3)*500,215+Math.floor(index/3)*155];
  if(layout==='comparison')return [index%2?1120:480,155+Math.floor(index/2)*185];
  if(layout==='connections')return [800+Math.cos(-Math.PI/2+index*2*Math.PI/count)*520,225+Math.sin(-Math.PI/2+index*2*Math.PI/count)*145];
  return [count===2?480+index*640:225+index*(1150/Math.max(1,count-1)),225];
}

export function validateShots(scene:Scene){
  const shots=scene.shots;if(!shots)return;
  const beats=scene.beats,objects=scene.choreography?.objects;
  if(!beats||!objects||!shots.length||shots.length!==beats.length)throw new Error('Shots need complete measured narration');
  for(const [index,shot] of shots.entries()){
    if(shot.sentence!==index||shot.text!==beats[index].text||shot.start!==beats[index].start||shot.end!==beats[index].end||
       !['wide','follow','detail'].includes(shot.mode)||
       (shot.focus!==null&&(!Number.isInteger(shot.focus)||!objects[shot.focus]||objects[shot.focus].sentence>index))||
       shot.label!==(shot.focus===null?null:objects[shot.focus].label))throw new Error('Shot must match its spoken sentence and visual object');
  }
}

function framing(scene:Scene,mode:'wide'|'follow'|'detail',focus:number|null){
  if(mode==='wide'||focus===null)return {scale:1,x:0,y:0};
  const [fx,fy]=scene.actions?actionPosition(scene.actions.form,focus,scene.choreography!.objects.length,scene.choreography!.objects.map(o=>o.label)):shotPosition(scene.choreography!.layout,focus,scene.choreography!.objects.length);
  // Keep every illustrated object and its label inside the stage. A shot's
  // primary emphasis comes from its focused object; the camera adds motion.
  const scale=mode==='detail'?1.05:1.02;
  return {scale,x:Math.max(-35,Math.min(35,(800-fx)*.08+800*(1-scale))),
          y:Math.max(-20,Math.min(20,(225-fy)*.08+225*(1-scale)))};
}

const target=(scene:Scene,index:number)=>{const shot=scene.shots![index];return framing(scene,shot.mode,shot.focus);};

/**
 * Without authored shots the camera follows the choreography: a close-up while the narration
 * dwells on a single object, wide whenever several objects are in play.
 */
export function autoCamera(scene:Scene,time:number){
  const steps=scene.choreography?.steps.filter(s=>s.action==='focus'||s.action==='reveal')??[];
  const cues:{start:number;focus:number|null}[]=[];
  for(const s of steps){
    const cue={start:s.start,focus:s.action==='focus'&&s.targets.length===1?s.targets[0]:null};
    if(cues.length&&Math.abs(cues[cues.length-1].start-cue.start)<.05)cues[cues.length-1]=cue;else cues.push(cue);
  }
  let index=-1;
  for(let i=0;i<cues.length;i++)if(time>=cues[i].start)index=i;
  if(index<0)return {scale:1,x:0,y:0,index:0};
  const current=framing(scene,'detail',cues[index].focus),previous=index?framing(scene,'detail',cues[index-1].focus):{scale:1,x:0,y:0};
  const raw=Math.max(0,Math.min(1,(time-cues[index].start)/.8)),ease=raw<.5?2*raw*raw:1-(-2*raw+2)**2/2;
  return {scale:previous.scale+(current.scale-previous.scale)*ease,x:previous.x+(current.x-previous.x)*ease,y:previous.y+(current.y-previous.y)*ease,index:0};
}

export function cameraAt(scene:Scene,time:number){
  const shots=scene.shots;
  if(!shots?.length)return autoCamera(scene,time);
  let index=0;
  for(let i=1;i<shots.length;i++)if(time>=shots[i].start)index=i;
  const current=target(scene,index),previous=index?target(scene,index-1):current;
  const raw=Math.max(0,Math.min(1,(time-shots[index].start)/.65)),ease=1-(1-raw)**3;
  return {scale:previous.scale+(current.scale-previous.scale)*ease,
          x:previous.x+(current.x-previous.x)*ease,
          y:previous.y+(current.y-previous.y)*ease,index};
}
