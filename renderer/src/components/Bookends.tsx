import {AbsoluteFill, useCurrentFrame, useVideoConfig} from 'remotion';
import type {Scene, VideoData} from '../types';
import {palette} from '../presentation';
import {EXIT_SECONDS, clamp01, easeOut, isIllustrated, lightVideo} from '../transitions';
import {fitLabel} from '../labels';

type Look = {base:string;ink:string;muted:string;accent:string;panel:string;line:string};

/** Bookends match the stage they sit next to: the light board or the themed dark stage. */
function look(scene:Scene|undefined, theme?:string, light=false):Look {
  if (light || isIllustrated(scene)) return {base:'#fbfaf5', ink:'#173044', muted:'#54707b', accent:'#087e81', panel:'#ffffff', line:'#d7e3e0'};
  const p = palette(theme);
  return {base:p.base, ink:'#f4f3e9', muted:p.muted, accent:p.accent, panel:p.panel, line:`${p.accent}33`};
}

const MAX_TOPICS = 5;
const font = "'Segoe UI', Selawik, Arial, sans-serif";

/** A list of lesson topics, each entering in turn. `mark` draws a number or a check. */
function TopicList({titles, t, start, step, colors, mark}:{titles:string[];t:number;start:number;step:number;colors:Look;mark:'number'|'check'}) {
  const shown = titles.slice(0, MAX_TOPICS), more = titles.length - shown.length;
  return <div style={{display:'flex', flexDirection:'column', gap:16}}>
    {shown.map((title, i) => {
      const p = easeOut((t - start - i*step)/.4);
      const fit = fitLabel(title, 1100, 36, 24);
      return <div key={i} style={{display:'flex', alignItems:'center', gap:24, opacity:p, transform:`translateX(${(1-p)*-30}px)`}}>
        <div style={{width:46, height:46, borderRadius:23, flex:'none', display:'flex', alignItems:'center', justifyContent:'center',
          background:mark === 'check' ? colors.accent : 'transparent', border:`2px solid ${colors.accent}`, color:mark === 'check' ? colors.base : colors.accent, fontSize:21, fontWeight:700}}>
          {mark === 'check'
            ? <svg width="22" height="22" viewBox="0 0 22 22"><path d="M4 11.5l4.5 4.5L18 6.5" fill="none" stroke={colors.base} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"/></svg>
            : i + 1}
        </div>
        <div style={{fontSize:fit.fontSize, fontWeight:600, color:colors.ink, lineHeight:1.2}}>{fit.lines.join(' ')}</div>
      </div>;
    })}
    {more > 0 && <div style={{fontSize:24, color:colors.muted, paddingLeft:70, opacity:easeOut((t - start - shown.length*step)/.4)}}>and {more} more</div>}
  </div>;
}

/** Topics of the whole lesson: chapter titles for chapter videos, otherwise scene headlines. */
// The opening scene often repeats the video title; listing it as a topic would be redundant.
const agendaOf = (data:VideoData) => (data.style?.agenda?.length ? data.style.agenda : data.scenes.map(s => s.headline))
  .filter(topic => topic.trim().toLowerCase() !== data.title.trim().toLowerCase());

