"""Render an isolated Tokens story excerpt without changing the user's episode."""
import copy
import argparse
import json
from pathlib import Path
from types import SimpleNamespace
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))

from backend.services.editor_jobs import EditorJobs
from backend.services.editor_store import EditorStore
from backend.services.script_generator import write_json_atomic


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--resume',help='Resume an isolated preview project after a renderer fix')
    args=parser.parse_args()
    source_id=(ROOT/'data/tokens-director-project.txt').read_text(encoding='utf-8').strip()
    original=json.loads((ROOT/'data/editor'/source_id/'project.json').read_text(encoding='utf-8'))
    selected=[copy.deepcopy(original['document']['scenes'][i-1]) for i in (2,3,7,8)]
    document={'title':'Tokens and Context Windows - Illustrated Story Preview',
              'topic':original['topic'],'scenes':selected}
    store=EditorStore(ROOT/'data/illustrated-story-preview/projects')
    if args.resume:
        project=store.load(args.resume)
        if [s['uid'] for s in project['document']['scenes']] != [s['uid'] for s in selected]:
            raise ValueError('Resume project no longer matches the selected source scenes')
    else:
        project=store.create(original['topic'],document,source={'mode':'script','profile':'draft'})
        project=store.approve_storyboard(project['id'],project['revision'])
    jobs=EditorJobs(ROOT,store)
    jobs.workspaces=SimpleNamespace(style=lambda _: {'theme':'ocean','brand':'VISUALFORGE AI','showIntro':False,'showOutro':False})
    folder=store.folder(project['id'])
    jobs._perform(project,'render_draft',None,'',folder)
    result=store.load(project['id'])
    validation=json.loads((folder/'draft-validation.json').read_text(encoding='utf-8'))
    report={'source_project':source_id,'source_revision':original['revision'],
            'scene_numbers':[2,3,7,8],'preview':str(folder/'draft.mp4'),
            'validation':validation,'cache':jobs.state.get('scene_cache')}
    write_json_atomic(ROOT/'data/illustrated-story-preview/result.json',report)
    print(json.dumps({'preview':report['preview'],'seconds':validation['videoDuration'],
                      'frames':validation['frames'],'cache':report['cache']},indent=2))


if __name__=='__main__':main()
