import type {Scene} from './types.ts';

export type SemanticMotion = 'meaning-space'|'encoding'|'dimensions'|'retrieval'|'rag'|'tokens'|'context'|'attention'|'generation'|'vector-database';
/** Choose a mechanism from the actual narration, never from the video title alone. */
export function semanticMotion(scene:Scene):SemanticMotion|undefined {
  if(scene.choreography)return;
  if(scene.demonstration||scene.visual?.worked||['code','chart','stat_card','water_cycle','neural_net'].includes(scene.visual?.kind??''))return;
  if(scene.visualPlan){
    const supported:SemanticMotion[]=['meaning-space','encoding','dimensions','retrieval','rag','tokens','context','attention','generation','vector-database'];
    return supported.find(kind=>kind===scene.visualPlan!.kind);
  }
  const text=scene.narration;
  if(/\b(retriev\w*|RAG)\b/i.test(text)&&/\b(context|LLM|language model|answer)\b/i.test(text))return 'rag';
  if(/\b(semantic search|keyword search|similarity search|closest matches|query vector)\b/i.test(text))return 'retrieval';
  if(/\b(dimensions?|dimensional)\b/i.test(text)&&/\b(embedding|vector)s?\b/i.test(text))return 'dimensions';
  if(/\b(embedding|vector)s?\b/i.test(text)&&/\b(close|closer|nearby|farther|distance|cluster|geometry|space|similar meanings|relationships between)\b/i.test(text))return 'meaning-space';
  if(/\bembeddings?\b/i.test(text)&&/\b(numerical|numbers|converts?|represented|representation|model|vector)\b/i.test(text))return 'encoding';
}

export function meaningGroups(scene:Scene){
  return [['cat','dog','lion'],['car','truck','vehicle'],['banana'],['king','queen'],['python','programming']]
    .map(group=>group.filter(term=>new RegExp(`\\b${term}\\b`,'i').test(scene.narration)))
    .filter(group=>group.length).slice(0,3).map(group=>group.join(' / '));
}

export function semanticProgress(scene:Scene,time:number,pattern:RegExp) {
  const matched=scene.beats?.filter(b=>pattern.test(b.text))??[];
  const beats=matched.length?matched:scene.beats??[];
  const start=beats[0]?.start??0,end=beats.at(-1)?.end??Math.min(scene.duration,4);
  return Math.max(0,Math.min(1,(time-start)/Math.max(.5,end-start)));
}

export function validateVisualPlan(scene:Scene){
  const plan=scene.visualPlan;if(!plan)return;
  const kinds=['authored','fallback','meaning-space','encoding','dimensions','retrieval','rag','tokens','context','attention','generation','vector-database'];
  if(!kinds.includes(plan.kind)||!['overview','detail'].includes(plan.view)||typeof plan.title!=='string'||plan.title.length>150||!Array.isArray(plan.objects)||!Array.isArray(plan.steps)||!Array.isArray(plan.at)||plan.at.length!==plan.steps.length||!scene.beats||scene.beats.length!==plan.steps.length)throw new Error('Invalid visual plan');
  for(const object of plan.objects)if(typeof object!=='string'||!scene.narration.toLowerCase().includes(object.toLowerCase()))throw new Error('Visual plan objects must come from narration');
  plan.steps.forEach((step,i)=>{if(step.sentence!==i||step.text!==scene.beats![i].text||plan.at[i]!==scene.beats![i].start)throw new Error('Visual plan must match measured narration');});
}

export function semanticTransition(current:SemanticMotion|undefined,previous:SemanticMotion|undefined){
  return current&&current===previous?'continuous':current==='dimensions'?'zoom':current==='rag'||current==='encoding'?'wipe':'fade';
}
