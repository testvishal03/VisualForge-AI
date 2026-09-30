"use strict";
const MOTIONS = {
  flow: "Flow along connections",
  assemble: "Assemble concepts",
  focus: "Focus on relationships",
  reveal: "Reveal step by step",
};
const motionDescriptions = {
  flow: "Keep concepts visible as the explanation progresses.",
  assemble: "Concepts move into position as the explanation builds.",
  focus: "Related concepts remain visible while emphasis moves between them.",
  reveal: "Concepts appear progressively and remain for comparison.",
};
function boardChange(card) {
  document.querySelectorAll(".style-sample").forEach((v) => {
    v.pause();
    v.remove();
  });
  state.dirty = true;
  card.querySelectorAll("video").forEach((v) => {
    v.pause();
    v.remove();
  });
  const note = $("storyboard-approval-note");
  if (note) note.textContent = "Changes need review";
  lockControls();
  if (state.doc) {
    renderPreview();
    renderMedia();
  }
}
const KIND_COLORS = {
  process: "#4a9eff",
  comparison: "#ff9a4a",
  cycle: "#4aff9a",
  timeline: "#c084fc",
  relationship: "#f472b6",
  components: "#fb923c",
  chart: "#34d399",
  neural_net: "#818cf8",
  code: "#a3e635",
  stat_card: "#f59e0b",
  water_cycle: "#67e8f9",
  explanation: "#94a3b8",
  example: "#fbbf24",
  takeaway: "#4ade80",
  title: "#f8fafc",
  quote: "#e879f9",
  analogy: "#f87171",
};
function storyboardCard(s, index, chapter, clip) {
  const card = element("article", undefined, "storyboard-card");

  const kind = s.visual.kind;
  const color = KIND_COLORS[kind] || "#94a3b8";

  const header = element("div", `SCENE ${index + 1}`, "eyebrow");
  header.style.display = "flex";
  header.style.justifyContent = "space-between";
  header.style.alignItems = "center";

  const badge = element("span", kind.replaceAll("_", " "));
  badge.style.backgroundColor = color + "33";
  badge.style.border = `1px solid ${color}`;
  badge.style.color = color;
  badge.style.fontSize = "11px";
  badge.style.padding = "2px 8px";
  badge.style.borderRadius = "10px";
  badge.style.textTransform = "uppercase";
  badge.style.letterSpacing = "0.5px";

  header.append(badge);
  card.append(header, element("h3", s.headline));
  const teaching = !chapter && !state.dirty && state.project.teaching_plan?.find(plan=>plan.uid===s.uid);
  if (teaching) {
    const details=element('details');
    details.append(element('summary',`Teaching plan: ${teaching.component.replaceAll('_',' ')}`));
    details.append(element('p',teaching.question),element('p',teaching.objective));
    const steps=element('ol');
    for(const step of teaching.steps)steps.append(element('li',`Sentence ${step.sentence+1}: ${step.action} — ${step.label}`));
    details.append(steps,element('p',`Takeaway: ${teaching.takeaway}`),element('p',teaching.evidence==='illustrative'?'Uses explicitly labeled toy vectors; these are not model embeddings.':'Visual steps are linked to your narration.','helper'));
    card.append(details);
  }
  const sketch = element("div", undefined, "storyboard-sketch");
  for (const label of s.visual.worked ? [s.visual.worked.input, ...s.visual.worked.steps.map(step=>`${step.action} / sentence ${step.sentence+1}`)] : s.visual.items.length ? s.visual.items : [s.body])
    sketch.append(element("span", label));
  card.append(
    sketch,
    element(
      "p",
      "Composition sketch · use Play scene to check rendered motion.",
      "helper",
    ),
  );

  const label = element("label");
  label.style.display = "flex";
  label.style.justifyContent = "space-between";

  const titleSpan = element("span", "Narration");
  const wordCount = s.narration
    ? s.narration
        .trim()
        .split(/\s+/)
        .filter((w) => w.length > 0).length
    : 0;
  const durationText = s.duration
    ? `${s.duration}s measured`
    : `~${(wordCount / 2.5).toFixed(1)}s`;
  const metaSpan = element("span", `📝 ${wordCount} words · ${durationText}`);
  metaSpan.style.color = "gray";
  metaSpan.style.fontSize = "12px";
  metaSpan.style.fontWeight = "normal";

  label.append(titleSpan, metaSpan);

  const narration = element("textarea");
  narration.rows = 4;
  narration.maxLength = 600;
  narration.value = s.narration;
  narration.setAttribute("aria-label", `Scene ${index + 1} narration`);
  narration.oninput = () => {
    s.narration = narration.value;
    const newWordCount = s.narration
      ? s.narration
          .trim()
          .split(/\s+/)
          .filter((w) => w.length > 0).length
      : 0;
    const newDurationText = s.duration
      ? `${s.duration}s measured`
      : `~${(newWordCount / 2.5).toFixed(1)}s`;
    metaSpan.textContent = `📝 ${newWordCount} words · ${newDurationText}`;
    boardChange(card);
  };

  const copyBtn = element("button", "Copy", "secondary");
  copyBtn.style.background = "transparent";
  copyBtn.style.fontSize = "12px";
  copyBtn.style.padding = "3px 10px";
  copyBtn.style.marginTop = "4px";
  copyBtn.onclick = async () => {
    try {
      await navigator.clipboard.writeText(s.narration);
      copyBtn.textContent = "Copied!";
      setTimeout(() => (copyBtn.textContent = "Copy"), 2000);
    } catch (err) {}
  };

  card.append(label, narration, copyBtn);
  const demoControls=element('details');
  demoControls.append(element('summary','Python / SQL worked example'));
  const suggested=!chapter?state.project.demonstration_specs?.[s.uid]:null;
  const configured=s.visual.demo?.kind!=='off'?s.visual.demo:null;
  const spec=configured||suggested;
  const demoKind=element('select');
  for(const [value,title] of [['auto','Automatic from narration'],['off','No computed example'],['python_variables','Python variables'],['python_condition','Python condition'],['python_loop','Python loop'],['sql_filter','SQL WHERE filter'],['sql_join','SQL INNER JOIN']]){
    const option=element('option',title);option.value=value;demoKind.append(option);
  }
  demoKind.value=s.visual.demo?.kind||'auto';demoKind.setAttribute('aria-label','Worked example type');
  const values=element('input');values.value=(spec?.values||[12,25,8]).join(', ');values.setAttribute('aria-label','Example values');
  const threshold=element('input');threshold.type='number';threshold.min=-100;threshold.max=100;threshold.value=spec?.threshold??15;threshold.setAttribute('aria-label','Example threshold');
  const cue=element('input');cue.type='number';cue.min=1;cue.max=60;cue.value=(spec?.sentence??0)+1;cue.setAttribute('aria-label','Example starting sentence');
  const applyDemo=()=>{
    const kind=demoKind.value==='auto'?spec?.kind:demoKind.value;
    if(!kind){message('Choose a demonstration type before editing its inputs.');return;}
    if(kind==='off'){s.visual.demo={kind:'off'};boardChange(card);return;}
    const numbers=values.value.split(',').map(v=>v.trim()).filter(Boolean).map(Number);
    if(numbers.length<2||numbers.length>5||numbers.some(v=>!Number.isInteger(v)||Math.abs(v)>100)||!Number.isInteger(Number(threshold.value))||Math.abs(Number(threshold.value))>100||!Number.isInteger(Number(cue.value))||Number(cue.value)<1){message('Use 2–5 integers between -100 and 100, an integer threshold, and a valid sentence number.');return;}
    demoKind.value=kind;s.visual.demo={kind,values:numbers,threshold:Number(threshold.value),sentence:Number(cue.value)-1};boardChange(card);
  };
  demoKind.onchange=()=>{if(demoKind.value==='auto'){delete s.visual.demo;boardChange(card);}else applyDemo();};
  for(const input of [values,threshold,cue])input.onchange=applyDemo;
  const carry=element('button','Use previous scene’s example values','secondary');carry.type='button';
  carry.onclick=()=>{const previous=chapter?.document?.scenes?.[index-1]||(!chapter?state.doc.scenes[index-1]:null);const old=previous?.visual.demo||state.project.demonstration_specs?.[previous?.uid];if(!old?.values){message('The previous scene has no example inputs to copy.');return;}values.value=old.values.join(', ');threshold.value=old.threshold;applyDemo();};
  demoControls.append(demoKind,element('p','Values (2–5 integers):'),values,element('p','Condition / WHERE threshold:'),threshold,element('p','Start at narration sentence:'),cue,carry,element('p','These are computed teaching examples. SQL examples reuse the same customers and orders. Check the scene preview after changing inputs.','helper'));
  card.append(demoControls);
  const layouts = {
    auto: "AI composition",
    pipeline: "Process demonstration",
    branching: "Branching relationships",
    layers: "System layers",
    contrast: "Side-by-side comparison",
    timeline: "Timeline",
    detail: "Zoom into details",
  };
  const allowed = {
    process: ["pipeline", "detail"],
    relationship: ["branching", "detail"],
    components: ["layers", "detail"],
    comparison: ["contrast", "detail"],
    timeline: ["timeline", "detail"],
  };
  const ll = element("label", "Scene composition");
  const ls = element("select");
  ls.setAttribute("aria-label", `Scene ${index + 1} composition`);
  for (const value of ["auto", ...(allowed[s.visual.kind] || [])]) {
    const o = element("option", layouts[value]);
    o.value = value;
    ls.append(o);
  }
  ls.value = s.visual.layout || "auto";
  ls.onchange = () => {
    s.visual.layout = ls.value;
    select.dataset.blocked = String(!supported || ls.value === "detail");
    note.textContent =
      ls.value === "detail"
        ? "Close-up view follows one concept at a time."
        : supported
          ? motionDescriptions[select.value]
          : "This layout uses its built-in animation.";
    boardChange(card);
  };
  ll.append(ls);
  card.append(ll);
  const ml = element("label", "Animation treatment");
  const select = element("select");
  select.setAttribute("aria-label", `Scene ${index + 1} animation`);
  for (const [value, text] of Object.entries(MOTIONS)) {
    const option = element("option", text);
    option.value = value;
    select.append(option);
  }
  select.value = s.visual.motion || "flow";
  const supported =
    s.visual.items.length >= 2 &&
    [
      "process",
      "relationship",
      "components",
      "comparison",
      "timeline",
    ].includes(s.visual.kind);
  select.dataset.blocked = String(!supported || s.visual.layout === "detail");
  const note = element(
    "p",
    s.visual.layout === "detail"
      ? "Close-up view follows one concept at a time."
      : supported
        ? motionDescriptions[select.value]
        : "This layout uses its built-in animation. Replan visuals to choose a different layout.",
    "helper",
  );
  select.onchange = () => {
    s.visual.motion = select.value;
    note.textContent = motionDescriptions[select.value];
    boardChange(card);
  };
  ml.append(select);
  card.append(ml, note);
  appendWorkedEditor(card,s,index,chapter);
  const instruction = element("input");
  instruction.placeholder = "Optional: what should improve?";
  instruction.maxLength = 1000;
  instruction.setAttribute(
    "aria-label",
    `Scene ${index + 1} improvement instruction`,
  );
  card.append(instruction);
  const actions = element("div", undefined, "storyboard-actions");
  for (const [action, text] of [
    ["motion", "Play scene"],
    ["replan", "Replan visuals"],
    ["regenerate", "Rewrite scene"],
    ["audio", "Prepare audio"],
    ...(s.visual.worked ? [["prepare_example", "Prepare example"]] : []),
  ]) {
    const b = element("button", text, "secondary");
    b.onclick = () =>
      guarded(async () => {
        state.boardInstructions =
          instruction.value || "Make the explanation concrete and concise.";
        if (chapter) await longTask("long_scene_" + action, s.uid);
        else {
          await save();
          await api(`/api/projects/${state.project.id}/task`, {
            revision: state.project.revision,
            action,
            uid: s.uid,
            instructions: state.boardInstructions,
          });
          state.busy = true;
          await poll();
        }
      });
    actions.append(b);
  }
  card.append(actions);
  if (clip) {
    const v = element("video");
    v.controls = true;
    v.preload = "metadata";
    v.src = clip;
    v.setAttribute("aria-label", `Scene ${index + 1} rendered animation`);
    card.append(v);
  }
  return card;
}
function renderStoryboardReview() {
  const box = $("storyboard-review");
  box.replaceChildren();
  box.hidden = !state.doc;
  if (!state.doc) return;
  box.append(
    element("h2", "Review the story before rendering"),
    element(
      "p",
      "Read the narration, choose the motion, and preview individual scenes. Only the selected scene is regenerated.",
      "helper",
    ),
  );
  const approval = element("div", undefined, "storyboard-actions");
  const approve = element("button", "🎬 Approve & Render Video Now", "primary");
  approve.id = "approve-storyboard";
  approve.onclick = () =>
    guarded(async () => {
      await save();
      state.project = await api(`/api/projects/${state.project.id}/approve`, {
        revision: state.project.revision,
      });
      const profile = state.project.source?.profile || "final";
      const renderAction = profile === "draft" ? "render_draft" : "render";
      await api(`/api/projects/${state.project.id}/task`, {
        revision: state.project.revision,
        action: renderAction,
        instructions: $("instructions")?.value || "",
      });
      state.busy = true;
      window.scrollTo({ top: 0, behavior: "smooth" });
      await poll();
    });
  approval.append(
    approve,
    element(
      "span",
      state.project.storyboard_approved && !state.dirty
        ? "Approved for export"
        : "Approve storyboard and immediately generate video",
      "helper",
    ),
  );
  box.append(approval);
  approval.lastChild.id = "storyboard-approval-note";
  appendStylePreview(box, state.project);
  appendVisualWarnings(box, state.project.quality);
  const grid = element("div", undefined, "storyboard-grid");
  state.doc.scenes.forEach((s, i) =>
    grid.append(storyboardCard(s, i, null, state.project.motion_urls?.[s.uid])),
  );
  box.append(grid);
}
function renderChapterStoryboard(box, p) {
  box.append(
    element(
      "p",
      "Review each chapter scene before approving the storyboard. Play scene renders just that scene; full-video exports remain behind approval.",
      "helper",
    ),
  );
  p.chapter_details.forEach((c, i) => {
    const chapter = element("details");
    chapter.open = i === 0;
    chapter.append(element("summary", c.title));
    box.append(chapter);
    const doc = state.longDraft.documents[c.id];
    if (!doc) {
      chapter.append(element("p", "Generate the chapter script first."));
      return;
    }
    appendStylePreview(chapter, c, doc.scenes[0]?.uid);
    appendVisualWarnings(chapter, c.quality);
    const grid = element("div", undefined, "storyboard-grid");
    doc.scenes.forEach((s, i) =>
      grid.append(storyboardCard(s, i, c.id, c.motion_urls?.[s.uid])),
    );
    chapter.append(grid);
  });
  lockControls();
}
const originalWorkspaceRender = renderWorkspace;
renderWorkspace = function () {
  originalWorkspaceRender();
  if (!state.project?.long_video) renderStoryboardReview();
  lockControls();
};
const originalLockControls = lockControls;
lockControls = function () {
  originalLockControls();
  document
    .querySelectorAll(
      ".storyboard-card button,.storyboard-card input,.storyboard-card select,.storyboard-card textarea,#approve-storyboard,.style-preview-button",
    )
    .forEach(
      (e) =>
        (e.disabled =
          state.busy || state.pending || e.dataset.blocked === "true"),
    );
  if (
    state.project?.review_required &&
    (!state.project.storyboard_approved || state.dirty)
  ) {
    $("render").disabled = true;
    $("draft-render").disabled = true;
  }
};
const originalDirty = dirty;
dirty = function () {
  originalDirty();
  if (!state.project?.long_video) renderStoryboardReview();
  lockControls();
};
const originalInputModeChange = $("input-mode").onchange;
$("input-mode").onchange = () => {
  originalInputModeChange();
  if ($("input-mode").value !== "long") {
    $("create-submit").textContent = "Create storyboard";
    $("input-help").textContent +=
      " You will review the storyboard before narration and full rendering.";
  }
};
$("create-submit").textContent = "Create storyboard";
$("input-help").textContent =
  "The local model prepares your script and visual plan. Review the storyboard, preview individual scenes, then approve and export.";