/** Opening title: brand, lesson title, and the topics this video covers. */
export function IntroScene({data}:{data:VideoData}) {
  const frame = useCurrentFrame(), {fps, durationInFrames} = useVideoConfig(), t = frame/fps, total = durationInFrames/fps;
  const colors = look(data.scenes[0], data.style?.theme, lightVideo(data.scenes));
  const exit = easeOut((t - (total - EXIT_SECONDS))/EXIT_SECONDS);
  const title = easeOut(t/.55), rule = easeOut((t - .25)/.6);
  const fit = fitLabel(data.title, 1500, 84, 52);
  const topics = agendaOf(data), agenda = topics.length > 1;
  return <AbsoluteFill style={{background:colors.base, fontFamily:font, color:colors.ink}}>
    <div style={{position:'absolute', inset:0, padding:'0 150px', display:'flex', flexDirection:'column', justifyContent:'center', opacity:1 - exit, transform:`translateY(${-exit*18}px)`}}>
      <div style={{fontSize:22, letterSpacing:6, fontWeight:700, color:colors.accent, opacity:title}}>{data.style?.brand ?? 'VISUALFORGE / LEARN'}</div>
      <div style={{fontSize:fit.fontSize, lineHeight:1.08, fontWeight:750, letterSpacing:-2, marginTop:22, opacity:title, transform:`translateY(${(1-title)*30}px)`}}>
        {fit.lines.map((line, i) => <div key={i}>{line}</div>)}
      </div>
      <div style={{width:`${rule*260}px`, height:6, borderRadius:3, background:colors.accent, margin:'34px 0 40px'}}/>
      {agenda && <>
        <div style={{fontSize:20, letterSpacing:5, fontWeight:700, color:colors.muted, marginBottom:22, opacity:easeOut((t - .6)/.4)}}>IN THIS VIDEO</div>
        <TopicList titles={topics} t={t} start={.75} step={.22} colors={colors} mark="number"/>
      </>}
    </div>
  </AbsoluteFill>;
}

/** Closing card: a recap of what was covered, then thanks and what comes next. */
export function OutroScene({data}:{data:VideoData}) {
  const frame = useCurrentFrame(), {fps} = useVideoConfig(), t = frame/fps;
  const colors = look(data.scenes.at(-1), data.style?.theme, lightVideo(data.scenes));
  const enter = easeOut(t/.4);
  // The recap holds for the first half, then yields to the sign-off.
  const recapOut = easeOut((t - 2.4)/.4), thanks = easeOut((t - 2.7)/.5), nextCard = easeOut((t - 3.2)/.5);
  const next = data.style?.nextTopic, topics = agendaOf(data), recap = topics.length > 1;
  return <AbsoluteFill style={{background:colors.base, fontFamily:font, color:colors.ink}}>
    {recap && recapOut < 1 && <div style={{position:'absolute', inset:0, padding:'0 150px', display:'flex', flexDirection:'column', justifyContent:'center', opacity:enter*(1 - recapOut), transform:`translateY(${-recapOut*20}px)`}}>
      <div style={{fontSize:22, letterSpacing:6, fontWeight:700, color:colors.accent, marginBottom:30}}>WHAT YOU LEARNED</div>
      <TopicList titles={topics} t={t} start={.2} step={.18} colors={colors} mark="check"/>
    </div>}
    <div style={{position:'absolute', inset:0, display:'flex', flexDirection:'column', alignItems:'center', justifyContent:'center', opacity:recap ? thanks : enter}}>
      <div style={{fontSize:84, fontWeight:750, color:colors.accent, letterSpacing:-2, transform:`translateY(${(1-thanks)*20}px)`}}>Thanks for watching</div>
      <div style={{fontSize:34, fontWeight:600, marginTop:18}}>{data.style?.brand ?? 'VISUALFORGE / LEARN'}</div>
      {next
        ? <div style={{marginTop:46, padding:'22px 36px', borderRadius:18, background:colors.panel, border:`2px solid ${colors.accent}55`, opacity:nextCard, transform:`translateY(${(1-nextCard)*24}px)`, textAlign:'center'}}>
            <div style={{fontSize:18, letterSpacing:4, fontWeight:700, color:colors.accent}}>UP NEXT IN THIS SERIES</div>
            <div style={{fontSize:38, fontWeight:700, marginTop:8}}>{next}</div>
          </div>
        : <div style={{fontSize:28, color:colors.muted, marginTop:30, opacity:nextCard}}>Subscribe for more</div>}
    </div>
    <div style={{position:'absolute', left:0, bottom:0, height:7, width:`${clamp01(t/5)*100}%`, background:colors.accent, opacity:.6}}/>
  </AbsoluteFill>;
}
