"""Estimated word budgets before speech, measured runtime after speech."""
import math
from backend.schemas.video_schema import words


def word_budget(minutes, scenes):
    # Reserve the existing half-second scene pauses; estimate 135 spoken words/minute.
    target=max(15*scenes, round((minutes*60-scenes*.5)*135/60))
    per=max(15,min(55,round(target/scenes)))
    return max(15,round(per*.85)), min(60,max(18,round(per*1.2)))


def duration_report(document, audio, target=None):
    scenes=document['scenes']
    estimated=sum(len(words(s['narration'])) for s in scenes)/135*60+len(scenes)*.5
    measured=sum(math.ceil((audio[s['uid']]['duration']+.5)*30)/30 for s in scenes) if all(s['uid'] in audio for s in scenes) else None
    seconds=measured if measured is not None else estimated
    return {'estimated_seconds':round(estimated,2), 'measured_seconds':round(measured,2) if measured is not None else None,
            'target_seconds':target, 'outside_target':bool(target and abs(seconds-target)>max(5,target*.15)),
            'words':sum(len(words(s['narration'])) for s in scenes)}

