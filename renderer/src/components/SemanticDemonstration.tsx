import {useCurrentFrame,useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {semanticProgress,meaningGroups,type SemanticMotion} from '../semantic-motion';

/** Motion illustrates relationships; all invented geometry is explicitly schematic. */
export function SemanticDemonstration({scene,kind,accent,previous}:{scene:Scene;kind:SemanticMotion;accent:string;previous?:Scene}){
  const t=useCurrentFrame()/useVideoConfig().fps;
  const continuing=scene.visualPlan?.transition==='continue'&&previous?.visualPlan?.kind===kind;
  const p=continuing?1:semanticProgress(scene,t,/vector|embedding|retriev|search|dimension|close|context/i);
  const reveal=(n:number)=>Math.max(0,Math.min(1,(p-n)*3));
  const labels=Array.from(scene.narration.matchAll(/[“"]([^”"\n]{2,48})[”"]/g),m=>m[1]).slice(0,3);
  const ownGroups=meaningGroups(scene);
  const groups=ownGroups.length?ownGroups:continuing&&previous?meaningGroups(previous):[];
  const beat=Math.max(0,(scene.visualPlan?.at??[]).filter(at=>t>=at).length-1);
  const detail=scene.visualPlan?.view==='detail';
  const text=(x:number,y:number,label:string,size=26)=><text x={x} y={y} fill="#f4f3e9" fontSize={size} textAnchor="middle">{label}</text>;
  const particle=(x:number,y:number,r=8)=><circle cx={x} cy={y} r={r} fill={accent}/>;
  return <svg viewBox="0 0 1600 450" style={{width:'100%',height:455,overflow:'visible'}} role="img" aria-label={kind+' animated explanation'}>
    <text x="0" y="10" fill={accent} fontSize="18" letterSpacing="3">SCHEMATIC EXPLANATION · NOT MEASURED MODEL OUTPUT</text>
    {['tokens','context','attention','generation','vector-database'].includes(kind)&&<>
      {kind==='tokens'&&<>
        {text(235,145,labels[0]??'Input text',30)}
        <path d="M100 190H390 M480 130V310 M480 220H660" stroke={accent} strokeWidth="4"/>
        {text(480,370,'Tokenizer',27)}
        {[0,1,2,3].map(i=><g key={i} opacity={Math.max(.15,Math.min(1,p*4-i*.5))} transform={`translate(${760+i*190} 190)`}>
          <path d="M0 0H130V70H0Z" stroke={accent} fill={`${accent}12`} strokeWidth="2"/>{text(65,45,`piece ${i+1}`,23)}{text(65,140,`ID ${String.fromCharCode(65+i)}`,23)}
        </g>)}{text(800,430,'Symbolic segmentation; actual token boundaries and IDs depend on the tokenizer.',23)}
      </>}
      {kind==='context'&&<>
        <path d="M220 90V340H1280V90" stroke={accent} strokeWidth="4" fill="none"/>
        {['Instructions','History','Question','Retrieved text','Answer budget'].map((label,i)=><g key={label} opacity={i<=Math.floor(p*5)?1:.15}>
          <path d={`M${250+i*200} 135H${420+i*200}V${300-(i%2)*45}H${250+i*200}Z`} fill={`${accent}${i===beat%5?'88':'33'}`} stroke={accent}/>{text(335+i*200,380,label,22)}
        </g>)}{text(800,70,'Finite context capacity',29)}{text(800,430,'Schematic allocation, not a measured token count',23)}
      </>}
      {kind==='attention'&&<>
        {[0,1,2,3,4].map(i=><g key={i}>
          <path d={`M${200+beat%5*300} 305 Q800 ${30+i*24} ${200+i*300} 160`} fill="none" stroke={accent} strokeWidth={i===beat%5?5:2} opacity={.2+p*.6}/>
          <circle cx={200+i*300} cy="160" r="22" fill={accent}/>{text(200+i*300,110,`Token ${i+1}`,26)}
        </g>)}<circle cx={200+beat%5*300} cy="305" r="25" fill="#ffbd99"/>
        {text(800,400,'The current token uses relationships with other tokens',28)}{text(800,440,'Connections are illustrative, not measured attention weights.',22)}
      </>}
      {kind==='generation'&&<>
        <path d="M130 220H1450" stroke={accent} strokeOpacity=".25" strokeWidth="4"/>
        {[0,1,2,3,4,5].map(i=><g key={i} opacity={i<=Math.floor(p*6)?1:.12}>
          <circle cx={190+i*240} cy="220" r="35" fill={i===Math.min(5,Math.floor(p*6))?'#ffbd99':accent}/>{text(190+i*240,315,`Token ${i+1}`,25)}
        </g>)}{text(800,110,'Predict → append → use the updated sequence',32)}{text(800,420,'Schematic sequence; no model prediction or probability is claimed.',23)}
      </>}
      {kind==='vector-database'&&<>
        {[0,1,2].map(group=><g key={group}>
          <ellipse cx={420+group*380} cy="100" rx="115" ry="35" fill="none" stroke={accent} strokeWidth="2"/>
          <path d={`M${305+group*380} 100V300 Q${420+group*380} 370 ${535+group*380} 300V100`} fill="none" stroke={accent} strokeWidth="2"/>
          {Array.from({length:8},(_,i)=><circle key={i} cx={360+group*380+(i%3)*55} cy={160+Math.floor(i/3)*60} r={group===beat%3?10:6} fill={accent} opacity={.3+p*.7}/>)}
        </g>)}<path d={`M100 210H${360+Math.floor(p*2)*380}`} stroke="#ffbd99" strokeWidth="4"/>
        {text(800,420,'Organize stored vectors to narrow the search',29)}
      </>}
    </>}
    {kind==='meaning-space'&&<>
      {[0,1,2,3,4].map(i=><path key={i} d={`M${170+i*280} 55V360 M140 ${70+i*70}H1460`} stroke="#ffffff10"/>)}
      {[0,1,2].map(group=><g key={group}>
        <ellipse cx={360+group*440} cy={180+(group%2)*90} rx={155*p+30} ry={95*p+20} fill={`${accent}09`} stroke={accent} strokeOpacity={p*.4} strokeDasharray="6 10"/>
        {Array.from({length:7},(_,i)=>{const a=i*2.4;const x=(190+i*185)*(1-p)+(360+group*440+Math.cos(a)*95)*p;const y=(80+group*125)*(1-p)+(180+(group%2)*90+Math.sin(a)*55)*p;return <circle key={i} cx={x} cy={y} r={i===0?12:6} fill={group===1?'#ffbd99':accent} opacity={.5+i/14}/>;})}
        {text(360+group*440,385,groups[group]??`Group ${group+1}`,detail&&group===beat%3?33:26)}
      </g>)}
      {text(800,435,'Nearby points illustrate related representations; distances here are illustrative.',23)}
    </>}
    {kind==='encoding'&&<>
      {text(250,100,'Input text',28)}{text(250,205,labels[0]??'Text',38)}
      <path d="M420 210H1130" stroke={accent} strokeWidth="3" strokeOpacity=".3"/>
      <g transform={`translate(${470+Math.min(1,p*1.4)*620} 210)`}>{particle(0,0,11)}</g>
      <circle cx="800" cy="210" r="98" fill="#102938" stroke={accent} strokeWidth="3"/>
      {[0,1,2].map(i=><ellipse key={i} cx="800" cy="210" rx={30+i*22} ry="70" fill="none" stroke={accent} strokeOpacity=".25" transform={`rotate(${i*60+p*100} 800 210)`}/>)}
      {text(800,350,'Embedding model',28)}{text(1310,100,'Vector coordinates',28)}
      {Array.from({length:8},(_,i)=><g key={i} opacity={reveal(.2+i*.045)*(detail&&i!==beat%8?.4:1)}><line x1="1200" x2={1220+(i%3)*45} y1={140+i*26} y2={140+i*26} stroke={accent} strokeWidth="9"/>{text(1400,148+i*26,`v${i+1}`,22)}</g>)}
      {text(800,430,'One representation, many numerical coordinates',25)}
    </>}
    {kind==='dimensions'&&<>
      <g transform={`translate(410 235) scale(${1-p*.15})`}>
        <path d="M-170 110H230 M-170 110V-130" stroke="#ffffff88" strokeWidth="2"/>
        {Array.from({length:15},(_,i)=><circle key={i} cx={Math.sin(i*12)*160} cy={Math.cos(i*4)*85} r="7" fill={accent}/>)}
      </g>
      <path d="M690 220H870" stroke={accent} strokeWidth="3" strokeDasharray="8 10"/>
      {Array.from({length:16},(_,i)=><g key={i} opacity={.2+.8*p}><path d={`M${940+i*30} 100V350`} stroke={accent} strokeOpacity=".4"/>{particle(940+i*30,140+(i*71)%170,5)}</g>)}
      {text(410,390,'A 2D view is only a projection',27)}{text(1170,390,'The full vector has many coordinates',27)}
      {text(800,440,'Axes are not named meanings; information is distributed across coordinates.',23)}
    </>}
    {kind==='retrieval'&&<>
      {text(225,95,'Query',28)}{text(225,225,labels[0]??'Question',26)}
      <path d="M390 215H680" stroke={accent} strokeWidth="3"/>
      <circle cx="800" cy="215" r={35+p*130} fill="none" stroke={accent} strokeWidth="2" opacity={.6}/>
      {particle(800,215,14)}
      {Array.from({length:12},(_,i)=>{const x=800+Math.cos(i*2.4)*(55+i*12),y=215+Math.sin(i*2.4)*(45+i*9);return <g key={i}><circle cx={x} cy={y} r="7" fill={i<3?accent:'#fff'} opacity={i<3?1:.25}/>{i<3&&<path d={`M800 215L${x} ${y}`} stroke={accent} opacity={p}/>}</g>;})}
      <path d="M1020 215H1220" stroke={accent} strokeWidth="3" opacity={p}/>
      {[0,1,2].map(i=><g key={i} opacity={reveal(i*.15)}><path d={`M1270 ${135+i*75}H1500`} stroke={accent} strokeWidth={12-i*3}/>{text(1390,165+i*75,`Match ${i+1}`,21)}</g>)}
      {text(800,415,'Compare representations, then retrieve relevant matches',29)}
    </>}
    {kind==='rag'&&<>
      {[0,1,2,3].map(i=><g key={i} transform={`translate(${110+i*35} ${100+i*25})`}><path d="M0 0H115V160H0Z M20 35H95 M20 65H95 M20 95H80" fill="#102938" stroke={i===1?accent:'#ffffff55'} strokeWidth="3"/></g>)}
      <path d="M370 220H1410" fill="none" stroke={accent} strokeOpacity=".25" strokeWidth="4"/>
      <g transform={`translate(${380+p*600} 205)`}><path d="M0 0H90M0 16H65M0 32H80" stroke={accent} strokeWidth="6"/></g>
      <path d="M690 130V310 M680 130H705 M680 310H705" stroke={accent} fill="none" strokeWidth="3"/>
      <circle cx="1050" cy="220" r="78" fill="#102938" stroke={accent} strokeWidth="3"/>{text(1050,230,'LLM',36)}
      {[0,1,2].map(i=><line key={i} x1="1250" x2={1250+reveal(.45+i*.08)*(220-i*30)} y1={185+i*35} y2={185+i*35} stroke={accent} strokeWidth="8"/>)}
      {text(225,365,'Sources',26)}{text(680,365,'Retrieved context',26)}{text(1050,365,'Generate',26)}{text(1370,365,'Answer',26)}
    </>}
  </svg>;
}