document.querySelector('label[for="new-profile"]').textContent =
  "Export quality after review";

function appendVisualWarnings(box, quality) {
  for (const issue of quality?.issues || []) {
    if (
      ["repeated_layout", "visual_text_density", "static_explanation", "example_narration", "example_token_count", "example_unsupported_number"].includes(
        issue.code,
      )
    )
      box.append(
        element("p", `Scene ${issue.scene}: ${issue.message}`, "helper"),
      );
  }
}
function appendStylePreview(box, p, uid) {
  const b = element(
    "button",
    "Preview video style (30-60s)",
    "secondary style-preview-button",
  );
  b.onclick = () =>
    guarded(async () => {
      if (uid) await longTask("long_scene_style_preview", uid);
      else {
        await save();
        await api(`/api/projects/${state.project.id}/task`, {
          revision: state.project.revision,
          action: "style_preview",
        });
        state.busy = true;
        await poll();
      }
    });
  box.append(
    b,
    element(
      "p",
      "A varied sample of consecutive scenes, with complete narration. Short scripts produce shorter samples. Chapter previews sample this chapter.",
      "helper",
    ),
  );
  if (p.style_url && !state.dirty) {
    const video = element("video", undefined, "style-sample");
    video.controls = true;
    video.preload = "metadata";
    video.src = p.style_url;
    video.style.width = "100%";
    video.style.maxWidth = "800px";
    box.append(video);
  }
}


