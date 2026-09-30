import {validateChoreography} from './choreography.ts';
import {validateShots} from './shot-direction.ts';
import {validateVisualActions} from './visual-actions.ts';
import type { Scene, VideoData } from "./types.ts";

import {validateWorkedScene} from './worked-example.ts';
import {validateCodeExample} from './code-example.ts';
import {validateTeaching} from './teaching-plan.ts';
import {validateVisualPlan} from './semantic-motion.ts';
import {validateBeatWords} from './presentation.ts';

export const FPS = 30;
export const SCENE_END_PADDING_SECONDS = 0.5;

/** Validate JSON at the renderer boundary before scheduling any frames. */
export function validateVideoData(value: unknown): asserts value is VideoData {
  if (!value || typeof value !== "object")
    throw new Error("videoData must be an object.");
  const data = value as Partial<VideoData>;
  if (
    data.style &&
    (!["ocean", "forest", "sunset"].includes(data.style.theme) ||
      typeof data.style.brand !== "string" ||
      data.style.brand.length > 48)
  )
    throw new Error("Invalid video style.");
  if (typeof data.title !== "string" || !data.title.trim()) {
    throw new Error("videoData.title must be a non-empty string.");
  }
  if (!Array.isArray(data.scenes) || data.scenes.length === 0) {
    throw new Error("videoData.scenes must contain at least one scene.");
  }
  const text=(value:unknown,limit:number)=>typeof value==='string'&&value.trim().length>0&&value.length<=limit&&!/[\x00-\x1f]/.test(value);
  if(data.style?.nextTopic!==undefined&&!text(data.style.nextTopic,160))throw new Error('Invalid next topic.');
  if(data.style?.agenda!==undefined&&(!Array.isArray(data.style.agenda)||data.style.agenda.length>100||data.style.agenda.some(t=>!text(t,160))))throw new Error('Invalid lesson agenda.');
  for(const flag of [data.style?.showIntro,data.style?.showOutro,data.style?.topicMap])if(flag!==undefined&&typeof flag!=='boolean')throw new Error('Invalid bookend flag.');
  const ids = new Set<number>();
  data.scenes.forEach((scene, index) => {
    const label = `Scene ${index + 1}`;
    if (!scene || !Number.isSafeInteger(scene.id) || ids.has(scene.id)) {
      throw new Error(`${label} must have a unique integer id.`);
    }
    ids.add(scene.id);
    validateTeaching(scene);
    validateVisualPlan(scene);
    validateChoreography(scene);
    validateShots(scene);
    validateVisualActions(scene);
    validateCodeExample(scene);
    if (Array.isArray(scene.beats))
      for (const beat of scene.beats) validateBeatWords(beat, label);
    if (!Number.isFinite(scene.duration) || scene.duration <= 0) {
      throw new Error(
        `${label} duration must be a positive number of seconds.`,
      );
    }
    if (
      typeof scene.headline !== "string" ||
      !scene.headline.trim() ||
      typeof scene.body !== "string"
    ) {
      throw new Error(
        `${label} requires a non-empty headline and a string body.`,
      );
    }
    if (typeof scene.narration !== "string" || !scene.narration.trim()) {
      throw new Error(
        `${label} requires non-empty narration. Run generate:audio after editing data/video.json.`,
      );
    }
    if (
      typeof scene.audio !== "string" ||
      !/^audio\/(?:[a-zA-Z0-9_-]+\/)*scene--?\d+\.wav$/.test(scene.audio)
    ) {
      throw new Error(
        `${label} requires a generated relative audio/.../scene-ID.wav path.`,
      );
    }
    if (scene.visual) {
      validateWorkedScene(scene);
      const compatible: Record<string, string[]> = {
        pipeline: ["process"],
        branching: ["relationship"],
        layers: ["components"],
        contrast: ["comparison"],
        timeline: ["timeline"],
        detail: [
          "process",
          "relationship",
          "components",
          "comparison",
          "timeline",
        ],
      };
      const layout = scene.visual.layout;
      if (
        layout &&
        layout !== "auto" &&
        !compatible[layout]?.includes(scene.visual.kind)
      )
        throw new Error("Incompatible scene composition.");
      if (
        scene.visual.motion !== undefined &&
        !["flow", "assemble", "focus", "reveal"].includes(scene.visual.motion)
      )
        throw new Error("Unknown animation treatment.");
      if (scene.visual.planned !== undefined && scene.visual.planned !== true)
        throw new Error("Invalid semantic planning flag.");
      const { kind, items } = scene.visual;
      if(kind==='code' && (!Array.isArray(scene.visual.codeLines)||scene.visual.codeLines.length<1||scene.visual.codeLines.length>30||scene.visual.codeLines.some(line=>typeof line!=='string'||line.length>100||/[\x00-\x08\x0a-\x1f]/.test(line))||!scene.visual.codeLines.some(line=>line.trim())))throw new Error('Code scenes require authored code lines.');
      if(kind==='stat_card'){
        const values=scene.visual.values??scene.visual.statValues;
        const numbers=(scene.narration.replaceAll(',','').match(/(?<![\w.])-?\d+(?:\.\d+)?(?!\w|\.\d)/g)||[]).map(Number);
        if(!Array.isArray(values)||values.length!==items.length||values.some(v=>!Number.isFinite(v)||!numbers.includes(v)) || (scene.visual.values!==undefined&&scene.visual.statValues!==undefined))throw new Error('Statistic cards require literal narration values.');
      }
      const validKinds = [
        "title",
        "explanation",
        "process",
        "comparison",
        "example",
        "takeaway",
        "relationship",
        "cycle",
        "timeline",
        "components",
        "water_cycle",
        "chart",
        "neural_net",
        "code",
        "stat_card",
        "quote",
        "analogy",
      ];
      if (!validKinds.includes(kind) || !Array.isArray(items)) {
        throw new Error(`${label} has an invalid visual layout.`);
      }
      const count =
        kind === "process"
          ? 3
          : kind === "comparison"
            ? 2
            : kind === "water_cycle"
              ? 4
              : [
                    "relationship",
                    "cycle",
                    "timeline",
                    "components",
                    "chart",
                    "neural_net",
                    "stat_card",
                    "quote",
                    "analogy",
                  ].includes(kind)
                ? items.length
                : 0;
      if (
        [
          "cycle",
          "timeline",
          "components",
          "chart",
          "neural_net",
          "stat_card",
        ].includes(kind) &&
        (count < 2 || count > 4)
      )
        throw new Error("Diagrams require 2–4 labels.");
      if (
        kind === "chart" &&
        (!Array.isArray(scene.visual.values) ||
          scene.visual.values.length !== count ||
          scene.visual.values.some(
            (v) => !Number.isFinite(v) || v < 0 || v > 100,
          ))
      )
        throw new Error("Charts require valid percentages.");
      if (
        scene.visual.variant !== undefined &&
        ![0, 1].includes(scene.visual.variant)
      )
        throw new Error("Unknown composition.");
      if (
        scene.visual.transition !== undefined &&
        !["fade", "slide", "wipe", "zoom"].includes(scene.visual.transition)
      )
        throw new Error("Unknown transition.");
      const icons = [
        "idea",
        "book",
        "database",
        "chip",
        "shield",
        "clock",
        "leaf",
        "people",
        "chart",
        "sun",
        "cloud",
        "water",
        "rain",
        "network",
        "gear",
        "battery",
        "globe",
        "brain",
        "layers",
        "lightning",
        "math",
        "code",
        "atom",
        "filter",
        "token",
        "matrix",
        "magnify",
        "rocket",
        "analog",
      ];
      if (
        scene.visual.icons &&
        (scene.visual.icons.length !== count ||
          scene.visual.icons.some((i) => !icons.includes(i)))
      )
        throw new Error("Invalid diagram icons.");
      if (
        (kind === "relationship" && ![2, 3].includes(count)) ||
        items.length !== count ||
        items.some(
          (item) =>
            typeof item !== "string" ||
            !item.trim() ||
            item.length > (kind === "comparison" ? 180 : 70),
        )
      ) {
        throw new Error(`${label} has invalid visual items.`);
      }
      if (scene.visual.directed && scene.beats) {
        const beats = scene.beats;
        if (
          !Array.isArray(beats) ||
          !beats.length ||
          beats.some(
            (b, i) =>
              typeof b.text !== "string" ||
              !b.text.trim() ||
              !Number.isFinite(b.start) ||
              !Number.isFinite(b.end) ||
              b.start < (i ? beats[i - 1].end : 0) ||
              b.end <= b.start ||
              b.end > scene.duration,
          ) ||
          beats[0].start !== 0 ||
          Math.abs(beats[beats.length - 1].end - scene.duration) > 1 / 24000 ||
          beats
            .map((b) => b.text)
            .join(" ")
            .replace(/\s+/g, " ") !== scene.narration.replace(/\s+/g, " ")
        ) {
          throw new Error(`${label} has invalid measured narration beats.`);
        }
        const reveals = scene.visual.revealAt;
        if (
          !Array.isArray(reveals) ||
          reveals.length !== items.length ||
          reveals.some(
            (t, i) =>
              !Number.isFinite(t) ||
              t < 0 ||
              t >= scene.duration ||
              (i > 0 && t < reveals[i - 1]) ||
              // Sentence starts always qualify; word cues only where words were measured.
              !beats.some((b) => Math.abs(b.start - t) < 1 / 24000 ||
                (!!b.words?.length && t > b.start && t < b.end)),
          )
        ) {
          throw new Error(`${label} has invalid visual reveal timing.`);
        }
      }
    }
  });
}

