"""Topic-specific diagrams grounded in the sentences being narrated."""
import re


def topic_visual(scene):
    from backend.services.director import sentences, choose_icon
    parts = sentences(scene.narration)
    text = scene.narration

    def find(pattern):
        for cue, part in enumerate(parts):
            match = re.search(pattern, part, re.I)
            if match:
                return match[0], cue
        return None

    def diagram(kind, matches, layout):
        nodes = sorted([m for m in matches if m], key=lambda m:m[1])
        if not 2 <= len(nodes) <= 4:
            return None
        return {'kind':kind, 'layout':layout, 'items':[m[0] for m in nodes],
                'cues':[m[1] for m in nodes], 'icons':[choose_icon(m[0]) for m in nodes],
                'icon':'layers' if kind=='components' else 'token', 'directed':True,
                'motion':'assemble', 'transition':'fade'}

    # Show only categories actually named in this scene. Equal bands are a
    # conceptual inventory, not fabricated token counts or capacity percentages.
    if re.search(r'\b(context|working space|container)\b', text, re.I) and re.search(r'\b(includes?|contains?|receives?|consumes?|space|capacity|shared|fits?)\b', text, re.I):
        categories = [find(p) for p in [r'\bsystem instructions\b', r'\b(?:conversation history|previous messages|previous conversation)\b',
            r'\b(?:current prompt|latest prompt|input tokens|input)\b', r'\b(?:retrieved documents|documents|tool results)\b',
            r'\b(?:output tokens|generated response|response|output)\b']]
        present = [m for m in categories if m]
        if len(present) >= 2:
            present = present[:4]
            return diagram('components', present, 'layers')
    if re.search(r'\btokeniz(?:er|ation)\b', text, re.I) and re.search(r'\b(?:split|break|broken|mapped|convert|flow)\b', text, re.I):
        matches = [find(r'\b(?:input text|text)\b'), find(r'\btokens\b'), find(r'\b(?:token IDs?|numerical IDs?)\b')]
        if all(matches) and [m[1] for m in matches] == sorted(m[1] for m in matches):
            return diagram('process', matches, 'pipeline')
    return None
