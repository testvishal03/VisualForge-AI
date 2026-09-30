import type {Environment} from '../motion';

/** Stylized explanatory illustration; all motion is deterministic and frame-driven. */
export function EnvironmentArt({mode, time, accent}: {mode:Environment; time:number; accent:string}) {
  const soil = mode === 'ground' || mode === 'plant';
  const rain = mode === 'rain';
  return <svg viewBox="0 0 1200 720" width="100%" height="100%" aria-label={`${mode} animated illustration`}>
    <defs>
      <linearGradient id="sea" x2="0" y2="1"><stop stopColor="#258da8"/><stop offset="1" stopColor="#123951"/></linearGradient>
      <linearGradient id="earth" x2="0" y2="1"><stop stopColor="#b58352"/><stop offset="1" stopColor="#3c3438"/></linearGradient>
      <radialGradient id="sun-glow"><stop stopColor="#fbc97b" stopOpacity=".3"/><stop offset="1" stopColor="#fbc97b" stopOpacity="0"/></radialGradient>
    </defs>
    <circle cx="880" cy="165" r="170" fill="url(#sun-glow)"/>
    <circle cx="880" cy="165" r="49" fill="#ffce88"/>
    <g stroke="#ffce88" strokeWidth="3" opacity=".6" transform={`rotate(${time*4} 880 165)`}>
      {Array.from({length:12},(_,i)=><path key={i} d="M880 95v-19" transform={`rotate(${i*30} 880 165)`}/>)}</g>
    <path d="M40 495 300 325 530 510 800 365 1170 515V690H40Z" fill="#2e5d64" opacity=".5"/>
    <path d="M40 535Q270 470 510 535T1170 535V690H40Z" fill={soil?'url(#earth)':'url(#sea)'}/>
    {soil ? <>
      <path d="M40 530Q270 468 510 530T1170 530" fill="none" stroke="#8bb993" strokeWidth="14"/>
      {[0,1,2].map(i=><path key={i} d={`M80 ${584+i*35}Q420 ${550+i*35} 1120 ${595+i*30}`} stroke="#d3ab80" strokeWidth="2" opacity=".25" fill="none"/>)}
      {mode==='ground' && <>{Array.from({length:20},(_,i)=>{const y=530+(time*32+i*17)%135;return <circle key={i} cx={150+i*48} cy={y} r="4" fill="#85d7f3" opacity={.7*(1-(y-530)/150)}/>;})}<path d="M130 519Q440 465 690 535T1100 535" stroke="#8bdef5" strokeWidth="6" fill="none" strokeDasharray="20 22" strokeDashoffset={-time*38}/></>}
    </> : Array.from({length:4},(_,i)=><path key={i} d={`M60 ${555+i*32} Q260 ${540+i*32+Math.sin(time+i)*9} 550 ${555+i*32}T1150 ${555+i*32}`} stroke="#98e3e5" strokeWidth="2" fill="none" opacity={.32-i*.05}/>)}
    {mode==='plant' && <g transform={`rotate(${Math.sin(time*.6)*.6} 595 525)`}>
      <path d="M595 545V280M595 390 500 330M595 440 700 370" stroke="#d2b78b" strokeWidth="16" fill="none"/>
      <path d="M595 535 550 610M590 560 650 632M572 580 510 602M615 590 690 610" fill="none" stroke="#c49e73" strokeWidth="7"/>
      {[[500,290],[605,230],[700,315],[545,365],[670,395]].map(([x,y],i)=><ellipse key={i} cx={x} cy={y} rx="80" ry="52" transform={`rotate(${i%2?25:-30} ${x} ${y})`} fill={i%2?'#7cb58f':'#438e7f'}/>)}
      {Array.from({length:8},(_,i)=><circle key={i} cx={590+Math.sin(i*3)*75} cy={510-(time*65+i*38)%260} r="5" fill={accent}/>)}</g>}
    {(mode==='clouds'||rain) && <g transform={`translate(${Math.sin(time*.16)*18} 0)`} fill={rain?'#8caec2':'#dbe9e8'}>
      <ellipse cx="520" cy="210" rx="240" ry="66"/><circle cx="435" cy="170" r="80"/><circle cx="555" cy="135" r="105"/><circle cx="670" cy="175" r="65"/>
      {mode==='clouds' && Array.from({length:16},(_,i)=><circle key={i} cx={365+(i%8)*43} cy={180+Math.floor(i/8)*35} r={5+Math.sin(time+i)*2} fill="#6a9eae" opacity=".5"/>)}</g>}
    {rain && <g stroke="#9adbf7" strokeWidth="4" strokeLinecap="round">{Array.from({length:28},(_,i)=>{const y=290+(time*145+i*39)%230;return <path key={i} d={`M${325+(i%14)*30} ${y}l-8 21`} opacity={.4+(i%3)*.2}/>;})}</g>}
    {(mode==='evaporation'||mode==='clouds'||mode==='plant') && <g fill={accent}>{Array.from({length:22},(_,i)=>{const p=(time*.13+i/22)%1;return <circle key={i} cx={(mode==='plant'?490:220)+(i%7)*56+Math.sin(p*7+i)*16} cy={510-p*270} r={3+p*4} opacity={Math.sin(p*Math.PI)*.7}/>;})}</g>}
    <g fill="#dbe9e8" fontFamily="Segoe UI, sans-serif" fontSize="20" letterSpacing="3">
      <text x="70" y="675">{mode==='ground'?'SURFACE / BELOW GROUND':mode==='plant'?'ROOTS / STEM / LEAVES':rain?'DROPLETS / PRECIPITATION':mode==='clouds'?'COOLING / CONDENSATION':'ENERGY / EVAPORATION'}</text>
    </g>
  </svg>;
}
