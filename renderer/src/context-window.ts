import type {Scene} from './types.ts';

/** Require both a context explanation and explicitly named content categories. */
export function isContextWindow(scene:Scene) {
  const v=scene.visual;
  return v?.kind==='components' && v.items.length>=2 &&
    /\b(context|working space|container)\b/i.test(scene.narration) &&
    /\b(includes?|contains?|receives?|consumes?|space|capacity|shared|fits?)\b/i.test(scene.narration) &&
    v.items.every(label=>/^(system instructions|conversation history|previous messages|previous conversation|current prompt|latest prompt|input tokens|input|retrieved documents|documents|tool results|output tokens|generated response|response|output)$/i.test(label.trim()));
}

export function contextCues(scene:Scene) {
  // Items mentioned in one sentence appear together, not at invented word times.
  return scene.visual!.items.map((_,i)=>scene.visual!.revealAt?.[i]??0);
}