/** A scene's own frames: its narration plus the silent end padding. */
export function sceneFrames(scene: Scene, fps: number) {
  return Math.ceil((scene.duration + SCENE_END_PADDING_SECONDS) * fps);
}

export function buildTimeline(videoData: VideoData, fps: number) {
  validateVideoData(videoData);
  if (!Number.isFinite(fps) || fps <= 0)
    throw new Error("FPS must be positive.");
  const introFrames=videoData.style?.showIntro?Math.ceil(3*fps):0;
  const outroFrames=videoData.style?.showOutro?Math.ceil(5*fps):0;
  let durationInFrames = introFrames;
  const scenes = videoData.scenes.map((scene: Scene) => {
    const frames = sceneFrames(scene, fps);
    if (!Number.isSafeInteger(frames) || frames < 1) {
      throw new Error(
        `Scene ${scene.id} duration must fit a safe integer frame count.`,
      );
    }
    const scheduled = {
      scene,
      from: durationInFrames,
      durationInFrames: frames,
    };
    durationInFrames += frames;
    if (!Number.isSafeInteger(durationInFrames))
      throw new Error("Total duration is too large.");
    return scheduled;
  });
  const outroFrom=durationInFrames;
  return { scenes, durationInFrames:durationInFrames+outroFrames, introFrames, outroFrames, outroFrom };
}
