"""After an export: a YouTube-ready thumbnail and description built from the measured video.

Everything comes from the validated script and the exact render props: chapter times use
the renderer's own frame arithmetic, so they match the MP4. Nothing is invented; claims in
the description are the narration's own sentences and headlines.
"""
import json
import math
from pathlib import Path
import re

from backend.services.run_state import file_hash
from backend.services.script_generator import write_json_atomic
from backend.tts.kokoro_tts import DEFAULT_VOICE, VOICES

FPS = 30
INTRO_SECONDS, OUTRO_SECONDS, PADDING_SECONDS = 3, 5, .5
# YouTube shows chapters only with at least three, the first at 0:00, each at least ten seconds.
MIN_CHAPTERS, MIN_CHAPTER_SECONDS = 3, 10
STOP = {'a', 'an', 'the', 'and', 'or', 'of', 'to', 'in', 'on', 'for', 'is', 'are', 'how', 'what', 'why', 'with', 'your', 'you', 'do', 'does'}


def scene_seconds(scene):
    """Mirror renderer/src/timeline.ts: ceil((duration + padding) * FPS) frames."""
    return math.ceil((scene['duration'] + PADDING_SECONDS) * FPS) / FPS


def stamp(seconds):
    seconds = int(seconds)
    return f'{seconds // 3600}:{seconds // 60 % 60:02d}:{seconds % 60:02d}' if seconds >= 3600 else f'{seconds // 60}:{seconds % 60:02d}'


def sections(parts, style):
    """(start, title) per section from [(title, seconds)], with bookends folded into neighbours."""
    rows, cursor = [], INTRO_SECONDS if style.get('showIntro') else 0
    for title, seconds in parts:
        rows.append([cursor, title, seconds])
        cursor += seconds
    if rows:
        rows[0][2] += rows[0][0]
        rows[0][0] = 0  # The intro belongs to the first chapter; chapters must start at 0:00.
        if style.get('showOutro'):
            rows[-1][2] += OUTRO_SECONDS
    return rows, cursor + (OUTRO_SECONDS if style.get('showOutro') else 0)


def chapters(rows):
    """Merge sections shorter than YouTube's minimum into their predecessor; None if too few remain."""
    merged = []
    for start, title, seconds in rows:
        if merged and seconds < MIN_CHAPTER_SECONDS:
            merged[-1][2] += seconds
        else:
            merged.append([start, title, seconds])
    if len(merged) > 1 and merged[0][2] < MIN_CHAPTER_SECONDS:
        merged[1] = [0, merged[0][1], merged[0][2] + merged[1][2]]
        merged.pop(0)
    ok = len(merged) >= MIN_CHAPTERS and all(s >= MIN_CHAPTER_SECONDS for _, _, s in merged)
    return [(start, title) for start, title, _ in merged] if ok else None


def first_sentence(text):
    match = re.match(r'(.+?[.!?])(\s|$)', text.strip())
    return (match[1] if match else text.strip())[:300]


def hashtags(topic):
    words = [w for w in re.findall(r"[A-Za-z0-9]+", topic) if w.lower() not in STOP]
    whole = ''.join(w[:1].upper() + w[1:] for w in words)[:40]
    tags = [whole] if whole else []
    tags += [w[:1].upper() + w[1:] for w in words if len(w) > 3 and w[:1].upper() + w[1:] != whole][:2]
    return ' '.join('#' + t for t in [*dict.fromkeys(tags), 'Explained', 'Learning'])


