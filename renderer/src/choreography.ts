import type {Scene} from './types.ts';

export type Choreography = {
  layout:'sequence'|'workspace'|'comparison'|'connections'|'intro'|'outro'|'budget';
  /** `at` is when the label is spoken (minus a short lead); older props omit it. */
  objects:{label:string;sentence:number;at?:number}[];
  steps:{sentence:number;action:'reveal'|'focus'|'connect'|'remove';targets:number[];start:number;end:number}[];
  note:string;
};

export function validateChoreography(scene:Scene){
  const c=scene.choreography;if(!c)return;
  if(!['sequence','workspace','comparison','connections','intro','outro','budget'].includes(c.layout)||c.note!=='Illustrative diagram; not measured model output'||!Array.isArray(c.objects)||!c.objects.length||c.objects.length>6||!Array.isArray(c.steps)||!c.steps.length||c.steps.length>20)throw new Error('Invalid choreography');
  for(const o of c.objects)if(typeof o.label!=='string'||!o.label.length||o.label.length>36||!Number.isInteger(o.sentence)||!scene.beats?.[o.sentence]?.text.toLowerCase().includes(o.label.toLowerCase())||(o.at!==undefined&&!withinBeat(o.at,scene.beats[o.sentence])))throw new Error('Choreography object is not grounded');
  if(c.layout==='budget'){const values=c.objects.map(o=>/^[0-9,]+ tokens$/.test(o.label)?Number(o.label.split(' ')[0].replaceAll(',','')):NaN);if(values.length!==3||values.some(v=>!Number.isFinite(v)||v<=0)||values[1]+values[2]!==values[0])throw new Error('Invalid budget allocation');}
  let previous=-1;
  for(const s of c.steps){
    const b=scene.beats?.[s.sentence];
    if(!Number.isInteger(s.sentence)||s.sentence<previous||!b||!withinBeat(s.start,b)||s.end!==b.end||!['reveal','focus','connect','remove'].includes(s.action)||!Array.isArray(s.targets)||!s.targets.length||s.targets.some(i=>!Number.isInteger(i)||!c.objects[i]||c.objects[i].sentence>s.sentence))throw new Error('Choreography must match measured sentence cues');
    if(s.action==='connect'&&(s.targets.length!==2||!(/\b(convert\w*|become\w*|map\w*|connect\w*|pass\w*|flow\w*|lead\w*|produce\w*|turn\w*|link\w*)\b/i).test(b.text)))throw new Error('Unsupported connection');
    if(s.action==='remove'&&!(/\b(remove\w*|drop\w*|outside|omit\w*|exclud\w*)\b/i).test(b.text))throw new Error('Unsupported removal');
    previous=s.sentence;
  }
  c.objects.forEach((o,i)=>{if(!c.steps.some(s=>s.action==='reveal'&&s.sentence===o.sentence&&s.targets.includes(i)))throw new Error('Missing object introduction');});
}

/** A cue is its sentence start, or a point inside the sentence when its words were measured. */
export const withinBeat=(t:number,b:{start:number;end:number;words?:unknown[]})=>Number.isFinite(t)&&(Math.abs(t-b.start)<1/24000||(!!b.words?.length&&t>b.start&&t<b.end));

export const cueProgress=(t:number,start:number,end:number)=>Math.max(0,Math.min(1,(t-start)/Math.max(.12,Math.min(.7,(end-start)*.3))));
export function objectState(c:Choreography,index:number,t:number){
  const reveal=c.steps.find(s=>s.action==='reveal'&&s.targets.includes(index));
  const remove=c.steps.find(s=>s.action==='remove'&&s.targets.includes(index)&&s.start<=t);
  const focus=c.steps.filter(s=>s.action==='focus'&&s.start<=t).at(-1);
  const at=c.objects[index]?.at??reveal?.start??0;
  return {visible:!!reveal&&t>=at, entrance:reveal?cueProgress(t,at,reveal.end):0,
    removed:remove?cueProgress(t,remove.start,remove.end):0,active:!!focus?.targets.includes(index)};
}
