"use strict";
const episodePanel=element('section',undefined,'episode-review');episodePanel.id='episode-review';
$('creator-result').insertBefore(episodePanel,$('script-review'));
let episodeKey='',storyStartUid=null,storyProjectId=null;
function renderEpisodeReview(){
  const p=state.project,report=p?.episode_review;episodePanel.hidden=!report;
  if(!report){episodeKey='';return;}
  const key=JSON.stringify([p.id,p.revision,report,p.visual_candidate,p.story_preview,!!state.busy,!!state.pending]);
  if(key===episodeKey)return;episodeKey=key;episodePanel.replaceChildren();
  episodePanel.append(element('h2','Review your episode'),element('p',`${report.scenes.length} scenes · ${report.warnings} review notes. ${report.measured?'Timing is measured.':'Timeline positions are estimates until all narration is recorded.'} ${report.notice}`,'helper'));
  if(storyProjectId!==p.id){storyProjectId=p.id;storyStartUid=null;}
  if(!p.long_video){
    const area=element('div',undefined,'story-preview');area.append(element('h3','Watch a continuous preview'));
    area.append(element('p','Play up to two minutes of complete scenes with their narration. Choose where to begin.','helper'));
    const controls=element('div',undefined,'story-preview-controls'),select=element('select');select.setAttribute('aria-label','Preview starting scene');
    for(const [index,row] of report.scenes.entries()){const option=element('option',`${index+1}. ${row.title}`);option.value=row.uid;select.append(option);}
    select.value=storyStartUid||p.story_preview?.start_uid||report.scenes[0]?.uid||'';select.onchange=()=>{storyStartUid=select.value;};
    const generate=element('button','Generate two-minute preview');generate.onclick=()=>guarded(async()=>{
      if(state.dirty||state.reviewDirty)throw new Error('Save your script edits before previewing the episode.');
      storyStartUid=select.value;await api(`/api/projects/${p.id}/task`,{revision:p.revision,action:'story_preview',uid:storyStartUid});state.busy=true;await poll();
    });controls.append(select,generate);area.append(controls);
    if(p.story_preview){const info=element('p',`${p.story_preview.scene_uids.length} consecutive scenes · ${Math.round(p.story_preview.seconds)} seconds`,'helper');const player=element('video');player.controls=true;player.preload='metadata';player.src=p.story_preview.url;player.setAttribute('aria-label','Continuous episode preview');area.append(info,player);}
    episodePanel.append(area);
  }
  const candidate=p.visual_candidate;
  if(candidate){
    const panel=element('div',undefined,'visual-candidate');panel.append(element('h3','Replacement visual — not applied yet'));
    const selected=report.scenes.find(s=>s.uid===candidate.uid);if(selected)panel.append(element('p',selected.title));
    const player=element('video');player.controls=true;player.preload='metadata';player.src=candidate.url;player.setAttribute('aria-label','Replacement visual preview');panel.append(player);
    for(const [label,action] of [['Accept replacement','accept-visual'],['Keep current visual','discard-visual']]){
      const button=element('button',label);button.onclick=()=>guarded(async()=>{
        if(state.dirty||state.reviewDirty)throw new Error('Save or discard script edits before deciding on this replacement.');
        await api(`/api/projects/${p.id}/${action}`,{revision:p.revision});await openProject(p.id);
      });panel.append(button);
    }episodePanel.append(panel);
  }
  const clock=seconds=>`${Math.floor(seconds/60)}:${String(Math.floor(seconds%60)).padStart(2,'0')}`;
  const timeline=element('div',undefined,'episode-timeline');
  for(const [index,row] of report.scenes.entries()){
    const card=element('details',undefined,'episode-scene');
    const summary=element('summary');
    if(row.thumbnail){const img=element('img');img.src=row.thumbnail;img.loading='lazy';img.alt=`Scene ${index+1}: ${row.title}`;summary.append(img);}
    else {const placeholder=element('span',String(index+1),'scene-placeholder');placeholder.setAttribute('aria-label','Thumbnail available after rendering this scene');summary.append(placeholder);}
    summary.append(element('strong',row.title),element('span',`${clock(row.start)} · ${Math.round(row.seconds)}s · ${row.form}${row.measured?'':' · estimated'}`));card.append(summary);
    card.append(element('p',row.narration));
    if(row.carry)card.append(element('p',`Shared concept: ${row.carry}`,'helper'));
    for(const warning of row.warnings)card.append(element('p',warning,'scene-warning'));
    if(row.shots?.length){
      const shots=element('details',undefined,'shot-list');shots.append(element('summary',`${row.shots.length} narration-timed shots`));
      for(const shot of row.shots){
        const line=element('div',undefined,'shot-row');line.append(element('p',`${shot.sentence+1}. ${shot.text}`));
        const action=row.actions?.find(item=>item.sentence===shot.sentence);
        if(action)line.firstChild.append(element('span',`Visual action: ${action.verb}`,'action-tag'));
        const select=element('select');select.setAttribute('aria-label',`Visual view for scene ${index+1}, sentence ${shot.sentence+1}`);
        for(const [value,label] of [['auto',`Automatic (${shot.mode})`],['wide','Full view'],['follow','Follow the action'],['detail','Close-up']]){const option=element('option',label);option.value=value;select.append(option);}
        select.value=shot.override;
        const apply=element('button','Apply view');apply.onclick=()=>guarded(async()=>{
          if(state.dirty||state.reviewDirty)throw new Error('Save your script edits before changing a shot.');
          await api(`/api/projects/${p.id}/shot`,{revision:p.revision,uid:row.uid,sentence:shot.sentence,mode:select.value});await openProject(p.id);
        });line.append(select,apply);shots.append(line);
      }card.append(shots);
    }
    const play=element('button',((p.video_url||p.draft_url)&&report.measured)||row.clip?'Play this scene':'Generate scene preview');play.onclick=()=>guarded(async()=>{
      if((p.video_url||p.draft_url)&&report.measured){const player=$('creator-player');player.currentTime=row.start;await player.play();player.scrollIntoView({behavior:'smooth',block:'center'});}
      else if(row.clip){const player=element('video');player.controls=true;player.src=row.clip;player.setAttribute('aria-label',row.title+' current scene preview');card.append(player);await player.play();}
      else{if(state.dirty||state.reviewDirty)throw new Error('Save your script edits before generating a scene preview.');await api(`/api/projects/${p.id}/task`,{revision:p.revision,action:p.long_video?'long_scene_motion':'motion',uid:row.uid});state.busy=true;await poll();}
    });card.append(play);
    for(const [label,instructions] of [['Show a worked example','Show a concrete worked example supported by this narration. Preserve every spoken word; do not invent numbers or add unsupported facts.'],['Simplify this diagram','Simplify the diagram. Use fewer source-grounded labels and focus on the main operation. Preserve narration.'],['Use a comparison','Use a comparison if the narration supports one. Otherwise show the relationship without inventing a contrast. Preserve narration.']]){
      const button=element('button',label);button.onclick=()=>guarded(async()=>{
        if(state.dirty||state.reviewDirty)throw new Error('Save your script edits before preparing a visual replacement.');
        await api(`/api/projects/${p.id}/task`,{revision:p.revision,action:'propose_visual',uid:row.uid,instructions});state.busy=true;await poll();
      });card.append(button);
    }timeline.append(card);
  }
  episodePanel.append(timeline);
  episodePanel.querySelectorAll('button').forEach(button=>button.disabled=state.busy||state.pending);
}
const beforeEpisodeRender=renderCreator;
renderCreator=function(){beforeEpisodeRender();renderEpisodeReview();};
