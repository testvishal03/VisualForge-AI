export type WorkedSpec = {input:string;label:string;steps:{action:'tokens'|'ids'|'process'|'generate';sentence:number}[]};
export type WorkedData = {input:string;tokens:{id:number;piece:string|number[]}[];continuation:string;prefixes:string[];generated_ids:number[];model:{model:string};mode:'raw_completion'};
export type Visual = {
  demo?: import('./code-example').DemoSpec | {kind:'off'};
  worked?: WorkedSpec;
  workedData?: WorkedData;
  kind:
    | "title"
    | "explanation"
    | "process"
    | "comparison"
    | "example"
    | "takeaway"
    | "relationship"
    | "cycle"
    | "timeline"
    | "components"
    | "water_cycle"
    | "chart"
    | "neural_net"
    | "code"
    | "stat_card"
    | "quote"
    | "analogy";
  items: string[];
  directed?: boolean;
  planned?: boolean;
  layout?:
    | "auto"
    | "pipeline"
    | "branching"
    | "layers"
    | "contrast"
    | "timeline"
    | "detail";
  motion?: "flow" | "assemble" | "focus" | "reveal";
  icon?: string;
  icons?: string[];
  variant?: number;
  values?: number[];
  statValues?: number[];
  codeLines?: string[];
  cues?: number[];
  revealAt?: number[];
  transition?: "fade" | "slide" | "wipe" | "zoom";
  shotOverrides?: Record<string,"wide"|"follow"|"detail">;
};

export type Scene = {
  choreography?: import('./choreography').Choreography;
  actions?: import('./visual-actions').VisualActions;
  shots?: {sentence:number;text:string;mode:'wide'|'follow'|'detail';focus:number|null;label:string|null;start:number;end:number}[];
  visualPlan?: {kind:string;title:string;view:'overview'|'detail';carry:string|null;
    objects:string[];steps:{sentence:number;action:string;text:string}[];at:number[];transition:string};
  demonstration?: import('./code-example').CodeExample;
  teaching?: import('./teaching-plan').TeachingPlan;
  id: number;
  /** Actual WAV duration in seconds, before scene end padding. */
  duration: number;
  headline: string;
  body: string;
  narration: string;
  /** Relative to renderer/public. */
  audio: string;
  visual?: Visual;
  beats?: Beat[];
};

/** Scene-relative seconds for one spoken whitespace word. */
export type WordTiming = { text: string; start: number; end: number };

export type Beat = {
  text: string;
  start: number;
  end: number;
  /** "model" comes from Kokoro phoneme durations; "estimated" is letter-weighted. */
  wordTiming?: 'model' | 'estimated';
  words?: WordTiming[];
};

export type VideoData = {
  title: string;
  previewTotal?: number;
  style?: {
    theme: "ocean" | "forest" | "sunset";
    brand: string;
    showIntro?: boolean;
    showOutro?: boolean;
    /** Topic rail and "Up next" bridge between scenes; on unless false. */
    topicMap?: boolean;
    /** Narration voice; part of the style so a voice change invalidates renders. */
    voice?: string;
    /** Next lesson in a series playlist, shown on the outro. */
    nextTopic?: string;
    /** Lesson topics for the intro and outro when they differ from this video's scenes (chapters). */
    agenda?: string[];
  };
  scenes: Scene[];
};

export type VideoProps = { videoData: VideoData };
