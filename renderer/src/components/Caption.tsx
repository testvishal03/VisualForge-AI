import type {CSSProperties} from 'react';
import {activeWord, captionPhrases} from '../presentation';
import type {Scene} from '../types';

/** The current caption phrase; the word being spoken is emphasized at its measured start. */
export function Caption({scene,t,highlight,style,boxStyle}:{scene:Scene;t:number;highlight:string;style:CSSProperties;boxStyle:CSSProperties}) {
  const phrase=captionPhrases(scene).find(p=>t>=p.start&&t<p.end);
  if(!phrase)return null;
  const active=activeWord(phrase.words,t);
  return <div style={style}><span style={{...boxStyle,boxDecorationBreak:'clone'}}>
    {phrase.words.map((word,i)=><span key={i} style={{color:i===active?highlight:undefined,opacity:i<=active?1:.72}}>{i?' ':''}{word.text}</span>)}
  </span></div>;
}