function appendWorkedEditor(card,scene,index,chapter) {
  const box=element('details');
  box.open=!!scene.visual.worked;
  box.append(element('summary','Animated LLM worked example'));
  box.append(element('p','Use real tokenizer output and one local-model continuation. Assign one action per narration sentence. Processing is schematic; reveal speed is illustrative.','helper'));
  const controls=element('div');
  const toggle=element('button',scene.visual.worked?'Remove example':'Add example','secondary');
  const draw=()=>{
    controls.replaceChildren();
    toggle.textContent=scene.visual.worked?'Remove example':'Add example';
    const spec=scene.visual.worked;
    if(!spec)return;
    for(const [key,title,max] of [['input','Example input',80],['label','Example label',40]]) {
      const label=element('label',title),input=element('input');
      input.value=spec[key];input.maxLength=max;input.setAttribute('aria-label',`Scene ${index+1} ${title}`);
      input.oninput=()=>{spec[key]=input.value;status.textContent='Save and prepare to check this example.';boardChange(card);};
      label.append(input);controls.append(label);
    }
    const doc=chapter?state.longDraft?.documents?.[chapter]:state.doc;
    const previous=doc?.scenes?.[index-1]?.visual?.worked;
    if(previous){const copy=element('button','Use previous scene input','secondary');copy.onclick=()=>{spec.input=previous.input;spec.label=previous.label;boardChange(card);draw();};controls.append(copy);}
    const parts=scene.narration.replace(/\b(?:Mr|Mrs|Ms|Dr|Prof|e\.g|i\.e|[A-Z])\./g,m=>m.replaceAll('.','\u2024')).split(/(?<=[.!?])\s+(?=[A-Z0-9"\u201c])/).filter(s=>s.trim()).map(s=>s.replaceAll('\u2024','.'));
    controls.append(element('p','Sentence cues: '+parts.map((s,i)=>`${i+1}. ${s}`).join(' '),'helper'));
    spec.steps.forEach((step,i)=>{
      const row=element('div',undefined,'storyboard-actions');
      const action=element('select');action.setAttribute('aria-label',`Example action ${i+1}`);
      for(const [value,title] of [['tokens','Show tokens'],['ids','Show token IDs'],['process','Schematic processing'],['generate','Reveal continuation']]){const option=element('option',title);option.value=value;action.append(option);}
      action.value=step.action;action.onchange=()=>{step.action=action.value;boardChange(card);};
      const cue=element('input');cue.type='number';cue.min='1';cue.max=String(parts.length);cue.value=String(step.sentence+1);cue.setAttribute('aria-label',`Narration sentence for action ${i+1}`);
      cue.onchange=()=>{step.sentence=Number(cue.value)-1;boardChange(card);};
      const remove=element('button','Remove step','secondary');remove.dataset.blocked=String(spec.steps.length===1);remove.disabled=spec.steps.length===1;remove.onclick=()=>{spec.steps.splice(i,1);boardChange(card);draw();};
      row.append(action,element('span','Sentence'),cue,remove);controls.append(row);
    });
    if(spec.steps.length<4&&(spec.steps.at(-1)?.sentence??-1)+1<parts.length){const add=element('button','Add step','secondary');add.onclick=()=>{spec.steps.push({action:['tokens','ids','process','generate'][spec.steps.length],sentence:(spec.steps.at(-1)?.sentence??-1)+1});boardChange(card);draw();};controls.append(add);}
    const info=chapter?state.project.chapter_details?.find(c=>c.id===chapter):state.project;
    const measured=info?.worked_examples?.[scene.uid];
    const status=element('p',measured?.ready&&measured.input===spec.input?`${measured.token_count} measured tokens from ${measured.model}. Continuation: ${measured.continuation}`:'Save, then use Prepare example or Play scene to measure this input.','helper');
    controls.append(status);
  };
  toggle.onclick=()=>{
    if(scene.visual.worked)delete scene.visual.worked;
    else scene.visual.worked={input:'The cat sat on the',label:'Sentence example',steps:[{action:'tokens',sentence:0}]};
    boardChange(card);
    // Rebuild the scene to update task buttons and example controls together.
    card.replaceWith(storyboardCard(scene,index,chapter,null));
  };
  box.append(toggle,controls);card.append(box);draw();
}
