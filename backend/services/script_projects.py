"""Split long user narration into renderable chapters without changing its text."""
import re
from backend.schemas.video_schema import words
from backend.services.director import script_to_video, build_direction
from backend.services.editor_store import document_from_video
from backend.services.scene_grouping import group_paragraphs
from backend.services.script_generator import write_json_atomic


def create(store, title, text, source):
    paragraphs = [re.sub(r'\s+', ' ', p).strip() for p in re.split(r'\n\s*\n', text) if p.strip()]
    chunks = group_paragraphs(paragraphs)
    source = {**source, 'minutes':len(words(text))/135, 'minimum_seconds':0}
    if len(chunks) <= 100:
        video = script_to_video(title, text)
        return store.create(video.topic, document_from_video(video, build_direction(video)), source=source)
    first = script_to_video(title, '\n\n'.join(chunks[:80]))
    parent = store.create(first.topic, source=source)
    from backend.services.long_video import chapters_store, plan_key
    children = chapters_store(store, parent)
    parent['long_video'] = {'chapters':[], 'outline_approved':None, 'script_approved':None}
    for start in range(0, len(chunks), 80):
        number = start//80+1
        chapter_title = f'{first.title[:95]} - Part {number}'
        narration = '\n\n'.join(chunks[start:start+80])
        video = script_to_video(chapter_title, narration)
        child = children.create(video.topic, document_from_video(video, build_direction(video)),
                                source={'mode':'script','minutes':len(words(narration))/135})
        parent['long_video']['chapters'].append({'id':child['id'], 'title':chapter_title,
            'focus':'Preserve the supplied narration.', 'visual_goal':'Demonstrate each spoken mechanism.',
            'seconds':round(len(words(narration))/135*60)})
    parent['long_video']['outline_approved'] = plan_key(parent)
    write_json_atomic(store.folder(parent['id'])/'project.json', parent)
    return parent
