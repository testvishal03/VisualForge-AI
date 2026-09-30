"use strict";
let creatorMode='prompt';
const progressByJob=new Map();
const creatorDraftKey='visualforge.creationDraft';
function rememberCreator(){
  try{localStorage.setItem(creatorDraftKey,JSON.stringify({mode:creatorMode,prompt:$('studio-topic').value,script:$('studio-script').value,title:$('studio-title').value,profile:$('studio-profile').value}));}catch{}
}
function updateCreatorInput(){
  const script=creatorMode==='script',text=$('studio-script').value.trim(),words=text?text.split(/\s+/).length:0;
  $('studio-prompt-group').hidden=script;$('studio-script-group').hidden=!script;
  document.querySelectorAll('.mode-tab').forEach(b=>{const active=b.dataset.mode===creatorMode;b.classList.toggle('active',active);b.setAttribute('aria-pressed',String(active));});
  $('prompt-char-count').textContent=$('studio-topic').value.length;
  $('script-stats').textContent=`${words.toLocaleString()} words | Duration follows your narration`;
  $('auto-length-note').textContent=script?(words?`About ${Math.max(1,Math.round(words/135*60))} seconds of speech, plus pauses. Final length is measured from the narration.`:'Video length follows your script. Paste it to see an estimate.'):'AI drafts to the scope of your idea. Final duration follows the script and recorded narration.';
  rememberCreator();
}
function newCreator(){
  if(state.busy||state.pending)return;
  if((state.dirty||state.reviewDirty)&&!confirm('Discard unsaved video edits?'))return;
  state.reviewDirty=false;
  state.project=null;state.doc=null;state.dirty=false;state.selected=null;
  localStorage.removeItem('visualforge.active');document.body.classList.add('simple-mode');
  creatorMode='prompt';
  for(const id of ['studio-topic','studio-script','studio-title'])$(id).value='';
  updateCreatorInput();
  workspaceOptions();renderWorkspace();renderCreator();window.scrollTo({top:0,behavior:'smooth'});$('studio-topic').focus();
}
function renderCreator(){
  const project=state.project,live=state.job?.project===project?.id?state.job:null;
  const job=live&&live.status!=='idle'?live:project?.last_job;
  const running=job?.status==='running',previewing=running&&['visual_preview','propose_visual','motion','long_scene_motion','story_preview'].includes(job?.action),currentUrl=!state.dirty&&(project?.video_url||project?.draft_url);
  const previous=!currentUrl&&!running&&project?.previous_export_url;
  const url=currentUrl||previous;
  $('creator-result').hidden=!project;
  $('creator-current').hidden=!(state.job?.status==='running'&&state.job.project!==project?.id);
  renderScriptReview(project,running);
  renderPlaylistSuggestion();
  if(!project)return;
  $('creator-finish').hidden=!currentUrl||!!project.accepted;
  $('creator-revise').hidden=!url;
  $('creator-player-shell').hidden=previewing||!url&&!running;
  $('creator-title').textContent=state.doc?.title||project.topic;
  const measured=project.duration?.measured_seconds??project.long_duration?.measured_seconds;
  const runtime=Math.round(measured||0);
  const planned=project.source?.length_plan;
  const target=live?.target_minutes||planned?.minutes||(project.source?.mode==='script'?project.source.minutes:null);
  $('creator-duration').textContent=measured?`${Math.floor(runtime/60)}:${String(runtime%60).padStart(2,'0')} · ${currentUrl?(project.video_url?'1080p video':'720p video'):'measured narration and pauses'}`:target?`${project.source?.mode==='script'?'Estimated from your script: about':'AI planned about'} ${Number(target).toFixed(1)} minutes${planned?.reason?' · '+planned.reason:''}`:'Length will follow your content and narration.';
  $('creator-eyebrow').textContent=previewing?'CREATING A VISUAL PREVIEW':project.accepted?'FINISHED':project.source?.approval_required&&!url&&!running?'REVIEW YOUR LESSON':previous?'PREVIOUS EXPORT - GENERATE TO APPLY UPDATES':url?'100% COMPLETE - READY TO WATCH':running?'CREATING YOUR VIDEO':'YOUR VIDEO';
  $('creator-progress').hidden=!running;
  if(running){
    const progress=generationProgress(job,progressByJob.get(job.id)||0);progressByJob.set(job.id,progress.pct);
    $('creator-phase').textContent=state.offline?'Reconnecting to the local engine':previewing?'Preparing your visual preview':progress.label;
    $('creator-detail').textContent=state.offline?'Your job may still be running. Keep the local server open.':'You can return to this page. Keep the laptop awake and the local engine running.';
    $('creator-percent').textContent=`${progress.pct}%`;$('creator-fill').style.width=`${progress.pct}%`;
    $('creator-meter').setAttribute('aria-valuenow',progress.pct);
    $('creator-elapsed').textContent=`Estimated progress · ${Math.floor((job.elapsed_seconds||0)/60)}m ${(job.elapsed_seconds||0)%60}s elapsed`;
    [...$('creator-stages').children].forEach((e,i)=>{e.classList.toggle('done',i<progress.stage);e.classList.toggle('current',i===progress.stage);});
  }
  const player=$('creator-player');player.hidden=!url;
  $('creator-placeholder').hidden=!!url;
  if(url&&player.getAttribute('src')!==url)player.src=url;
  if(!url&&player.hasAttribute('src')){player.pause();player.removeAttribute('src');player.load();}
  const failed=job?.status==='failed',cancelled=job?.status==='cancelled';
  $('creator-placeholder-title').textContent=running?'Your video is taking shape':failed?'Let’s get your video finished':cancelled?'Generation cancelled':'Ready for the next step';
  $('creator-placeholder-note').textContent=running?'The finished video will appear here automatically.':cancelled?'Completed stages are saved. Retry to continue.':project.source?.approval_required?'Review the script above, then approve it to generate your video.':'Generate the video, or open the editor to adjust your content.';
  $('creator-error').hidden=!failed;$('creator-error-detail').textContent=failed?job.error||'Generation failed. Retry or open the editor to review your content.':'';
  $('creator-download').hidden=!url;if(url)$('creator-download').href=url;
  $('creator-retry').hidden=running||!!currentUrl||!!(project.source?.approval_required&&!(failed&&job?.action==='auto_generate')&&(!project.long_video&&project.document||project.chapter_details?.length&&project.chapter_details.every(c=>c.script)));
  $('creator-retry').textContent=project.source?.approval_required&&failed&&job?.action==='auto_generate'?'Retry script preparation':previous?'Generate updated video':failed||cancelled?'Retry generation':'Generate video';
  $('creator-edit').hidden=!document.body.classList.contains('simple-mode');
  $('creator-back').hidden=document.body.classList.contains('simple-mode');
  for(const id of ['creator-new','creator-edit','creator-retry','creator-finish','creator-revise','creator-delete','creator-settings','visual-preview-btn'])$(id).disabled=state.busy||state.pending;
  $('creator-cancel').disabled=!!state.cancelling;
  $('creator-cancel').textContent=state.cancelling?'Cancelling…':'Cancel generation';
}
const creatorOriginalRender=renderWorkspace;
renderWorkspace=function(){creatorOriginalRender();renderCreator();};
const creatorOriginalLock=lockControls;
lockControls=function(){creatorOriginalLock();document.querySelectorAll('#welcome input,#welcome textarea,#welcome select,#welcome button,#script-review button,#script-review textarea').forEach(e=>e.disabled=state.busy||state.pending);};
document.querySelectorAll('.mode-tab').forEach(b=>b.onclick=()=>{creatorMode=b.dataset.mode;updateCreatorInput();});
document.querySelectorAll('.prompt-chip').forEach(b=>b.onclick=()=>{$('studio-topic').value=b.dataset.prompt;updateCreatorInput();$('studio-topic').focus();});
for(const id of ['studio-topic','studio-script','studio-title','studio-profile'])$(id).oninput=updateCreatorInput;
$('studio-script-file').onchange=async event=>{
  const file=event.target.files[0];if(!file)return;
  if(file.size>1500000){message('Upload up to 1.5 MB of script text at a time. Long scripts become chapters automatically.');return;}
  try{const text=await file.text();$('studio-script').value=text;updateCreatorInput();}catch(error){message(error.message);}
};
$('studio-generate-btn').onclick=()=>guarded(async()=>{
  const text=$(creatorMode==='script'?'studio-script':'studio-topic').value.trim();
  if(!text){message('Enter your idea or paste a script first.');return;}
  const words=text.split(/\s+/).length;

  const project=await api('/api/projects',{mode:creatorMode,text,title:$('studio-title').value.trim()||undefined,profile:$('studio-profile').value,workspace_id:$('studio-workspace').value||undefined,automatic:true,approval_required:true});
  state.busy=true;state.cancelling=false;await openProject(project.id);await poll();
});
for(const id of ['new-project','creator-new'])$(id).onclick=newCreator;
$('creator-edit').onclick=()=>{document.body.classList.remove('simple-mode');renderCreator();};
$('creator-back').onclick=()=>{document.body.classList.add('simple-mode');renderCreator();};
$('creator-cancel').onclick=async()=>{if(state.cancelling)return;state.cancelling=true;renderCreator();try{await api('/api/cancel',{});}catch(e){state.cancelling=false;message(e.message);}await poll();};
$('creator-retry').onclick=()=>guarded(async()=>{
  await save();
  const p=state.project;
  if(!p.source?.automatic&&p.long_video){document.body.classList.remove('simple-mode');renderCreator();message('Use the chapter editor to continue this existing chapter project.');return;}
  if(!p.source?.automatic&&p.document){state.project=await api(`/api/projects/${p.id}/approve`,{revision:p.revision});}
  await api(`/api/projects/${p.id}/task`,{revision:state.project.revision,action:p.source?.automatic?'auto_generate':p.document?(p.source?.profile==='final'?'render':'render_draft'):'generate'});
  state.busy=true;state.cancelling=false;await poll();
});
try{const draft=JSON.parse(localStorage.getItem(creatorDraftKey)||'null');if(draft){creatorMode=draft.mode==='script'?'script':'prompt';$('studio-topic').value=draft.prompt||'';$('studio-script').value=draft.script||'';$('studio-title').value=draft.title||'';$('studio-profile').value=draft.profile==='final'?'final':'draft';}}catch{}
updateCreatorInput();
lockControls();

