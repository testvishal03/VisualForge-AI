"""Group spoken sentences without changing their wording or order."""
import re
from backend.schemas.video_schema import words


def group_paragraphs(paragraphs):
    from backend.services.director import sentences
    atoms, boundaries = [], {}
    for paragraph in paragraphs:
        parts = sentences(paragraph)
        for part in parts:
            if len(words(part)) > 60 or len(part) > 600:
                raise ValueError('One sentence is too long. Split sentences to at most 60 words and 600 characters.')
            atoms.append(part)
        boundaries[len(atoms)] = len(words(paragraph)) >= 20
    # A blank line after a substantial paragraph is an authored teaching break.
    # Short line-by-line scripts instead accumulate into coherent spoken beats.
    n = len(atoms)
    costs = [float('inf')] * (n+1)
    paths = [None] * (n+1)
    costs[0] = 0
    for end in range(1, n+1):
        for start in range(end-1, -1, -1):
            text = ' '.join(atoms[start:end])
            count = len(words(text))
            if count > 60 or len(text) > 600:
                break
            if count < 1 or paths[start] is None and start != 0:
                continue
            cost = 8 + (count-42)**2/90 + (25 if count < 15 else 0)
            cost += sum(35 for boundary, strong in boundaries.items() if strong and start < boundary < end)
            if end in boundaries and boundaries[end]:
                cost -= 12
            if end < n:
                following = atoms[end]
                if re.match(r"(?:now|another important|and that brings|so what|why |let.s|in contrast|remember|to summarize)", following, re.I):
                    cost -= 8
                if re.search(r'[:?]$', atoms[end-1]) or re.match(r'^(?:and |but |those |this |it |each |for example)', following, re.I):
                    cost += 10
            if costs[start]+cost < costs[end]:
                costs[end] = costs[start]+cost
                paths[end] = start
    if paths[n] is None:
        raise ValueError('Cannot group this script into complete 15-60 word scenes. Split long sentences or expand isolated short sections.')
    chunks, end = [], n
    while end:
        start = paths[end]
        chunks.append(' '.join(atoms[start:end]))
        end = start
    return chunks[::-1]