def description(title, topic, scenes, style, parts=None):
    """Plain-text description; `parts` overrides scene sections (chapter videos)."""
    rows, total = sections(parts or [(s['headline'], scene_seconds(s)) for s in scenes], style)
    marks = chapters(rows)
    points = [s for s in scenes if s.get('headline')][:8]
    voice = VOICES.get(style.get('voice', DEFAULT_VOICE), (style.get('voice', 'Kokoro'),))[0]
    lines = [title, '', first_sentence(scenes[0]['narration']) if scenes else topic, '', 'In this video:']
    if parts:
        # Chapter videos summarise by chapter; listing every scene would bury the structure.
        lines += [f'• {name}' for name, _ in parts[:12]]
    else:
        lines += [f"• {s['headline']}" + (f" - {s['body']}" if s.get('body') and s['body'].casefold() != s['headline'].casefold() else '') for s in points]
    if marks:
        lines += ['', 'Chapters:', *[f'{stamp(start)} {name}' for start, name in marks]]
    if scenes and scenes[-1].get('body'):
        lines += ['', f"Key takeaway: {scenes[-1]['body']}"]
    if style.get('nextTopic'):
        lines += ['', f"Next in this series: {style['nextTopic']}"]
    lines += ['', hashtags(topic), '',
              f'Narration is AI-generated (Kokoro "{voice}" voice). Diagrams are illustrative. '
              'Please check facts against reliable sources.']
    return '\n'.join(lines) + '\n', {'seconds': round(total, 3), 'chapters': len(marks) if marks else 0,
                                    'chapters_note': None if marks else 'YouTube needs 3+ chapters of 10s+; this video is too short for chapter markers.'}


def publish(jobs, project, folder: Path, data, render, profile, parts=None):
    """Write thumbnail.png and description.txt next to the export and record them on the project."""
    out = folder/'publish'
    out.mkdir(exist_ok=True)
    props = out/'thumbnail-props.json'
    write_json_atomic(props, {'videoData': data})
    pending, thumbnail = out/'thumbnail.pending.png', out/'thumbnail.png'
    render(['still', 'VisualForgeThumbnail', pending, f'--props={props}'], 'thumbnail')
    pending.replace(thumbnail)
    text, meta = description(data['title'], project.get('topic') or data['title'], data['scenes'], data.get('style', {}), parts)
    notes = out/'description.txt'
    notes.write_text(text, encoding='utf-8')
    record = {'profile': profile, 'thumbnail': {'file': 'publish/thumbnail.png', 'sha256': file_hash(thumbnail)},
              'description': {'file': 'publish/description.txt', 'sha256': file_hash(notes)}, **meta}
    jobs.store.update_artifact(project['id'], 'publish', record)
    return record


def publish_safely(jobs, project, folder, data, render, profile, parts=None):
    """Publishing extras must never cost the user their verified video."""
    try:
        return publish(jobs, project, folder, data, render, profile, parts)
    except Exception as exc:  # noqa: BLE001 - reported, then the finished video is kept
        jobs.state['publish_error'] = f'Thumbnail and description were not created: {exc}'
        (folder/'logs').mkdir(exist_ok=True)
        with (folder/'logs'/'publish.log').open('a', encoding='utf-8') as log:
            log.write(f'{exc!r}\n')
        return None


def present(jobs, project, result):
    """Expose current publishing files: only when intact and made for the export being shown."""
    record = project.get('publish')
    shown = 'draft' if not result.get('video_url') and result.get('draft_url') else 'final'
    result['publish'] = None
    if not record or record.get('profile') != shown or not (result.get('video_url') or result.get('draft_url')):
        return result
    base = jobs.store.folder(project['id']).resolve()
    for kind in ('thumbnail', 'description'):
        target = (base/record[kind]['file']).resolve()
        if not target.is_relative_to(base) or not target.is_file() or file_hash(target) != record[kind]['sha256']:
            return result
    result['publish'] = {'thumbnail_url': f"/media/{project['id']}/thumbnail?v={record['thumbnail']['sha256'][:12]}",
                         'description_url': f"/media/{project['id']}/description?v={record['description']['sha256'][:12]}",
                         'description': (base/record['description']['file']).read_text(encoding='utf-8'),
                         'chapters': record.get('chapters', 0), 'chapters_note': record.get('chapters_note')}
    return result