$('creator-current').onclick=()=>guarded(()=>openProject(state.job.project));

function renderPlaylistSuggestion(){
  const w=state.spaces.find(w=>w.id===$('studio-workspace').value);
  $('playlist-suggestion').hidden=!w?.next_topic&&!w?.active_project;
  $('playlist-next-label').textContent=w?.active_project?'Your current video is still in review. Refine it before moving on.':w?.next_topic?`Next lesson: ${w.next_topic}`:'';
  $('playlist-use-next').textContent=w?.active_project?'Continue current video':'Use suggested topic';
}
$('studio-workspace').addEventListener('change',renderPlaylistSuggestion);
$('playlist-use-next').onclick=()=>guarded(async()=>{const w=state.spaces.find(w=>w.id===$('studio-workspace').value);if(w?.active_project){await openProject(w.active_project);return;}if(w?.next_topic){creatorMode='prompt';$('studio-topic').value=w.next_topic;updateCreatorInput();}});
let scriptReviewKey='';
function renderScriptReview(p,running){
  const rows=p?.long_video?(p.chapter_details||[]).filter(c=>c.script).map(c=>({id:c.id,title:c.title,script:c.script,visual:c.visual_goal})):p?.document?[{id:'single',title:p.document.title,script:p.document.scenes.map(s=>s.narration).join('\n\n'),visual:p.document.scenes.map(s=>s.headline+' ('+s.visual.kind+')').join(' / ')}]:[];
  const show=rows.length>0;
  $('script-review').hidden=!show;
  if(!show){scriptReviewKey='';return;}
  const words=rows.reduce((sum,r)=>sum+r.script.trim().split(/\s+/).length,0);
  $('script-review-summary').textContent=`${words.toLocaleString()} words | About ${(words/135).toFixed(1)} minutes of speech (estimate). ${(p.long_video?p.script_approved:p.storyboard_approved)?'Current script approved.':'Waiting for your approval.'}`;
  const key=p.id+':'+p.revision;
  if(key!==scriptReviewKey){
    $('script-review').open=!(p.video_url||p.draft_url||p.previous_export_url);
    const box=$('script-review-fields');box.replaceChildren();
    for(const row of rows){const label=element('label',row.title),input=element('textarea');input.rows=10;input.value=row.script;input.oninput=()=>{state.reviewDirty=true;$('creator-finish').disabled=true;};input.dataset.chapter=row.id;input.setAttribute('aria-label',row.title+' narration');label.append(input);box.append(label);}
    renderVisualPlan(p);
    scriptReviewKey=key;
  }
  const preview=p.style_url||(p.chapter_details||[]).find(c=>c.style_url)?.style_url;
  $('visual-preview-area').hidden=!preview;
  if(preview&&$('visual-preview-player').getAttribute('src')!==preview){$('visual-preview-player').src=preview;$('script-review').open=true;}
  if(!preview)$('visual-preview-player').removeAttribute('src');
  $('script-review').querySelectorAll('button,textarea,input').forEach(e=>e.disabled=!!running||state.busy||state.pending);
}
async function saveReviewedScript(){
  await save();
  let p=state.project;const fields=[...$('script-review-fields').querySelectorAll('textarea')];
  if(p.long_video){state.project=await api(`/api/projects/${p.id}/long-save`,{revision:p.revision,scripts:Object.fromEntries(fields.map(e=>[e.dataset.chapter,e.value]))});}
  else {
    // Preserve scene boundaries and authored visuals through the existing editor.
    const paragraphs=fields[0].value.trim().split(/\n\s*\n/);
    if(paragraphs.length!==p.document.scenes.length)throw new Error('Keep one paragraph per existing scene, or use Edit video to change scene structure.');
    const doc=structuredClone(p.document);doc.scenes.forEach((s,i)=>s.narration=paragraphs[i].trim());
    state.project=await api(`/api/projects/${p.id}/save`,{revision:p.revision,document:doc});state.doc=structuredClone(state.project.document);
  }
  state.dirty=false;state.reviewDirty=false;
}
$('script-save').onclick=()=>guarded(async()=>{await saveReviewedScript();await openProject(state.project.id);});
$('script-approve').onclick=()=>guarded(async()=>{
  await saveReviewedScript();let p=state.project;
  p=await api(`/api/projects/${p.id}/${p.long_video?'long-save':'approve'}`,{revision:p.revision,...(p.long_video?{approve_script:true}:{})});state.project=p;
  await api(`/api/projects/${p.id}/task`,{revision:p.revision,action:p.long_video?(p.source.profile==='draft'?'long_render_draft':'long_render'):(p.source.profile==='draft'?'render_draft':'render')});state.busy=true;await poll();
});
$('script-expand').onclick=()=>guarded(async()=>{await saveReviewedScript();const p=state.project;await api(`/api/projects/${p.id}/task`,{revision:p.revision,action:'expand_script'});state.busy=true;await poll();});

