"use strict";
const $ = (id) => document.getElementById(id);
const state = {
  token: "",
  project: null,
  doc: null,
  selected: null,
  dirty: false,
  busy: false,
  pending: true,
  lastJob: "",
  spaces: [],
  spaceId: null,
  editingSpace: null,
};
const clone = (value) => structuredClone(value);
function element(tag, text, className) {
  const e = document.createElement(tag);
  if (text !== undefined) e.textContent = text;
  if (className) e.className = className;
  return e;
}
async function api(path, body) {
  const r = await fetch(path, {
    method: body === undefined ? "GET" : "POST",
    headers:
      body === undefined
        ? {}
        : { "Content-Type": "application/json", "X-Editor-Token": state.token },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Request failed");
  return data;
}
function message(text) {
  $("message").textContent = text || "";
  $("message").hidden = !text;
  for (const dialog of document.querySelectorAll("dialog")) {
    let error = dialog.querySelector(".dialog-error");
    if (!error) {
      error = element("p", "", "dialog-error");
      error.setAttribute("role", "alert");
      dialog.prepend(error);
    }
    error.textContent = dialog.open ? text || "" : "";
    error.hidden = !error.textContent;
  }
}
function scene() {
  return state.doc?.scenes.find((s) => s.uid === state.selected);
}
function lockControls() {
  lockLongControls();
  const locked = state.busy || state.pending;
  for (const id of [
    "new-project",
    "welcome-new",
    "studio-generate-btn",
    "import",
    "save",
    "render",
    "audio",
    "all-audio",
    "preview",
    "regenerate",
    "move-up",
    "move-down",
    "retry-draft",
    "create-submit",
    "new-space",
    "edit-space",
    "duplicate-space",
    "trash-space",
    "draft-render",
    "replan",
  ])
    $(id) && ($(id).disabled = locked);
  for (const id of [
    "video-title",
    "headline",
    "body",
    "narration",
    "layout",
    "composition",
    "instructions",
    "studio-topic",
    "studio-script",
    "studio-long-minutes",
  ])
    $(id) && ($(id).disabled = locked);
  document
    .querySelectorAll("#visual-items textarea, #visual-items input")
    .forEach((e) => (e.disabled = locked));
  $("composition").disabled =
    locked ||
    ["water_cycle", "chart", "comparison", "cycle"].includes(
      scene()?.visual.kind,
    );
  $("save").disabled = locked || !state.dirty;
  $("render").disabled = locked || !state.doc;
  $("draft-render").disabled = locked || !state.doc;
  const i = state.doc?.scenes.findIndex((s) => s.uid === state.selected) ?? 0;
  $("move-up").disabled = locked || i <= 0;
  $("move-down").disabled =
    locked || !state.doc || i >= state.doc.scenes.length - 1;
  $("save-state").textContent = state.dirty ? "Unsaved changes" : "Saved";
  document
    .querySelectorAll(".episode-move")
    .forEach((b) => (b.disabled = locked || b.dataset.edge === "true"));
}
function dirty() {
  state.dirty = true;
  lockControls();
  renderPreview();
  renderQuality();
  renderMedia();
}
async function guarded(fn) {
  if (state.pending) return;
  state.pending = true;
  message("");
  lockControls();
  try {
    await fn();
  } catch (error) {
    message(error.message);
  } finally {
    state.pending = false;
    lockControls();
  }
}
async function loadProjects() {
  await loadSpaces();
}
async function openProject(id, scroll = true) {
  if(state.reviewDirty&&id!==state.project?.id&&!confirm("Discard unsaved script edits?"))return;
  if(id!==state.project?.id)state.reviewDirty=false;
  state.project = await api("/api/projects/" + id);
  localStorage.setItem("visualforge.active",id);
  state.spaceId = state.project.workspace?.id || state.spaceId;
  state.doc = state.project.document ? clone(state.project.document) : null;
  state.dirty = false;
  if (!state.doc?.scenes.some((s) => s.uid === state.selected))
    state.selected = state.doc?.scenes[0]?.uid;
  renderWorkspace();
  await loadProjects();
  if (scroll) window.scrollTo(0, 0);
}
function renderWorkspace() {
  $("long-workspace").hidden = !state.project?.long_video;
  if (state.project?.long_video) {
    $("welcome").hidden = true;
    $("workspace").hidden = true;
    renderLongVideo();
    lockControls();
    return;
  }
  $("welcome").hidden = !!state.project;
  $("workspace").hidden = !state.project;
  if (!state.project) return;
  $("video-title").value = state.doc?.title || state.project.topic;
  $("topic").textContent = state.project.topic;
  $("editor-grid").hidden = !state.doc;
  $("draft-empty").hidden = !!state.doc;
  if (!state.doc) {
    const running = state.project.last_job?.status === "running";
    $("draft-empty-title").textContent = running
      ? "Your draft is on its way."
      : "Draft generation needs attention";
    $("draft-empty-note").textContent = running
      ? "Local generation can take several minutes. Progress appears below."
      : "The draft is not complete. Retry uses saved checkpoints, or start a new video with a reviewed written script.";
  }
  $("retry-draft").textContent = state.project.directed
    ? "Retry video generation"
    : "Retry draft generation";
  if (state.doc) {
    renderScenes();
    renderEditor();
  }
  lockControls();
}
function renderScenes() {
  $("scene-count").textContent = state.doc.scenes.length;
  $("scenes").replaceChildren();
  state.doc.scenes.forEach((s, i) => {
    const b = element(
      "button",
      undefined,
      "scene-button" + (s.uid === state.selected ? " active" : ""),
    );
    b.append(element("b", String(i + 1).padStart(2, "0")));
    const label = element("span", s.headline);
    label.append(element("small", s.visual.kind.replaceAll("_", " ")));
    b.append(label);
    b.onclick = () => {
      state.selected = s.uid;
      renderScenes();
      renderEditor();
    };
    $("scenes").append(b);
  });
}
function renderEditor() {
  const s = scene();
  if (!s) return;
  const i = state.doc.scenes.indexOf(s);
  $("scene-number").textContent =
    `SCENE ${String(i + 1).padStart(2, "0")} / ${String(state.doc.scenes.length).padStart(2, "0")}`;
  for (const key of ["headline", "body", "narration"]) $(key).value = s[key];
  $("layout").value = s.visual.kind;
  $("composition").value = s.visual.variant ?? 0;
  renderItems();
  wordCount();
  renderPreview();
  renderQuality();
  renderMedia();
  lockControls();
}
function renderItems() {
  $("direction-note").textContent = state.project.directed
    ? "Automatic direction: visuals follow measured narration sentences. Narration edits replan this scene; layout edits reuse audio. Composition A/B is available for general diagrams and explanation cards."
    : "";
  $("visual-items").replaceChildren();
  scene().visual.items.forEach((value, i) => {
    const label = element(
      "label",
      scene().visual.kind === "process"
        ? `Step ${i + 1}`
        : scene().visual.kind !== "comparison"
          ? `Diagram label ${i + 1}`
          : state.project.directed
            ? `Comparison ${i + 1}`
            : i === 0
              ? "Possibilities caption"
              : "Limitations caption",
    );
    const input = element("textarea");
    input.rows = 2;
    input.value = value;
    input.maxLength = scene().visual.kind === "comparison" ? 180 : 70;
    input.setAttribute("aria-label", label.textContent);
    input.oninput = () => {
      scene().visual.items[i] = input.value;
      dirty();
    };
    label.append(input);
    $("visual-items").append(label);
    if (scene().visual.kind === "chart") {
      const numberLabel = element("label", "Percentage " + (i + 1));
      const number = element("input");
      number.type = "number";
      number.min = 0;
      number.max = 100;
      number.step = "any";
      number.value = scene().visual.values[i];
      number.oninput = () => {
        scene().visual.values[i] =
          number.value === "" ? null : Number(number.value);
        dirty();
      };
      numberLabel.append(number);
      $("visual-items").append(numberLabel);
    }
  });
}
function wordCount() {
  const count =
    scene()?.narration.match(/\b[\w]+(?:[-'][\w]+)*\b/g)?.length || 0;
  $("word-count").textContent = `${count} words`;
  $("word-count").style.color = count < 15 || count > 60 ? "#a43832" : "";
}
function renderPreview() {
  const s = scene();
  if (!s) return;
  const sketch = $("layout-sketch");
  sketch.replaceChildren(
    element("div", s.visual.kind.replaceAll("_", " "), "sketch-kind"),
    element("h3", s.headline),
  );
  if (s.visual.items.length) {
    const cards = element("div", undefined, "sketch-cards");
    s.visual.items.forEach((item, i) => {
      const card = element("div", undefined, "sketch-card");
      card.append(
        element(
          "b",
          s.visual.kind !== "comparison"
            ? `0${i + 1} →`
            : state.project.directed
              ? "VIEW " + (i + 1)
              : i === 0
                ? "POSSIBILITIES"
                : "LIMITATIONS",
        ),
        element("span", item || "Add a label"),
      );
      cards.append(card);
    });
    sketch.append(cards);
  } else sketch.append(element("p", s.body));
  const saved = state.project.document;
  const original = saved?.scenes.find((x) => x.uid === s.uid);
  const unchanged =
    original &&
    JSON.stringify(original) === JSON.stringify(s) &&
    saved.title === state.doc.title &&
    saved.scenes.findIndex((x) => x.uid === s.uid) ===
      state.doc.scenes.indexOf(s);
  const url = unchanged ? state.project.preview_urls?.[s.uid] : null;
  $("exact-preview").hidden = !url;
  sketch.hidden = !!url;
  if (url && $("exact-preview").getAttribute("src") !== url)
    $("exact-preview").src = url;
  $("preview-note").textContent = url
    ? "Actual Remotion frame using the saved scene and measured narration."
    : "Live layout sketch. Render an exact frame to check the final design.";
}
function renderQuality() {
  const box = $("quality");
  box.replaceChildren();
  if (state.dirty) {
    box.append(element("p", "Save to refresh editorial checks.", "helper"));
    return;
  }
  const i = state.doc.scenes.findIndex((s) => s.uid === state.selected) + 1;
  const issues =
    state.project.quality?.issues.filter(
      (x) => x.scene === i || x.scene === 0,
    ) || [];
  if (!issues.length)
    box.append(
      element("p", "No automated issues found in this scene.", "quality-clear"),
    );
  for (const issue of issues)
    box.append(element("div", issue.message, "quality-note " + issue.severity));
  const total = state.project.quality?.issues.length || 0;
  if (total)
    box.append(
      element(
        "p",
        `${total} review note${total === 1 ? "" : "s"} across this video.`,
        "helper",
      ),
    );
}
function renderMedia() {
  renderDraftMedia();
  const s = scene();
  if (!s) return;
  const original = state.project.document?.scenes.find((x) => x.uid === s.uid);
  const audio =
    original?.narration === s.narration ? state.project.audio?.[s.uid] : null;
  const player = $("audio-player");
  player.hidden = !audio;
  if (audio) {
    if (player.getAttribute("src") !== audio.url) player.src = audio.url;
    $("audio-note").textContent =
      `${audio.duration.toFixed(2)} seconds · reusable narration`;
  } else {
    player.pause();
    player.removeAttribute("src");
    $("audio-note").textContent =
      "Generate this scene’s audio to listen. Narration edits refresh only this WAV.";
  }
  const url = !state.dirty ? state.project.video_url : null;
  $("final-result").hidden = !url;
  if (url) {
    if ($("final-video").getAttribute("src") !== url)
      $("final-video").src = url;
    $("download").href = url;
    let tsDiv = $("yt-timestamps-container");
    if (!tsDiv) {
      tsDiv = element("div");
      tsDiv.id = "yt-timestamps-container";
      tsDiv.style.marginTop = "15px";
      const tsHeader = element("div");
      tsHeader.style.display = "flex";
      tsHeader.style.justifyContent = "space-between";
      tsHeader.style.alignItems = "center";
      tsHeader.style.marginBottom = "5px";
      const label = element("div", "YOUTUBE CHAPTERS", "section-label");
      label.style.marginBottom = "0";
      const copyBtn = element("button", "Copy timestamps", "text-button");
      copyBtn.onclick = async () => {
        try {
          const ta = $("yt-timestamps-textarea");
          if (ta) {
            await navigator.clipboard.writeText(ta.value);
            copyBtn.textContent = "Copied!";
            setTimeout(() => (copyBtn.textContent = "Copy timestamps"), 2000);
          }
        } catch (err) {}
      };
      tsHeader.append(label, copyBtn);
      const tsTextarea = element("textarea");
      tsTextarea.id = "yt-timestamps-textarea";
      tsTextarea.readOnly = true;
      tsTextarea.rows = 5;
      tsTextarea.style.fontSize = "12px";
      tsTextarea.style.fontFamily = "monospace";
      tsTextarea.onclick = () => tsTextarea.select();
      tsDiv.append(tsHeader, tsTextarea);
      $("final-result").append(tsDiv);
    }
    if (state.doc && state.doc.scenes) {
      let currentSeconds = 0;
      let tsLines = [];
      for (const sc of state.doc.scenes) {
        const mm = Math.floor(currentSeconds / 60)
          .toString()
          .padStart(2, "0");
        const ss = Math.floor(currentSeconds % 60)
          .toString()
          .padStart(2, "0");
        tsLines.push(`${mm}:${ss} ${sc.headline}`);
        let dur = sc.duration;
        if (!dur) {
          const wc = sc.narration
            ? sc.narration
                .trim()
                .split(/\s+/)
                .filter((w) => w.length > 0).length
            : 0;
          dur = wc / 2.5;
        }
        currentSeconds += dur + 0.5;
      }
      const ta = $("yt-timestamps-textarea");
      if (ta) ta.value = tsLines.join("\n");
    }
  } else {
    $("final-video").pause();
    $("final-video").removeAttribute("src");
  }
}
async function save() {
  if (!state.dirty) return;
  if (state.project?.long_video) {
    await saveLong();
    return;
  }
  state.project = await api(`/api/projects/${state.project.id}/save`, {
    revision: state.project.revision,
    document: state.doc,
  });
  state.doc = clone(state.project.document);
  state.dirty = false;
  renderWorkspace();
  await loadProjects();
}
async function task(action, uid) {
  await save();
  await api(`/api/projects/${state.project.id}/task`, {
    revision: state.project.revision,
    action,
    uid,
    instructions: $("instructions").value,
  });
  state.busy = true;
  await poll();
}
async function poll() {
  if(state.polling)return;
  state.polling=true;
  try {
    const job = await api("/api/job");
    state.job=job;
    if(job.status==="running"&&!state.project)await openProject(job.project,false);
    if (state.offline) {
      state.offline = false;
      message("");
    }
    state.busy = job.status === "running";
    $("job-panel").hidden = job.status === "idle";
    if (job.status !== "idle") {
      $("job-title").textContent =
        {
          long_outline: "Chapter outline",
          long_scripts: "Chapter scripts",
          long_visuals: "AI visual planning",
          long_audio: "Chapter narration",
          long_adjust: "Chapter duration rewrite",
          long_render_draft: "Chapter drafts and full video",
          long_render: "Final chapter export",
          generate: "Automatic video generation",
          draft: "Draft generation",
          audio: "Narration",
          preview: "Exact frame preview",
          regenerate: "Scene regeneration",
          replan: "Visual planning",
          prepare_example: "Preparing measured example",
          long_scene_prepare_example: "Preparing measured example",
          render_draft: "720p draft render",
          render: "1080p final render",
        }[job.action] || "Generating Video";
      $("job-phase").textContent =
        job.status === "complete"
          ? job.result_kind === "storyboard"
            ? "Storyboard ready"
            : {
                style_preview: "Style preview ready",
                long_scene_style_preview: "Style preview ready",
                prepare_example: "Measured example ready",
                long_scene_prepare_example: "Measured example ready",
                motion: "Scene preview ready",
                long_scene_motion: "Scene preview ready",
                long_scripts: "Chapter scripts ready",
                long_outline: "Outline ready",
                audio: "Narration ready",
                long_audio: "Narration ready",
                replan: "Visual plan ready",
                long_visuals: "Visual plans ready",
                render: "Video ready",
                render_draft: "Draft video ready",
                long_render: "Video ready",
                long_render_draft: "Draft video ready",
              }[job.action] || "Video ready"
          : job.phase ||
            (job.status === "running" ? "Processing..." : job.status);
      $("job-log").textContent = (job.progress || []).join("\n");
      let pBar = $("job-progress-bar");
      const logs = job.progress || [];
      const fullText = logs.join("\n");
      let frameCurrent = null;
      let frameTotal = null;
      let timeRemaining = null;
      let sceneCurrent = null;
      let sceneTotal = state.doc?.scenes?.length || null;
      let phaseDetail = "";

      for (let i = logs.length - 1; i >= 0; i--) {
        const line = logs[i];
        const remMatch = line.match(
          /(?:Rendered|Rendering frame)\s+(\d+)\s*(?:\/|of)\s*(\d+)/i,
        );
        if (remMatch && frameCurrent === null) {
          frameCurrent = parseInt(remMatch[1], 10);
          frameTotal = parseInt(remMatch[2], 10);
        }
        const trMatch = line.match(/time\s*remaining:\s*([^\r\n,]+)/i);
        if (trMatch && timeRemaining === null) {
          timeRemaining = trMatch[1].trim();
        }
        const sceneMatch = line.match(
          /Scene\s+(\d+)(?:\s*\/\s*(\d+)|\s*:|\b)/i,
        );
        if (sceneMatch && sceneCurrent === null) {
          sceneCurrent = parseInt(sceneMatch[1], 10);
          if (sceneMatch[2]) sceneTotal = parseInt(sceneMatch[2], 10);
        }
      }

      const isDirectRender = ["render", "render_draft"].includes(job.action);
      let pct = 0;

      if (job.status === "complete") {
        pct = 100;
        phaseDetail = "Video generation complete";
      } else if (frameCurrent !== null && frameTotal && frameTotal > 0) {
        const ratio = Math.min(1, frameCurrent / frameTotal);
        if (isDirectRender) {
          pct = Math.min(98, Math.max(10, Math.round(10 + ratio * 85)));
        } else {
          pct = Math.min(98, Math.max(65, Math.round(65 + ratio * 30)));
        }
        phaseDetail = `Rendering frames: ${frameCurrent} / ${frameTotal}`;
      } else if (
        job.phase === "render" ||
        fullText.toLowerCase().includes("bundling")
      ) {
        pct = isDirectRender ? 10 : 65;
        phaseDetail = "Bundling animation assets and starting compositor...";
      } else if (sceneCurrent !== null) {
        const total = sceneTotal || 10;
        const ratio = Math.min(1, sceneCurrent / total);
        if (isDirectRender) {
          pct = Math.min(15, Math.round(ratio * 15));
        } else {
          pct = Math.min(65, Math.max(30, Math.round(30 + ratio * 35)));
        }
        phaseDetail = `Voice narration: Scene ${sceneCurrent}${sceneTotal ? " / " + sceneTotal : ""}`;
        if (!timeRemaining && job.elapsed_seconds && sceneCurrent > 1) {
          const secPerScene = job.elapsed_seconds / sceneCurrent;
          const leftScenes = Math.max(0, total - sceneCurrent);
          const leftSec = Math.round(secPerScene * leftScenes + total * 1.2);
          const m = Math.floor(leftSec / 60);
          const s = leftSec % 60;
          timeRemaining = m > 0 ? `~${m}m ${s}s` : `~${s}s`;
        }
      } else {
        const t = fullText.toLowerCase();
        if (t.includes("script") || t.includes("outline")) pct = 15;
        else if (t.includes("quality") || t.includes("fact")) pct = 25;
        else if (t.includes("audio") || t.includes("narration")) pct = 45;
        else if (
          t.includes("visual") ||
          t.includes("diagram") ||
          t.includes("props")
        )
          pct = 65;
        else if (t.includes("render") || t.includes("rendered")) pct = 80;
        else if (t.includes("validat")) pct = 95;
        else pct = 10;
        phaseDetail = job.phase ? `Phase: ${job.phase}` : "Processing...";
      }

      if (
        !timeRemaining &&
        job.status === "running" &&
        job.elapsed_seconds > 4 &&
        pct > 5 &&
        pct < 95
      ) {
        const totalSecEst = job.elapsed_seconds / (pct / 100);
        const remSec = Math.max(
          5,
          Math.round(totalSecEst - job.elapsed_seconds),
        );
        const m = Math.floor(remSec / 60);
        const s = remSec % 60;
        timeRemaining = m > 0 ? `~${m}m ${s}s` : `~${s}s`;
      }

      if (pBar) pBar.style.width = pct + "%";
      if ($("job-pct-text")) $("job-pct-text").textContent = pct + "%";

      const steps = [
        { node: $("step-script"), line: $("line-1"), threshold: 15 },
        { node: $("step-quality"), line: $("line-2"), threshold: 25 },
        { node: $("step-audio"), line: $("line-3"), threshold: 45 },
        { node: $("step-visuals"), line: $("line-4"), threshold: 65 },
        { node: $("step-render"), line: null, threshold: 85 },
      ];
      steps.forEach((s, idx) => {
        if (!s.node) return;
        s.node.classList.remove("active", "completed");
        if (s.line) s.line.classList.remove("completed");
        if (pct > s.threshold || pct === 100) {
          s.node.classList.add("completed");
          if (s.line) s.line.classList.add("completed");
        } else if (pct >= (idx === 0 ? 0 : steps[idx - 1].threshold)) {
          s.node.classList.add("active");
        }
      });

      $("cancel").hidden = !state.busy;

      if (job.status === "running") {
        const timeBadge = timeRemaining
          ? `⏳ ${timeRemaining} left`
          : "⏳ Estimating...";
        $("job-phase").textContent = timeBadge;
        const elapsedPart =
          job.elapsed_seconds !== undefined
            ? ` · ${job.elapsed_seconds}s elapsed`
            : "";
        $("job-result").textContent =
          `${phaseDetail} (${timeBadge}${elapsedPart})`;
      } else if (job.status === "complete") {
        $("job-result").textContent =
          job.message || `Completed in ${job.seconds}s.`;
        if (job.audio_cache) {
          $("job-result").textContent +=
            ` Audio: ${job.audio_cache.generated_scene_ids.length} generated, ${job.audio_cache.reused_scene_ids.length} reused.`;
        }
      } else {
        $("job-result").textContent =
          job.error || job.message || "Task finished.";
      }
      const key = job.id + job.status;
      if (!state.busy && key !== state.lastJob) {
        state.lastJob = key;
        if (state.project?.id === job.project && !state.dirty)
          await openProject(job.project, false);
        else await loadProjects();
      }
    }
    lockControls();
    if(typeof renderCreator==="function")renderCreator();
  } catch (error) {
    state.offline = true;
    message(
      "Connection lost. Generation may still be running locally. Reconnecting automatically...",
    );
    if(typeof renderCreator==="function")renderCreator();
  } finally {state.polling=false;}
}
function showNew() {
  workspaceOptions();
  $("new-dialog").showModal();
  $("new-topic").focus();
}
if ($("new-project")) $("new-project").onclick = showNew;
if ($("welcome-new")) $("welcome-new").onclick = showNew;
if ($("close-dialog"))
  $("close-dialog").onclick = () => $("new-dialog").close();
$("create-form").onsubmit = (e) => {
  e.preventDefault();
  guarded(async () => {
    if (state.dirty && !confirm("Discard unsaved changes?")) return;
    const project = await api("/api/projects", {
      mode: $("input-mode").value,
      text: $("new-topic").value,
      title: $("new-title").value,
      minutes: Number($("new-duration").value),
      profile: $("new-profile").value,
      workspace_id: $("new-workspace").value || undefined,
      render_now: true,
    });
    $("new-dialog").close();
    state.busy = true;
    window.scrollTo({ top: 0, behavior: "smooth" });
    await openProject(project.id);
    await poll();
  });
};
$("import").onclick = () =>
  guarded(async () => {
    if (state.dirty && !confirm("Discard unsaved changes?")) return;
    const project = await api("/api/import", { run: $("runs").value });
    await openProject(project.id);
  });
$("video-title").oninput = () => {
  if (state.doc) {
    state.doc.title = $("video-title").value;
    dirty();
  }
};
for (const key of ["headline", "body", "narration"])
  $(key).oninput = () => {
    scene()[key] = $(key).value;
    dirty();
    if (key === "headline") renderScenes();
    if (key === "narration") wordCount();
  };
$("layout").onchange = () => {
  const kind = $("layout").value;
  const count =
    kind === "water_cycle"
      ? 4
      : ["process", "cycle", "components"].includes(kind)
        ? 3
        : ["comparison", "relationship", "timeline", "chart"].includes(kind)
          ? 2
          : 0;
  scene().visual = {
    variant: 0,
    transition: "fade",
    ...(kind === "chart" ? { values: [0, 0] } : {}),
    ...(state.project.directed
      ? {
          directed: true,
          icon: scene().visual.icon || "idea",
          cues: [],
          variant: 0,
          transition: "fade",
        }
      : {}),
    kind,
    items: Array.from(
      { length: count },
      (_, i) => scene().visual.items[i] || "",
    ),
  };
  renderItems();
  dirty();
  renderScenes();
};
function move(delta) {
  const i = state.doc.scenes.findIndex((s) => s.uid === state.selected);
  const j = i + delta;
  if (j < 0 || j >= state.doc.scenes.length) return;
  [state.doc.scenes[i], state.doc.scenes[j]] = [
    state.doc.scenes[j],
    state.doc.scenes[i],
  ];
  dirty();
  renderScenes();
  renderEditor();
}
$("move-up").onclick = () => move(-1);
$("move-down").onclick = () => move(1);
$("save").onclick = () => guarded(save);
$("audio").onclick = () => guarded(() => task("audio", state.selected));
$("all-audio").onclick = () => guarded(() => task("audio"));
$("preview").onclick = () => guarded(() => task("preview", state.selected));
$("regenerate").onclick = () =>
  guarded(() => task("regenerate", state.selected));
$("render").onclick = () => guarded(() => task("render"));
$("retry-draft").onclick = () =>
  guarded(() => task(state.project.directed ? "generate" : "draft"));
$("cancel").onclick = () =>
  guarded(async () => {
    await api("/api/cancel", {});
    $("job-phase").textContent = "Cancelling…";
  });
window.addEventListener("beforeunload", (e) => {
  if (state.dirty) {
    e.preventDefault();
    e.returnValue = "";
  }
});
(async () => {
  try {
    const config = await api("/api/config");
    state.token = config.token;
    state.voices = config.voices || [];
    state.recommendedVoice = config.recommended_voice || "af_heart";
    $("model-status").textContent = config.model?.label || "Local workspace";
    const runs = await api("/api/runs");
    for (const run of runs) {
      const option = element("option", run.title);
      option.value = run.id;
      $("runs").append(option);
    }
    if (runs.length > 1) $("runs").value = runs[runs.length - 1].id;
    await loadProjects();
    const remembered=localStorage.getItem("visualforge.active");
    if(remembered){try{await openProject(remembered,false);}catch{localStorage.removeItem("visualforge.active");}}
    await poll();
    setInterval(poll, 1800);
  } catch (error) {
    message(error.message);
  } finally {
    state.pending=false;
    document.body.classList.remove("is-loading");
    lockControls();
    if(typeof renderCreator==="function")renderCreator();
  }
})();

$("input-mode").onchange = () => {
  const script = $("input-mode").value === "script";
  $("script-title-field").hidden = !script;
  $("new-title").required = false;
  $("duration-field").hidden = script;
  $("new-topic").maxLength = script ? 16000 : 500;
  $("input-label").textContent = script
    ? "Your narration script"
    : "Your prompt";
  $("new-topic").placeholder = script
    ? "Paste spoken narration. Separate teaching points with blank lines."
    : "Explain a topic for beginners, with a concrete example.";
  $("input-help").textContent = script
    ? "Use 30-720 spoken words, in 2-16 paragraphs of 15-60 words. Narration is preserved; omit stage directions and headings. The director adds titles, diagrams, icons, animations, transitions, and measured sentence timing."
    : "The local model drafts a script, then plans and renders the video. It can take several minutes or fail validation. A reviewed written script gives more predictable results.";
};

async function loadSpaces() {
  state.spaces = await api("/api/workspaces");
  $("projects").replaceChildren();
  for (const w of state.spaces.filter((w) => !w.deleted)) {
    const b = element(
      "button",
      undefined,
      "project-link" + (state.spaceId === w.id ? " active" : ""),
    );
    b.append(
      element("strong", w.name),
      element(
        "small",
        `${w.kind === "series" ? "Series" : "Single video"} - ${w.episodes.length} video${w.episodes.length === 1 ? "" : "s"}`,
      ),
    );
    b.onclick = () => guarded(() => selectSpace(w.id));
    $("projects").append(b);
  }
  renderSpaceBar();
  workspaceOptions();
  if (typeof renderPlaylistSuggestion === "function") renderPlaylistSuggestion();
}
async function selectSpace(id) {
  if(state.reviewDirty&&!confirm("Discard unsaved script edits?"))return;
  state.reviewDirty=false;
  if (state.dirty && !confirm("Discard unsaved changes?")) return;
  state.spaceId = id;
  const w = state.spaces.find((w) => w.id === id);
  if (w?.episodes.length) {
    await openProject(w.episodes[0]);
    return;
  }
  state.project = null;
  state.doc = null;
  state.dirty = false;
  renderWorkspace();
  await loadSpaces();
}
function renderSpaceBar() {
  const w = state.spaces.find((w) => w.id === state.spaceId && !w.deleted);
  $("space-bar").hidden = !w;
  if (!w) return;
  $("space-name").textContent = w.name;
  $("space-kind").textContent =
    w.kind === "series" ? "SERIES / LOCAL PLAYLIST" : "SINGLE VIDEO";
  $("space-description").textContent =
    `${w.theme} theme - ${w.audience} - ${w.brand}`;
  $("episodes").replaceChildren();
  w.videos.forEach((p, i) => {
    const row = element("div", undefined, "episode-row");
    const b = element("button", `${i + 1}. ${p.title}`, "text-button");
    b.onclick = () =>
      guarded(async () => {
        if (state.dirty && !confirm("Discard unsaved changes?")) return;
        await openProject(p.id);
      });
    row.append(b, element("span", p.status, "episode-status"));
    if (w.kind === "series")
      for (const [delta, label] of [
        [-1, "\u2191"],
        [1, "\u2193"],
      ]) {
        const move = element("button", label, "icon-button episode-move");
        move.dataset.edge = String(
          i + delta < 0 || i + delta >= w.episodes.length,
        );
        move.setAttribute(
          "aria-label",
          `Move episode ${i + 1} ${delta < 0 ? "up" : "down"}`,
        );
        move.disabled =
          state.busy ||
          state.pending ||
          i + delta < 0 ||
          i + delta >= w.episodes.length;
        move.onclick = () =>
          guarded(async () => {
            const episodes = [...w.episodes];
            [episodes[i], episodes[i + delta]] = [
              episodes[i + delta],
              episodes[i],
            ];
            await api(`/api/workspaces/${w.id}/reorder`, { episodes });
            await loadSpaces();
          });
        row.append(move);
      }
    $("episodes").append(row);
  });
}
function workspaceOptions() {
  for (const selId of ["new-workspace", "studio-workspace"]) {
    const el = $(selId);
    if (!el) continue;
    el.replaceChildren();
    const auto = element("option", "New single-video workspace");
    auto.value = "";
    el.append(auto);
    for (const w of state.spaces.filter(
      (w) => !w.deleted && (w.kind === "series" || !w.episodes.length),
    )) {
      const o = element("option", w.name);
      o.value = w.id;
      el.append(o);
    }
    if ([...el.options].some((o) => o.value === state.spaceId))
      el.value = state.spaceId;
  }
}
function spaceDialog(w) {
  state.editingSpace = w?.id || null;
  $("space-dialog-title").textContent = w
    ? "Workspace settings"
    : "New workspace";
  for (const [id, key, fallback] of [
    ["space-title", "name", ""],
    ["space-type", "kind", "single"],
    ["space-theme", "theme", "ocean"],
    ["space-brand", "brand", "VISUALFORGE / LEARN"],
    ["space-audience", "audience", "beginners"],
  ])
    $(id).value = w?.[key] ?? fallback;

  $("space-topics").value=(w?.topics||[]).join("\n");
  updateTopicChoices(w?.current_topic||"");
  // Existing workspaces keep their stored voice; new ones start with the recommended voice.
  const voices = $("space-voice");
  voices.replaceChildren(...(state.voices || []).map((v) => {
    const option = element("option", `${v.name} - ${v.description}`);
    option.value = v.id;
    return option;
  }));
  voices.value = w?.voice || state.recommendedVoice || "af_heart";
  // Show each workspace's real setting; new workspaces start with both bookends on.
  $("space-intro").checked = w ? w.show_intro === true : true;
  $("space-outro").checked = w ? w.show_outro === true : true;
  $("space-music").checked = w ? w.music === true : false;
  $("space-voice-audio").pause();
  let swatch = $("theme-swatch");
  if (!swatch) {
    const label = document.querySelector('label[for="space-theme"]');
    if (label) {
      label.style.display = "flex";
      label.style.alignItems = "center";
      label.style.gap = "10px";

      swatch = element("div");
      swatch.id = "theme-swatch";
      swatch.style.width = "28px";
      swatch.style.height = "28px";
      swatch.style.borderRadius = "50%";
      swatch.style.display = "inline-flex";
      swatch.style.justifyContent = "center";
      swatch.style.alignItems = "center";

      const inner = element("div");
      inner.id = "theme-swatch-inner";
      inner.style.width = "14px";
      inner.style.height = "14px";
      inner.style.borderRadius = "50%";
      swatch.append(inner);
      label.append(swatch);

      if ($("space-theme")) {
        $("space-theme").addEventListener("change", () => {
          const themes = {
            ocean: { bg: "#0b1825", fill: "#75e5cd" },
            forest: { bg: "#11251e", fill: "#b9e28c" },
            sunset: { bg: "#261d2e", fill: "#ffb18f" },
          };
          const t = themes[$("space-theme").value] || themes.ocean;
          swatch.style.backgroundColor = t.bg;
          inner.style.backgroundColor = t.fill;
        });
      }
    }
  }
  if ($("space-theme")) $("space-theme").dispatchEvent(new Event("change"));

  $("space-dialog").showModal();
  $("space-title").focus();
}
$("new-space").onclick = () => spaceDialog();
$("edit-space").onclick = () =>
  spaceDialog(state.spaces.find((w) => w.id === state.spaceId));
$("close-space").onclick = () => { $("space-voice-audio").pause(); $("space-dialog").close(); };
$("space-voice-play").onclick = async () => {
  const audio = $("space-voice-audio"), button = $("space-voice-play");
  if (!audio.paused) { audio.pause(); return; }
  // The first listen synthesizes a short local sample; later listens reuse it.
  button.textContent = "Preparing…"; button.disabled = true;
  audio.src = `/api/voice-sample/${$("space-voice").value}`;
  try { await audio.play(); button.textContent = "Stop"; }
  catch (error) { button.textContent = "Listen"; message("Could not play the voice sample. " + error.message); }
  finally { button.disabled = false; }
};
$("space-voice-audio").onpause = () => { $("space-voice-play").textContent = "Listen"; };
$("space-voice-audio").onended = () => { $("space-voice-play").textContent = "Listen"; };
$("space-voice").onchange = () => $("space-voice-audio").pause();
$("space-form").onsubmit = (e) => {
  e.preventDefault();
  guarded(async () => {
    await save();
    const data = {
      name: $("space-title").value,
      kind: $("space-type").value,
      theme: $("space-theme").value,
      brand: $("space-brand").value,
      audience: $("space-audience").value,
      topics: $("space-topics").value.split(/\r?\n/).map(t=>t.trim()).filter(Boolean),
      current_topic: $("space-current-topic").value,
      voice: $("space-voice").value,
      show_intro: $("space-intro").checked,
      show_outro: $("space-outro").checked,
      music: $("space-music").checked,
    };
    const w = await api(
      state.editingSpace
        ? `/api/workspaces/${state.editingSpace}/save`
        : "/api/workspaces",
      data,
    );
    const wasEditing = state.editingSpace;
    state.spaceId = w.id;
    $("space-dialog").close();
    await loadSpaces();
    if (state.project?.workspace?.id === w.id && !state.dirty)
      await openProject(state.project.id, false);
    else if (!wasEditing && !state.dirty) {
      state.project = null;
      state.doc = null;
      renderWorkspace();
    }
  });
};
$("duplicate-space").onclick = () =>
  guarded(async () => {
    await save();
    const w = await api(`/api/workspaces/${state.spaceId}/duplicate`, {});
    await loadSpaces();
    await selectSpace(w.id);
  });
$("trash-space").onclick = () =>
  guarded(async () => {
    await save();
    await api(`/api/workspaces/${state.spaceId}/trash`, {});
    state.spaceId = null;
    state.project = null;
    state.doc = null;
    state.dirty = false;
    renderWorkspace();
    await loadSpaces();
    message("Workspace moved to Trash. You can restore it at any time.");
  });
async function showTrash() {
  await loadSpaces();
  $("trash-list").replaceChildren();
  for (const w of state.spaces.filter((w) => w.deleted)) {
    const row = element("div", undefined, "episode-row");
    const restore = element("button", "Restore", "secondary");
    restore.onclick = () =>
      guarded(async () => {
        await api(`/api/workspaces/${w.id}/restore`, {});
        await showTrash();
      });
    const remove=element('button','Delete permanently','danger');
    remove.onclick=()=>guarded(async()=>{if(prompt(`Permanently delete workspace "${w.name}" and its ${w.episodes.length} videos? This cannot be undone. Shared models and narration caches are retained. Type DELETE to confirm.`)!=='DELETE')return;await api(`/api/workspaces/${w.id}/delete`,{confirmation:'DELETE'});if(state.project?.workspace?.id===w.id){state.project=null;state.doc=null;state.dirty=false;localStorage.removeItem('visualforge.active');renderWorkspace();}await showTrash();});
    row.append(element("span", w.name), restore,remove);
    $("trash-list").append(row);
  }
  if (!$("trash-list").children.length)
    $("trash-list").append(element("p", "Trash is empty."));
  if (!$("trash-dialog").open) $("trash-dialog").showModal();
}
$("show-trash").onclick = () => guarded(showTrash);
$("close-trash").onclick = () => $("trash-dialog").close();
$("composition").onchange = () => {
  scene().visual.variant = Number($("composition").value);
  dirty();
};
$("replan").onclick = () => guarded(() => task("replan", state.selected));
$("draft-render").onclick = () => guarded(() => task("render_draft"));
function renderDraftMedia() {
  const url = !state.dirty ? state.project?.draft_url : null;
  $("draft-result").hidden = !url;
  if (url) {
    if ($("draft-video").getAttribute("src") !== url)
      $("draft-video").src = url;
    $("draft-download").href = url;
  } else {
    $("draft-video").pause();
    $("draft-video").removeAttribute("src");
  }
  const d = state.project?.duration;
  $("duration-note").textContent = state.dirty
    ? "Save to refresh duration estimate."
    : d
      ? `${d.measured_seconds !== null ? "Measured" : "Estimated"} runtime: ${Math.round(d.measured_seconds ?? d.estimated_seconds)}s${d.target_seconds ? " - target " + d.target_seconds + "s" : ""}${d.outside_target ? " - Outside target: shorten or expand narration before final export." : ""}`
      : "";
}

const originalModeChange = $("input-mode").onchange;
$("input-mode").onchange = () => {
  originalModeChange();
  const long = $("input-mode").value === "long";
  $("new-profile").hidden = long;
  document.querySelector('label[for="new-profile"]').hidden = long;
  $("new-duration").replaceChildren();
  for (const value of long ? [7, 10, 15, 20, 30] : [0.5, 1, 2, 3]) {
    const o = element(
      "option",
      value === 0.5 ? "30 seconds" : value + " minutes",
    );
    o.value = value;
    $("new-duration").append(o);
  }
  $("create-submit").textContent = long
    ? "Create chapter outline"
    : "Generate video";
  if (long)
    $("input-help").textContent =
      "First review the chapter outline and scripts. Then measure narration, preview chapters, and export the complete video. Long jobs save completed chapters for retry.";
};
function lockLongControls() {
  document
    .querySelectorAll(
      "#long-workspace button, #long-workspace input, #long-workspace textarea",
    )
    .forEach(
      (e) =>
        (e.disabled =
          state.busy || state.pending || e.dataset.blocked === "true"),
    );
}
async function saveLong(extra = {}) {
  const payload = {
    revision: state.project.revision,
    ...(state.dirty ? state.longDraft : {}),
    ...extra,
  };
  await api(`/api/projects/${state.project.id}/long-save`, payload);
  state.dirty = false;
  await openProject(state.project.id, false);
}
async function longTask(action, uid) {
  await save();
  await api(`/api/projects/${state.project.id}/task`, {
    revision: state.project.revision,
    action,
    uid,
    instructions:
      state.boardInstructions || "Make the explanation concrete and concise.",
  });
  state.busy = true;
  await poll();
}
function renderLongVideo() {
  const box = $("long-workspace");
  box.replaceChildren();
  const p = state.project;
  const tab = state.longTab || "outline";
  state.longDraft =
    tab === "outline"
      ? { chapters: clone(p.long_video.chapters) }
      : tab === "storyboard"
        ? {
            documents: Object.fromEntries(
              p.chapter_details
                .filter((c) => c.document)
                .map((c) => [c.id, clone(c.document)]),
            ),
          }
        : {
            scripts: Object.fromEntries(
              p.chapter_details.map((c) => [c.id, c.script]),
            ),
          };
  box.append(
    element("div", "CHAPTER WORKFLOW", "eyebrow"),
    element("h1", p.topic),
  );
  const d = p.long_duration;
  box.append(
    element(
      "p",
      `Target: ${d.target_seconds / 60} minutes | ${d.measured_seconds === null ? "Narration not fully measured" : Math.round(d.measured_seconds) + " seconds measured"} | Review facts before publishing.`,
      "helper",
    ),
  );
  const controls = element("div", undefined, "long-actions");
  function button(text, fn, blocked = false) {
    const b = element("button", text, "secondary");
    b.dataset.blocked = String(blocked);
    b.onclick = () => guarded(fn);
    controls.append(b);
    return b;
  }
  for (const name of ["outline", "script", "storyboard"])
    button(
      name === "outline"
        ? "1. Review outline"
        : name === "script"
          ? "2. Review scripts"
          : "3. Storyboard",
      async () => {
        await save();
        state.longTab = name;
        renderLongVideo();
        lockControls();
      },
    );
  button("Save edits", () => saveLong());
  if (tab === "outline") {
    button(
      "Approve outline",
      () => saveLong({ approve_outline: true }),
      !p.chapter_details.length,
    );
    button(
      "Generate / resume scripts",
      () => longTask("long_scripts"),
      !p.outline_approved,
    );
  } else {
    button(
      "Plan visuals from script",
      () => longTask("long_visuals"),
      p.chapter_details.some((c) => !c.script),
    );
    button(
      "Measure narration",
      () => longTask("long_audio"),
      p.chapter_details.some((c) => !c.script),
    );
    button(
      "Approve storyboard for export",
      () => saveLong({ approve_script: true }),
      p.chapter_details.some((c) => !c.script),
    );
    button(
      "Preview chapters + 720p video",
      () => longTask("long_render_draft"),
      !p.script_approved,
    );
    button(
      "Export 1080p video",
      () => longTask("long_render"),
      !p.script_approved,
    );
  }
  box.append(
    controls,
    element(
      "p",
      p.script_approved
        ? "Scripts approved for rendering."
        : p.outline_approved
          ? "Outline approved. Generate, edit, and approve scripts before rendering."
          : "Review the outline and approve it before generating narration scripts.",
      "helper",
    ),
  );
  if (!p.chapter_details.length) {
    button("Retry outline", () => longTask("long_outline"));
    box.append(
      element(
        "p",
        "Your outline is being planned. Completed work stays saved if a task fails.",
      ),
    );
  }
  if (tab === "storyboard") {
    renderChapterStoryboard(box, p);
    return;
  }
  p.chapter_details.forEach((c, i) => {
    const card = element("article", undefined, "chapter-card");
    card.append(element("h2", `${i + 1}. ${c.title}`));
    if (tab === "outline")
      for (const [field, label, max] of [
        ["title", "Chapter title", 100],
        ["focus", "Teaching focus", 300],
        ["visual_goal", "Visual approach", 160],
        ["seconds", "Target seconds", 180],
      ]) {
        const l = element("label", label),
          input = element(field === "seconds" ? "input" : "textarea");
        input.value = c[field];
        input.setAttribute("aria-label", `Chapter ${i + 1} ${label}`);
        if (field === "seconds") {
          input.type = "number";
          input.min = 30;
          input.max = 180;
        } else {
          input.rows = field === "focus" ? 3 : 2;
          input.maxLength = max;
        }
        input.oninput = () => {
          state.longDraft.chapters[i][field] =
            field === "seconds" ? Number(input.value) : input.value;
          state.dirty = true;
          lockControls();
        };
        l.append(input);
        card.append(l);
      }
    else {
      const l = element(
          "label",
          "Narration - one teaching scene per paragraph",
        ),
        t = element("textarea");
      t.rows = 12;
      t.maxLength = 16000;
      t.value = c.script;
      t.setAttribute("aria-label", `Chapter ${i + 1} narration`);
      t.oninput = () => {
        state.longDraft.scripts[c.id] = t.value;
        state.dirty = true;
        lockControls();
      };
      l.append(t);
      card.append(l);
      const measured = c.duration?.measured_seconds;
      card.append(
        element(
          "p",
          `Target ${c.seconds}s | ${measured === null || measured === undefined ? "Measure narration to check timing" : measured + "s measured"} | Visuals: ${[...new Set(c.layouts)].join(", ") || "pending"}`,
          "helper",
        ),
      );
      if (
        measured &&
        Math.abs(measured - c.seconds) > Math.max(5, c.seconds * 0.1)
      ) {
        card.append(
          element(
            "p",
            "Outside the chapter target. You can edit the script or request a duration rewrite. Re-measure and approve the result.",
            "quality-note",
          ),
        );
        const b = element(
          "button",
          measured < c.seconds
            ? "Expand this chapter to target"
            : "Shorten this chapter to target",
          "secondary",
        );
        b.onclick = () => guarded(() => longTask("long_adjust", c.id));
        card.append(b);
      }
      for (const issue of c.quality?.issues || [])
        card.append(element("p", issue.message, "quality-note"));
      if (c.preview_url) {
        const v = element("video");
        v.controls = true;
        v.preload = "metadata";
        v.src = c.preview_url;
        card.append(v);
      }
    }
    box.append(card);
  });
  for (const [url, label] of [
    [p.draft_url, "Download full 720p draft"],
    [p.video_url, "Download full 1080p video"],
  ])
    if (url) {
      const v = element("video");
      v.controls = true;
      v.preload = "metadata";
      v.src = url;
      const a = element("a", label, "secondary");
      a.href = url;
      a.download = "visualforge.mp4";
      box.append(v, a);
    }
  lockLongControls();
}


function updateTopicChoices(current=''){
  const select=$('space-current-topic');select.replaceChildren();const empty=element('option','Start at the first topic');empty.value='';select.append(empty);
  for(const title of $('space-topics').value.split(/\r?\n/).map(t=>t.trim()).filter(Boolean)){const o=element('option',title);o.value=title;select.append(o);}
  select.value=current;
}
$('space-topics').oninput=()=>updateTopicChoices($('space-current-topic').value);
$('playlist-preset').onclick=()=>{
  $('space-title').value='Generative AI Visualized';$('space-type').value='series';
  $('space-topics').value=['What is Generative AI?','How Large Language Models Work','Tokens and Context Windows','Embeddings','Vector Databases','RAG','Prompt Engineering','Fine-Tuning','Tool Calling','AI Agents','MCP','Multimodal AI','Guardrails and AI Safety','Build a RAG Application','Build an AI Agent'].join('\n');updateTopicChoices();
};
