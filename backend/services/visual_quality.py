"""Which rule-directed scenes would gain most from the AI planner, for videos too long to plan fully.

Rule-based choreography labels a scene with phrases picked from its narration. Sometimes those
are weak: a lone verb or adjective ("built", "simplest"), a vague noun ("smarter trick", "tiny
bit"), or a cut verb phrase ("embeddings don't"). Sometimes the narration names a stronger
concept the rules skipped ("nearest neighbor search", "ANN"). Scenes are scored on both, so a
limited planning budget goes to the scenes where viewers would notice the difference.
"""
import re

VAGUE = set('''trick bit bits ones one way ways thing things lot lots kind part parts stuff point points idea ideas
something everything anything example examples case cases area areas option options needs side top bottom'''.split())
LOOSE = set('''simplest single build built make made use used using get got need needs choosing picking deciding
look looks recap don't doesn't isn't aren't can't won't designed around connects connected stands leave'''.split())
# Scenes drawn by a fixed diagram, an explainer or a title card are not candidates.
PLANNABLE = {'explanation', 'example', 'relationship', 'analogy'}


def weak_label(label):
    words = label.casefold().replace('’', "'").split()
    if not words:
        return True
    if any(w in LOOSE for w in words) or words[-1] in VAGUE:
        return True
    # A single lowercase word ending like a verb or adjective form ("built", "fastest", "running").
    return len(words) == 1 and label[:1].islower() and re.search(r'(?:ed|est|ing|ly)$', words[0]) is not None


def strong_option(option):
    words = option.split()
    if re.fullmatch(r'[A-Z]{2,6}', option):
        return True
    return 2 <= len(words) <= 4 and not any(w.casefold() in VAGUE | LOOSE for w in words)


def score(scene):
    """0 when the rule visual is fine; higher when its labels are weak or miss what the narration names."""
    if scene['visual'].get('kind') not in PLANNABLE:
        return 0.0
    return label_score(scene, scene['visual'])


def label_score(scene, visual):
    """How weak the labels a visual would show are, for any kind of visual (lower is better)."""
    from backend.services.choreography import compile_scene
    from backend.services.director import sentences
    from backend.services.semantic_director import concept_options
    labels = [o['label'] for o in (compile_scene(scene, visual) or {}).get('objects', [])] or list(visual.get('items') or [])
    used = {l.casefold() for l in labels}
    options = [o for part in sentences(scene['narration']) for o in concept_options(part)]
    missed = [o for o in dict.fromkeys(options) if strong_option(o) and o.casefold() not in used
              and not any(o.casefold() in u or u in o.casefold() for u in used)]
    bad = sum(weak_label(l) for l in labels)
    # One weak label is already visible on screen, so each counts in full, not as a share.
    value = (min(3, bad) * .5 if labels else 1.0) + min(2, len(missed)) * .25
    return round(value, 3)


def weak_scenes(document, limit):
    """Up to `limit` scene numbers (1-based) worth planning, worst first; scenes scoring 0 are never chosen."""
    from backend.services.explainers import plan as plan_explainer
    ranked = []
    for number, scene in enumerate(document['scenes'], 1):
        if scene['visual'].get('worked') or plan_explainer(scene):
            continue
        value = score(scene)
        if value >= .5:
            ranked.append((-value, number))
    return [number for _, number in sorted(ranked)[:limit]]
