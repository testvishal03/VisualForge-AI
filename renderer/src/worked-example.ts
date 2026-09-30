import type {Scene} from './types.ts';

export function validateWorkedScene(scene:Scene) {
  const spec=scene.visual?.worked, data=scene.visual?.workedData;
  if (!spec) {if(data) throw new Error('Example data has no authored steps'); return;}
  const fail=()=>{throw new Error('Worked example requires matching measured tokens and narration cues');};
  if(typeof spec.input!=='string'||!spec.input.trim()||spec.input.length>80||typeof spec.label!=='string'||!spec.label.trim()||spec.label.length>40) fail();
  const beats=scene.beats;
  if(!beats?.length||beats.some((b,i)=>!Number.isFinite(b.start)||!Number.isFinite(b.end)||b.start<(i?beats[i-1].end:0)||b.end<=b.start||b.end>scene.duration)||beats[0].start!==0||Math.abs(beats.at(-1)!.end-scene.duration)>1/24000||beats.map(b=>b.text).join(' ').replace(/\s+/g,' ')!==scene.narration.replace(/\s+/g,' '))fail();
  if(!Array.isArray(spec.steps)||spec.steps.length<1||spec.steps.length>4||spec.steps.some((s,i)=>!['tokens','ids','process','generate'].includes(s.action)||!Number.isInteger(s.sentence)||s.sentence<0||s.sentence>=(beats?.length??0)||(i>0&&s.sentence<=spec.steps[i-1].sentence)))fail();
  if(!data||data.input!==spec.input||data.mode!=='raw_completion'||typeof data.model?.model!=='string')return fail();
  if(!Array.isArray(data.tokens)||data.tokens.length<1||data.tokens.length>24)return fail();
  const raw:number[]=[];
  for(const token of data.tokens){
    if(!token||!Number.isInteger(token.id)||token.id<0)return fail();
    if(typeof token.piece==='string')raw.push(...new TextEncoder().encode(token.piece));
    else if(Array.isArray(token.piece)&&token.piece.every(b=>Number.isInteger(b)&&b>=0&&b<=255))raw.push(...token.piece);
    else return fail();
  }
  const input=[...new TextEncoder().encode(spec.input)];
  if(raw.length!==input.length||raw.some((b,i)=>b!==input[i]))fail();
  if(typeof data.continuation!=='string'||data.continuation.length>600||!Array.isArray(data.generated_ids)||!data.generated_ids.length||data.generated_ids.length>20||data.generated_ids.some(i=>!Number.isInteger(i)||i<0)||!Array.isArray(data.prefixes)||data.prefixes.length!==data.generated_ids.length||data.prefixes.some(p=>typeof p!=='string'||p.length>600)||data.prefixes.at(-1)!==data.continuation)fail();
}

export function exampleStage(scene:Scene,time:number) {
  const steps=scene.visual!.worked!.steps;
  let index=-1;
  steps.forEach((s,i)=>{if(time>=scene.beats![s.sentence].start)index=i;});
  if(index<0)return {action:undefined,progress:0};
  const start=scene.beats![steps[index].sentence].start;
  const end=index+1<steps.length?scene.beats![steps[index+1].sentence].start:scene.duration;
  return {action:steps[index].action,progress:Math.max(0,Math.min(1,(time-start)/Math.max(.1,(end-start)*.7)))};
}
