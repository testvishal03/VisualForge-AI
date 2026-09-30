# Topic-aware visual actions

The visual director chooses a bounded diagram family for each illustrated scene: flow, split, mapping, comparison, context window, or network. Object labels come from cited narration sentences or a validated authored choreography. One action record per sentence is bound to measured Kokoro narration timings, and the Remotion renderer rejects mistimed or unsupported action data. Existing dedicated worked examples, charts, and code scenes remain separate.

For the Tokens and Context Windows project, the consecutive test segment selects flow (text input), split (types of token pieces), the real-tokenizer example, mapping (identifiers and representations), and comparison (text that consumes different space). A tokenizer is displayed as a tool beside the split diagram, not as a type of token. Generic mapping uses a neutral link rather than claiming an unsupported direction. Connections route around labels, and camera framing remains bounded.

The studio's episode review lists the action at each narration-timed shot. It flags a repeated diagram family, repeated action through a long scene, and dense labels. Identical labels can carry between adjacent illustrated scenes. These are editorial checks, not a factual or aesthetic guarantee for arbitrary topics.

Validation: 195 backend tests, 24 renderer tests, TypeScript typecheck, and JavaScript syntax check passed. The five-scene local preview is rendered and checked with full-media validation and frame inspection. The source script stays at revision 3, unapproved.
