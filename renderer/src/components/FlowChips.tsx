import {along, chipKind, type Point} from '../flow';

const ink='#173044';
const tones=['#fae6b1','#d7ece9','#f9d9ca','#e8e3f8'];

export const CHIPS=5,CHIP_GAP=.14,CHIP_TRAVEL=.95;

/**
 * A few items visibly move from one object to the next as the arrow is drawn, so a
 * narrated relationship ("converts X into Y") reads as something happening, not just a line.
 */
export function FlowChips({from,control,to,start,time,label,accent}:{from:Point;control:Point;to:Point;start:number;time:number;label:string;accent:string}){
  const kind=chipKind(label);
  return <g>
    {Array.from({length:CHIPS},(_,k)=>{
      const u=(time-start-k*CHIP_GAP)/CHIP_TRAVEL;
      if(u<=0||u>=1)return null;
      const [x,y]=along(from,control,to,u),fade=Math.sin(Math.PI*u);
      return <g key={k} transform={`translate(${x} ${y})`} opacity={fade}>
        {kind==='chip'?<rect x="-9" y="-13" width="18" height="26" rx="4" fill={tones[k%tones.length]} stroke={ink} strokeWidth="2.5"/>
          :kind==='page'?<path d="M-9-12h12l6 6v18h-18z" fill="#fff0dc" stroke={ink} strokeWidth="2.5" strokeLinejoin="round"/>
          :<circle r="8" fill={accent}/>}
      </g>;
    })}
  </g>;
}
