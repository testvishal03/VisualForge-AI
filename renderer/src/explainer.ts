import type {Scene} from './types.ts';

/**
 * Reusable explainer animations chosen from the narration. `at` holds measured cue times
 * (seconds into the scene); text comes from the narration, short fixed headings, or an
 * example the narration quotes. Candidate bars are illustrative, never measured odds.
 */
export type Explainer =
  | {kind:'next_token';prompt:string;source:'narration'|'example';candidates:string[];at:{type?:number;guess?:number;repeat?:number};end:number}
  | {kind:'denoise';subject:string;named:boolean;at:{noise?:number;clean?:number};end:number}
  | {kind:'contrast';left:{title:string;verb:string};right:{title:string;verb:string};bins:string[];hoodie?:boolean;at:{left?:number;right?:number};end:number}
  | {kind:'caveats';cards:{key:'wrong'|'bias'|'editor'|'privacy';title:string}[];at:Record<string,number>;end:number}
  | {kind:'steps';steps:{key:'feed'|'patterns'|'prompt'|'step';title:string;detail:string}[];at:Record<string,number>;end:number};

export const SHAPES=['heart','star','sun','smile','moon','flower','tree','house','cat'];
const text=(v:unknown,limit:number)=>typeof v==='string'&&v.trim().length>0&&v.length<=limit&&!/[\x00-\x1f]/.test(v);

export function validateExplainer(scene:Scene){
  const e=scene.explainer;if(!e)return;
  const fail=()=>{throw new Error('Invalid explainer animation.');};
  if(!Number.isFinite(e.end)||e.end<0||e.end>scene.duration+1e-6)fail();
  for(const t of Object.values(e.at??{}))if(!Number.isFinite(t)||t<0||t>scene.duration)fail();
  if(e.kind==='next_token'){
    if(!text(e.prompt,80)||!['narration','example'].includes(e.source)||!Array.isArray(e.candidates)||e.candidates.length>3||e.candidates.some(c=>!text(c,20)))fail();
  }else if(e.kind==='denoise'){
    if(!SHAPES.includes(e.subject)||typeof e.named!=='boolean')fail();
  }else if(e.kind==='contrast'){
    if(![e.left,e.right].every(p=>p&&text(p.title,40)&&text(p.verb,20))||!Array.isArray(e.bins)||![0,2].includes(e.bins.length)||e.bins.some(b=>!text(b,20))||(e.hoodie!==undefined&&typeof e.hoodie!=='boolean'))fail();
  }else if(e.kind==='caveats'){
    if(!Array.isArray(e.cards)||e.cards.length<2||e.cards.length>4||e.cards.some(c=>!['wrong','bias','editor','privacy'].includes(c.key)||!text(c.title,30)))fail();
  }else if(e.kind==='steps'){
    if(!Array.isArray(e.steps)||e.steps.length<2||e.steps.length>4||e.steps.some(st=>!['feed','patterns','prompt','step'].includes(st.key)||!text(st.title,30)||!text(st.detail,80)))fail();
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
