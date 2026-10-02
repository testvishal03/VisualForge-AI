import type {Scene} from './types.ts';
import {withinBeat} from './choreography.ts';

export type VisualActions={form:'flow'|'split'|'mapping'|'compare'|'window'|'network'|'grid'|'stack'|'focus';beats:{sentence:number;text:string;verb:'reveal'|'split'|'transform'|'evict'|'fill'|'compare'|'flow';targets:number[];start:number;end:number;at?:number}[]};

export function validateVisualActions(scene:Scene){
  const a=scene.actions;if(!a)return;
  const beats=scene.beats,objects=scene.choreography?.objects;
  if(!beats||!objects||!['flow','split','mapping','compare','window','network','grid','stack','focus'].includes(a.form)||a.beats.length!==beats.length)throw new Error('Visual actions need complete narration and objects');
  for(const [i,row] of a.beats.entries()){
    if(row.sentence!==i||row.text!==beats[i].text||row.start!==beats[i].start||row.end!==beats[i].end||(row.at!==undefined&&!withinBeat(row.at,beats[i]))||
      !['reveal','split','transform','evict','fill','compare','flow'].includes(row.verb)||!Array.isArray(row.targets)||
      row.targets.some(index=>!Number.isInteger(index)||!objects[index]||objects[index].sentence>i)||
      row.verb==='evict'&&!/\b(remove\w*|drop\w*|outside|omit\w*|exclud\w*)\b/i.test(row.text))throw new Error('Visual action must match its spoken sentence');
  }
}

export function actionPosition(form:VisualActions['form'],index:number,count:number,labels?:string[]):[number,number]{
  if(form==='window')return [count===2?475+index*650:250+index*(1100/Math.max(1,count-1)),245];
  if(form==='split'){
    if(index===0)return [800,110];
    const tools=labels?labels.map((label,i)=>i>0&&/\b(tokenizer|parser|splitter)\b/i.test(label)?i:-1).filter(i=>i>=0):[];
    if(tools.includes(index))return [1370,110];
    const categories=Array.from({length:count-1},(_,i)=>i+1).filter(i=>!tools.includes(i));
    const rank=categories.indexOf(index);
    return [categories.length===1?800:280+rank*(1040/Math.max(1,categories.length-1)),315];
  }
  if(form==='mapping')return [count===2?460+index*680:270+index*(1060/Math.max(1,count-1)),245];
  if(form==='compare')return [count===2?460+index*680:235+index*(1130/Math.max(1,count-1)),245];
  // Tiles in two columns: a list of examples.
  if(form==='grid'){const rows=Math.ceil(count/2),row=Math.floor(index/2),alone=index===count-1&&count%2===1;
    return [alone?800:index%2===0?520:1080,rows===1?245:150+row*(190/Math.max(1,rows-1))];}
  // Layers stacked top to bottom: the parts or levels of one thing.
  if(form==='stack')return [800,240+(index-(count-1)/2)*128];
  // One main concept on the left, its details listed on the right.
  if(form==='focus')return index===0?[450,245]:[1150,count===2?245:105+(index-1)*(280/Math.max(1,count-2))];
  if(form==='network')return [800+Math.cos(-Math.PI/2+index*2*Math.PI/count)*450,245+Math.sin(-Math.PI/2+index*2*Math.PI/count)*150];
  return [count===2?480+index*640:225+index*(1150/Math.max(1,count-1)),245];
}

export function activeAction(scene:Scene,time:number){
  const rows=scene.actions?.beats;if(!rows?.length)return null;
  let index=0;for(let i=1;i<rows.length;i++)if(time>=rows[i].start)index=i;
  const row=rows[index];
  // The motion plays from its spoken verb; the sentence still selects the row.
  const at=row.at??row.start;
  const progress=Math.max(0,Math.min(1,(time-at)/Math.max(.55,Math.min(1.2,(row.end-at)*.4))));
  return {...row,progress,started:time>=at};
}
