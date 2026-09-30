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
  beats?: { text: string; start: number; end: number }[];
};

export type VideoData = {
  title: string;
  previewTotal?: number;
  style?: {
    theme: "ocean" | "forest" | "sunset";
    brand: string;
    showIntro?: boolean;
    showOutro?: boolean;
  };
  scenes: Scene[];
};

export type VideoProps = { videoData: VideoData };
