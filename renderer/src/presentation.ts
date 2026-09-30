import type {Beat, Scene, WordTiming} from './types.ts';

export function palette(theme:string|undefined) {
  return theme==='sunset'?{accent:'#ffbd99',base:'#29202d',panel:'#352936',muted:'#dbcbda'}:
    theme==='forest'?{accent:'#bddd97',base:'#142b29',panel:'#203b34',muted:'#c2d6cb'}:
    {accent:'#8ee5db',base:'#102938',panel:'#193746',muted:'#c2d4df'};
}

/** Word times for a beat: measured when present, otherwise spread evenly across the sentence. */
export function beatWords(beat:Beat):WordTiming[] {
  if(beat.words?.length)return beat.words;
  const words=beat.text.trim().split(/\s+/),span=(beat.end-beat.start)/words.length;
  return words.map((text,i)=>({text,start:beat.start+span*i,end:beat.start+span*(i+1)}));
}

/** Caption phrases of at most 12 words; each switches when its first word is spoken. */
export function captionPhrases(scene:Scene) {
  const beats=scene.beats?.length?scene.beats:[{text:scene.narration,start:0,end:scene.duration}];
  return beats.flatMap(beat=>{
    const words=beatWords(beat);const chunks:WordTiming[][]=[];
    const size=Math.min(12,Math.ceil(words.length/Math.ceil(words.length/12)));
    for(let i=0;i<words.length;i+=size)chunks.push(words.slice(i,i+size));
    return chunks.map((chunk,i)=>({
      text:chunk.map(w=>w.text).join(' '),
      words:chunk,
      // The first phrase opens with the sentence so no caption gap precedes its first word.
      start:i?chunk[0].start:beat.start,
      end:i<chunks.length-1?chunks[i+1][0].start:beat.end,
    }));
  });
}

/** Index of the word being spoken: the last word that has started, held through the pause after it. */
export function activeWord(words:WordTiming[],t:number) {
  let active=-1;
  words.forEach((w,i)=>{if(t>=w.start)active=i;});
  return active;
}

/** Shared validation for measured word timing inside one sentence beat. */
export function validateBeatWords(beat:Beat,label:string) {
  if(beat.words===undefined)return;
  const tolerance=1e-6;
  const words=beat.words,expected=beat.text.trim().split(/\s+/);
  if(!Array.isArray(words)||words.length!==expected.length||
    (beat.wordTiming!==undefined&&!['model','estimated'].includes(beat.wordTiming))||
    words.some((w,i)=>w.text!==expected[i]||!Number.isFinite(w.start)||!Number.isFinite(w.end)||
      w.start<beat.start-tolerance||w.end>beat.end+tolerance||w.end<w.start||(i>0&&w.start<words[i-1].start)))
    throw new Error(`${label} has invalid word timing.`);
}

export function sceneTransition(kind:string|undefined,progress:number,first=false) {
  const p=Math.max(0,Math.min(1,progress));
  if(first)return {opacity:1};
  if(kind==='slide')return {transform:`translateX(${(1-p)*48}px)`,opacity:p};
  if(kind==='wipe')return {clipPath:`inset(0 ${(1-p)*100}% 0 0)`};
  if(kind==='zoom')return {transform:`scale(${.97+.03*p})`,opacity:p};
  return {opacity:p};
}
