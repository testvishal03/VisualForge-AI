import type {Scene} from './types.ts';

export type TeachingPlan={version:1;component:'explanation'|'embedding'|'vector_search'|'rag'|'python'|'sql';question:string;objective:string;takeaway:string;evidence:'source'|'illustrative'|'computed';steps:{sentence:number;action:'explain'|'encode'|'compare'|'retrieve'|'context'|'answer';label:string}[];at:number[];example?:{query:number[];points:{label:string;vector:number[];cosine:number}[];metric:'cosine';provenance:'illustrative'}};

export function validateTeaching(scene:Scene) {
  const plan=scene.teaching;
  if(!plan)return;
  const fail=()=>{throw new Error('Invalid source-linked teaching plan.');};
  if(plan.version!==1||!['explanation','embedding','vector_search','rag','python','sql'].includes(plan.component)||
    !['question','objective','takeaway'].every(key=>typeof plan[key as 'question']==='string'&&plan[key as 'question'].length>0)||
    !Array.isArray(plan.steps)||plan.steps.length<1||plan.steps.length>20||!Array.isArray(plan.at)||plan.at.length!==plan.steps.length)fail();
  let previous=-1;
  plan.steps.forEach((step,i)=>{
    const beat=scene.beats?.[step.sentence];
    if(!Number.isInteger(step.sentence)||step.sentence<=previous||!beat||typeof step.label!=='string'||step.label.length<1||step.label.length>60||!beat.text.toLowerCase().includes(step.label.toLowerCase())||
      !['explain','encode','compare','retrieve','context','answer'].includes(step.action)||!Number.isFinite(plan.at[i])||Math.abs(plan.at[i]-beat.start)>.001)fail();
    previous=step.sentence;
  });
  if(plan.takeaway!==scene.beats?.at(-1)?.text)fail();
  const toy=['embedding','vector_search'].includes(plan.component);
  if(plan.evidence!==(toy?'illustrative':['python','sql'].includes(plan.component)?'computed':'source'))fail();
  if(toy){
    const data=plan.example;
    if(!data||data.provenance!=='illustrative'||data.metric!=='cosine'||data.query.length!==2||data.query.some(x=>!Number.isFinite(x))||Math.hypot(...data.query)===0||data.points.length!==3)fail();
    data!.points.forEach(point=>{
      if(!['A','B','C'].includes(point.label)||point.vector.length!==2||point.vector.some(x=>!Number.isFinite(x)||x<0||x>1)||Math.hypot(...point.vector)===0)fail();
      const cosine=point.vector.reduce((sum,x,i)=>sum+x*data!.query[i],0)/(Math.hypot(...point.vector)*Math.hypot(...data!.query));
      if(!Number.isFinite(point.cosine)||Math.abs(point.cosine-cosine)>.00001)fail();
    });
  }else if(plan.example)fail();
  if(plan.component==='rag'){
    const retrieve=plan.steps.findIndex(s=>s.action==='retrieve'),answer=plan.steps.findIndex(s=>s.action==='answer');
    if(retrieve<0||answer<=retrieve)fail();
  }
}

export function teachingStage(plan:TeachingPlan,time:number){return plan.at.reduce((active,at,i)=>time>=at?i:active,0);}
