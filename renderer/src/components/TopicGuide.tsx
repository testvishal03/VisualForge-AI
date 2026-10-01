import {useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene} from '../types';
import {BRIDGE_HEADLINE_DELAY, BRIDGE_SECONDS, bridgedFrom, clamp01, easeInOut, easeOut, sceneSeconds, teaserWindow} from '../transitions';
import {fitLabel} from '../labels';

type Colors = {ink:string;muted:string;accent:string;card:string;line:string};
// A compact row in the strip under the caption, so it never covers the stage.
const CARD = {width:600, right:95, bottom:12, height:66};

/**
 * Where the viewer is in the lesson, and what comes next. The rail shows every topic
 * (done, current, upcoming); near the end of a scene an "Up next" card previews the
 * following topic, and at the cut that card grows toward the new headline.
 */
export function TopicGuide({scenes, index, colors}:{scenes:Scene[];index:number;colors:Colors}) {
  const frame = useCurrentFrame(), {fps} = useVideoConfig(), t = frame/fps;
  const scene = scenes[index], next = scenes[index + 1], previous = scenes[index - 1];
  if (scenes.length < 2) return null;
  // After this scene ends, the next scene's own guide (and its bridge) takes over.
  if (t >= sceneSeconds(scene, fps)) return null;
  const progress = clamp01(t/scene.duration);
  const teaser = teaserWindow(scene, next, fps);
  const bridged = bridgedFrom(previous, scene, fps, true) && t < BRIDGE_SECONDS;
  return <>
    <TopicRail count={scenes.length} index={index} progress={progress} colors={colors}/>
    {teaser && t >= teaser.start && <UpNext scene={next!} colors={colors} enter={easeOut((t - teaser.start)/.5)}/>}
    {bridged && <Bridge scene={scene} colors={colors} p={t/BRIDGE_SECONDS}/>}
  </>;
}

function TopicRail({count, index, progress, colors}:{count:number;index:number;progress:number;colors:Colors}) {
  // Beyond a dozen topics the segments would be too small to read; show one bar instead.
  const compact = count > 12;
  return <div style={{position:'absolute', top:46, right:95, display:'flex', alignItems:'center', gap:18, fontFamily:'Segoe UI, Arial, sans-serif'}}>
    <span style={{fontSize:17, letterSpacing:3, fontWeight:700, color:colors.accent}}>TOPIC {index + 1} / {count}</span>
    {compact
      ? <div style={{width:260, height:8, borderRadius:4, background:colors.line}}><div style={{width:`${(index + progress)/count*100}%`, height:'100%', borderRadius:4, background:colors.accent}}/></div>
      : <div style={{display:'flex', gap:7}}>{Array.from({length:count}, (_, i) =>
          <div key={i} style={{width:i === index ? 64 : 24, height:8, borderRadius:4, overflow:'hidden', background:i < index ? colors.accent : colors.line}}>
            {i === index && <div style={{width:`${progress*100}%`, height:'100%', background:colors.accent}}/>}
          </div>)}</div>}
  </div>;
}

function CardBody({scene, colors, fontSize}:{scene:Scene;colors:Colors;fontSize?:number}) {
  const fit = fitLabel(scene.headline, CARD.width - 200, fontSize ?? 26, 16);
  return <div style={{display:'flex', alignItems:'center', gap:18, height:'100%'}}>
    <div style={{display:'flex', alignItems:'center', gap:8, fontSize:15, letterSpacing:3, fontWeight:700, color:colors.accent, flex:'none'}}>
      UP NEXT <svg width="26" height="14" viewBox="0 0 26 14"><path d="M1 7h21M16 1l6 6-6 6" fill="none" stroke={colors.accent} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/></svg>
    </div>
    <div style={{fontSize:fit.fontSize, lineHeight:1.1, fontWeight:700, color:colors.ink}}>{fit.lines.map((line, i) => <div key={i}>{line}</div>)}</div>
  </div>;
}

const cardStyle = (colors:Colors) => ({position:'absolute' as const, width:CARD.width, height:CARD.height, padding:'0 26px', boxSizing:'border-box' as const, borderRadius:16,
  background:colors.card, border:`2px solid ${colors.accent}55`, boxShadow:'0 14px 34px #0b1d2a26', fontFamily:'Segoe UI, Arial, sans-serif'});

function UpNext({scene, colors, enter}:{scene:Scene;colors:Colors;enter:number}) {
  return <div style={{...cardStyle(colors), right:CARD.right, bottom:CARD.bottom, opacity:enter, transform:`translateX(${(1 - enter)*60}px)`}}>
    <CardBody scene={scene} colors={colors}/>
  </div>;
}

/**
 * The previous scene's card travels toward the headline and has fully dissolved by the
 * time the headline starts entering (BRIDGE_HEADLINE_DELAY), so the two never overlap.
 */
function Bridge({scene, colors, p}:{scene:Scene;colors:Colors;p:number}) {
  const e = easeInOut(p);
  const fromLeft = 1920 - CARD.right - CARD.width, fromTop = 1080 - CARD.bottom - CARD.height;
  const fade = BRIDGE_HEADLINE_DELAY/BRIDGE_SECONDS;
  return <div style={{...cardStyle(colors), left:fromLeft + (95 - fromLeft)*e, top:fromTop + (100 - fromTop)*e,
    transform:`scale(${1 + .35*e})`, transformOrigin:'top left', opacity:1 - easeOut((p - fade*.55)/(fade*.45))}}>
    <CardBody scene={scene} colors={colors}/>
  </div>;
}
