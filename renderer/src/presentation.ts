import type {Scene} from './types.ts';

export function palette(theme:string|undefined) {
  return theme==='sunset'?{accent:'#ffbd99',base:'#29202d',panel:'#352936',muted:'#dbcbda'}:
    theme==='forest'?{accent:'#bddd97',base:'#142b29',panel:'#203b34',muted:'#c2d6cb'}:
    {accent:'#8ee5db',base:'#102938',panel:'#193746',muted:'#c2d4df'};
}

/** Phrase pacing is estimated within measured sentence bounds, not word alignment. */
export function captionPhrases(scene:Scene) {
  const beats=scene.beats?.length?scene.beats:[{text:scene.narration,start:0,end:scene.duration}];
  return beats.flatMap(beat=>{
    const words=beat.text.trim().split(/\s+/);const chunks:string[][]=[];
    const size=Math.min(12,Math.ceil(words.length/Math.ceil(words.length/12)));
    for(let i=0;i<words.length;i+=size)chunks.push(words.slice(i,i+size));
    let consumed=0;
    return chunks.map(chunk=>{
      const start=beat.start+(beat.end-beat.start)*consumed/words.length;consumed+=chunk.length;
      return {text:chunk.join(' '),start,end:beat.start+(beat.end-beat.start)*consumed/words.length};
    });
  });
}

export function sceneTransition(kind:string|undefined,progress:number,first=false) {
  const p=Math.max(0,Math.min(1,progress));
  if(first)return {opacity:1};
  if(kind==='slide')return {transform:`translateX(${(1-p)*48}px)`,opacity:p};
  if(kind==='wipe')return {clipPath:`inset(0 ${(1-p)*100}% 0 0)`};
  if(kind==='zoom')return {transform:`scale(${.97+.03*p})`,opacity:p};
  return {opacity:p};
}