function renderVisualPlan(p){
  const box=$('visual-plan-list');box.replaceChildren();
  const plan=p.visual_plan;if(!plan){box.append(element('p','Prepare your script to see the visual plan.'));return;}
  for(const [i,row] of plan.scenes.entries()){
    const card=element('details',undefined,'visual-plan-row');card.append(element('summary',`${i+1}. ${row.title} - ${row.kind==='fallback'?'Review fallback':row.kind==='authored'?'Existing demonstration':row.kind.replaceAll('-',' ')}`));
    card.append(element('p',row.question),element('p',`Objects: ${(row.choreography?.objects.map(o=>o.label)||row.objects).join(', ')||'Source text'} | View: ${row.choreography?.layout||row.view} | Transition: ${row.transition}`,'helper'));
    if(row.carry)card.append(element('p',`Continue the example: ${row.carry}`,'helper'));
    for(const step of row.steps)card.append(element('p',`Sentence ${step.sentence+1}: ${step.action} - ${step.text}`));
    if(row.choreography)for(const step of row.choreography.steps)card.append(element('p',`At sentence ${step.sentence+1}: ${step.action} ${step.targets.map(i=>row.choreography.objects[i].label).join(' + ')}`,'helper'));
    const request=element('input');request.type='text';request.maxLength=1000;request.placeholder='For example: focus on the comparison';request.setAttribute('aria-label',`Visual revision for scene ${i+1}`);
    const revise=element('button','Change this visual');revise.type='button';revise.onclick=()=>guarded(async()=>{
      if(state.reviewDirty||state.dirty)throw new Error('Save your script edits before changing a visual.');
      const current=state.project;await api(`/api/projects/${current.id}/task`,{revision:current.revision,action:'propose_visual',uid:row.uid,instructions:request.value||'Use a clear demonstration with objects revealed at the matching narration sentence.'});state.busy=true;await poll();
    });card.append(request,revise);
    box.append(card);
  }
  if(plan.warnings?.length){const notes=element('details');notes.append(element('summary',`${plan.warnings.length} visual review notes`));for(const warning of plan.warnings)notes.append(element('p',`Scene ${warning.scene}: ${warning.message}`,'helper'));box.prepend(notes);}
}
$('visual-preview-btn').onclick=()=>guarded(async()=>{await saveReviewedScript();const p=state.project;await api(`/api/projects/${p.id}/task`,{revision:p.revision,action:'visual_preview'});state.busy=true;await poll();});
$('creator-revise').onclick=()=>guarded(async()=>{if(state.project.accepted){const p=state.project;state.project=await api(`/api/projects/${p.id}/reopen`,{revision:p.revision});await loadSpaces();renderCreator();}$('script-review').open=true;$('script-review').scrollIntoView({behavior:'smooth',block:'start'});});
$('creator-finish').onclick=()=>guarded(async()=>{if(state.dirty||state.reviewDirty)throw new Error('Save edits and render the updated video before marking it finished.');const p=state.project;state.project=await api(`/api/projects/${p.id}/accept`,{revision:p.revision});await openProject(p.id);message('Video marked finished. Your next playlist topic is now available from New video.');});
$('creator-settings').onclick=()=>spaceDialog(state.spaces.find(w=>w.id===state.spaceId));
$('creator-delete').onclick=()=>guarded(async()=>{
  const p=state.project;if(prompt(`Permanently delete "${p.topic}"? This removes its script, edits, chapter files and exported videos. Shared models and narration caches are retained. This cannot be undone. Type DELETE to confirm.`)!=='DELETE')return;
  await api(`/api/projects/${p.id}/delete`,{revision:p.revision,confirmation:'DELETE'});localStorage.removeItem('visualforge.active');state.project=null;state.doc=null;state.dirty=false;await loadSpaces();renderWorkspace();
});
$('creator-result').insertBefore($('creator-player-shell'),$('script-review'));

window.addEventListener("beforeunload",event=>{if(state.reviewDirty){event.preventDefault();event.returnValue="";}});

$("creator-edit").textContent="Advanced scene editor";document.querySelector(".creator-more").append($("creator-edit"),$("trash-space"));
