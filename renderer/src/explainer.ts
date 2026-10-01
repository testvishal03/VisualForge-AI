import type {Scene} from './types.ts';

/**
 * Reusable explainer animations chosen from the narration. `at` holds measured cue times
 * (seconds into the scene); text comes from the narration, short fixed headings, or an
 * example the narration quotes. Candidate bars are illustrative, never measured odds.
 */
export type Explainer =
  | {kind:'next_token';prompt:string;source:'narration'|'example';candidates:string[];probs?:number[];measured?:boolean;model?:string;at:{type?:number;guess?:number;repeat?:number};end:number}
  | {kind:'denoise';subject:string;named:boolean;at:{noise?:number;clean?:number};end:number}
  | {kind:'contrast';left:{title:string;verb:string};right:{title:string;verb:string};bins:string[];hoodie?:boolean;at:{left?:number;right?:number};end:number}
  | {kind:'caveats';cards:{key:'wrong'|'bias'|'editor'|'privacy';title:string}[];at:Record<string,number>;end:number}
  | {kind:'steps';steps:{key:'feed'|'patterns'|'prompt'|'step';title:string;detail:string}[];at:Record<string,number>;end:number}
  | {kind:'tokens';text:string;pieces:string[];ids:number[];model:string;at:{split?:number;ids?:number};end:number}
  | {kind:'embedding_map';points:{label:string;group:number}[];at:Record<string,number>;end:number}
  | {kind:'retrieval';stages:{key:RetrievalStage;title:string}[];at:Record<string,number>;end:number};

export type RetrievalStage='question'|'embedding'|'search'|'chunks'|'llm'|'answer';
const STAGE_KEYS=['question','embedding','search','chunks','llm','answer'];

export const SHAPES=['heart','star','sun','smile','moon','flower','tree','house','cat'];
const text=(v:unknown,limit:number)=>typeof v==='string'&&v.trim().length>0&&v.length<=limit&&!/[\x00-\x1f]/.test(v);

export function validateExplainer(scene:Scene){
  const e=scene.explainer;if(!e)return;
  const fail=()=>{throw new Error('Invalid explainer animation.');};
  if(!Number.isFinite(e.end)||e.end<0||e.end>scene.duration+1e-6)fail();
  for(const t of Object.values(e.at??{}))if(!Number.isFinite(t)||t<0||t>scene.duration)fail();
  if(e.kind==='next_token'){
    if(!text(e.prompt,80)||!['narration','example'].includes(e.source)||!Array.isArray(e.candidates)||e.candidates.length>3||e.candidates.some(c=>!text(c,20)))fail();
    // Measured odds must come with their model and match the candidates one to one, highest first.
    if(e.measured!==undefined&&(typeof e.measured!=='boolean'||e.measured&&(!text(e.model,60)||!Array.isArray(e.probs))))fail();
    if(e.probs!==undefined&&(!Array.isArray(e.probs)||e.probs.length!==e.candidates.length||e.probs.some((v,i)=>!Number.isFinite(v)||v<0||v>1||(i>0&&v>e.probs![i-1]+1e-9))))fail();
  }else if(e.kind==='denoise'){
    if(!SHAPES.includes(e.subject)||typeof e.named!=='boolean')fail();
  }else if(e.kind==='contrast'){
    if(![e.left,e.right].every(p=>p&&text(p.title,40)&&text(p.verb,20))||!Array.isArray(e.bins)||![0,2].includes(e.bins.length)||e.bins.some(b=>!text(b,20))||(e.hoodie!==undefined&&typeof e.hoodie!=='boolean'))fail();
  }else if(e.kind==='caveats'){
    if(!Array.isArray(e.cards)||e.cards.length<2||e.cards.length>4||e.cards.some(c=>!['wrong','bias','editor','privacy'].includes(c.key)||!text(c.title,30)))fail();
  }else if(e.kind==='steps'){
    if(!Array.isArray(e.steps)||e.steps.length<2||e.steps.length>4||e.steps.some(st=>!['feed','patterns','prompt','step'].includes(st.key)||!text(st.title,30)||!text(st.detail,80)))fail();
  }else if(e.kind==='tokens'){
    // Measured pieces must rebuild the narration's text exactly, one real ID per piece.
    if(!text(e.text,200)||!text(e.model,60)||!Array.isArray(e.pieces)||!Array.isArray(e.ids)||e.pieces.length<1||e.pieces.length>40||e.pieces.length!==e.ids.length||
      e.pieces.join('')!==e.text||e.ids.some(id=>!Number.isInteger(id)||id<0))fail();
  }else if(e.kind==='embedding_map'){
    if(!Array.isArray(e.points)||e.points.length<4||e.points.length>8||e.points.some(pt=>!text(pt.label,24)||!Number.isInteger(pt.group)||pt.group<0||pt.group>7))fail();
  }else if(e.kind==='retrieval'){
    if(!Array.isArray(e.stages)||e.stages.length<4||e.stages.length>6||e.stages.some(st=>!STAGE_KEYS.includes(st.key)||!text(st.title,30)))fail();
  }else fail();
}

