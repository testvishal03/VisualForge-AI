"""Conservative, source-grounded improvements shared by both visual directors."""
import re

# These endings are clear truncation signals, not a general grammar checker.
DANGLING = set('a an the at by for from in into of on onto to with without and or because although than enough each every some can could will would must should is are was were has have gain gains'.split())


def label_problem(label):
    words = re.findall(r"[\w]+(?:[-'][\w]+)*", label.lower())
    return (not words or label.rstrip().endswith(('...', '\u2026'))
            or words[-1] in DANGLING)


def label_candidates(sentence):
    words = re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", sentence)
    return sorted({label for start in range(len(words))
                   for size in range(1, min(10, len(words)-start)+1)
                   if len(label := ' '.join(words[start:start+size])) <= 60
                   and not label_problem(label)
                   and words[start].lower() not in DANGLING})


def improve_visual(scene, visual, previous=()):
    """Repair generated labels only; never rewrite narration or numeric data."""
    from backend.services.director import sentences, choose_icon
    from backend.services.scene_direction import composition, COMPATIBLE
    result = dict(visual)
    parts = sentences(scene.narration)
    labels = list(result.get('items', []))
    cues = result.get('cues', [])
    used = {label.casefold() for label in labels if not label_problem(label)}
    for i, label in enumerate(labels):
        if not label_problem(label) or i >= len(cues):
            continue
        source = parts[cues[i]]
        candidates = [s for s in label_candidates(source) if s.casefold() not in used]
        original = set(re.findall(r'\w+', label.lower()))
        if candidates:
            # Keep the subject and extend a cut-off action when space allows.
            chosen = max(candidates, key=lambda s: (
                len(original & set(s.lower().split())),
                s.lower().startswith(label.rstrip('. ').lower()), len(s)))
            labels[i] = chosen
            used.add(chosen.casefold())
    result['items'] = labels
    if result.get('icons'):
        result['icons'] = [choose_icon(label) for label in labels]
    if len(previous) >= 2 and all(composition(v) == composition(result) for v in previous[-2:]):
        if result['kind'] in COMPATIBLE['detail']:
            result['layout'] = 'detail' if composition(result) != 'detail' else 'auto'
            result['motion'] = 'focus'
    if 'worked' not in result:
        example = automatic_example(scene.narration)
        if example:
            result['worked'] = example
    return result


def automatic_example(narration):
    """Use an explicitly quoted tokenizer input, never an invented demonstration."""
    from backend.services.director import sentences
    if not re.search(r'\btokeniz(?:er|ation|e|es|ing)\b', narration, re.I):
        return None
    # Numeric segmentation claims can depend on a different tokenizer.
    if re.search(r'\b(?:exactly|into)\s+(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten)\s+tokens', narration, re.I):
        return None
    parts = sentences(narration)
    matches = []
    for i, part in enumerate(parts):
        if not re.search(r'\b(?:input|text|sentence|phrase)\b', part, re.I):
            continue
        for match in re.finditer(r'["\u201c]([^"\u201d\n]{1,80})["\u201d]', part):
            matches.append((i, match[1]))
    if len(matches) != 1:
        return None
    cue, text = matches[0]
    if len(text.split()) > 10:
        return None
    steps = [{'action': 'tokens', 'sentence': cue}]
    for i in range(cue+1, len(parts)):
        if re.search(r'\b(?:token IDs?|identifiers?)\b', parts[i], re.I):
            steps.append({'action': 'ids', 'sentence': i})
            break
    # No automatic completion: authored output claims may disagree with the model.
    return {'input': text, 'label': 'Local tokenizer example', 'steps': steps}