/** 0 before a cue, rising to 1 over `seconds` after it. */
export const after=(t:number,cue:number|undefined,seconds=.6)=>cue===undefined?0:Math.max(0,Math.min(1,(t-cue)/seconds));

/** Deterministic per-cell noise that reshuffles every frame-step, so static visibly churns. */
export function noise(i:number,j:number,step:number){
  const x=Math.sin(i*127.1+j*311.7+step*74.7)*43758.5453;
  return x-Math.floor(x);
}

/** Whether a point in [-1,1]² lies inside the named shape (y grows downward). */
export function inside(shape:string,x:number,y:number){
  const r=Math.hypot(x,y),a=Math.atan2(y,x);
  switch(shape){
    case 'heart':{const X=x*1.25,Y=-(y*1.25)+.25;return (X*X+Y*Y-1)**3-X*X*Y**3<=0;}
    case 'star':return r<=.38+.45*Math.max(0,Math.cos(2.5*(a+Math.PI/2)))**3;
    case 'sun':return r<.5||(r<.92&&Math.cos(8*a)>.6);
    case 'smile':return (r<.85&&r>.7)||Math.hypot(x+.3,y+.25)<.12||Math.hypot(x-.3,y+.25)<.12||(r<.5&&r>.38&&y>.1);
    case 'moon':return r<.8&&Math.hypot(x-.35,y+.15)>.62;
    case 'flower':return r<.25||(r<.55+.3*Math.cos(5*a)&&r<.85)||(Math.abs(x)<.05&&y>0);
    case 'tree':return (y<.45&&Math.abs(x)<(y+.85)*.55&&y>-.85)||(Math.abs(x)<.12&&y>=.45&&y<.9);
    case 'house':return (Math.abs(x)<.6&&y>-.1&&y<.8)||(y<=-.1&&y>-.75&&Math.abs(x)<(y+.75)*1.1);
    case 'cat':return Math.hypot(x,y-.1)<.6||(y<-.2&&y>-.85&&Math.abs(Math.abs(x)-.4)<(y+.85)*.35);
    default:return r<.6;
  }
}

/** Wrap token chips into rows that fit `width`; returns x/y for each chip. */
export function chipRows(widths:number[],width:number,gap=10,row=96){
  let x=0,y=0;
  return widths.map(w=>{if(x>0&&x+w>width){x=0;y+=row;}const at={x,y};x+=w+gap;return at;});
}

/** Cluster centres for an illustrative map: groups spread across the plane, members around each centre. */
export function mapLayout(groups:number[]){
  const count=Math.max(...groups)+1,centres=Array.from({length:count},(_,g)=>{
    const a=-Math.PI/2+g*2*Math.PI/count;return count===1?[700,275]:[700+Math.cos(a)*380,275+Math.sin(a)*125];});
  const seen=new Map<number,number>();
  return groups.map(g=>{const k=seen.get(g)??0;seen.set(g,k+1);const a=k*2.4;return [centres[g][0]+(k?Math.cos(a)*85:0),centres[g][1]+(k?Math.sin(a)*38:0)] as [number,number];});
}
