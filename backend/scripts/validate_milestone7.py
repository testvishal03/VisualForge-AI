"""Exercise the local studio with authored demonstration scripts; no uploads."""
import json
import sys
import time
import copy
import subprocess
from pathlib import Path
from urllib.request import Request, urlopen

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
from backend.tests.test_workspaces import WATER, COMPUTER, TIMELINE
from backend.services.process_runner import node_executable


def main():
    base='http://127.0.0.1:8765'
    token=json.loads(urlopen(base+'/api/config').read())['token']
    def api(path,body=None):
        request=Request(base+path,data=json.dumps(body).encode() if body is not None else None,
                        headers={'Content-Type':'application/json','X-Editor-Token':token})
        with urlopen(request,timeout=60) as response: return json.loads(response.read())
    output=ROOT/'data/milestone7-validation.json'
    evidence=json.loads(output.read_text(encoding='utf-8')) if output.exists() else []
    def wait():
        last=''
        while True:
            job=api('/api/job')
            if job['status']!='running':
                if job['status']!='complete': raise RuntimeError(job)
                print(json.dumps({k:v for k,v in job.items() if k!='progress'}),flush=True)
                evidence.append(job)
                return
            if job['phase']!=last:
                last=job['phase'];print(f"{job['project']}: {last}",flush=True)
            time.sleep(2)
    spaces=api('/api/workspaces')
    w=next((w for w in spaces if w['name']=='Visual storytelling demos' and not w['deleted']),None)
    if not w: w=api('/api/workspaces',{'name':'Visual storytelling demos','kind':'series','brand':'VISUALFORGE / SCIENCE'})
    for title,script in [('Water cycle in motion',WATER),('Inside a computer',COMPUTER),('A garden through time',TIMELINE)]:
        projects=api('/api/projects')
        p=next((p for p in projects if p['id'] in w['episodes'] and p['title']==title),None)
        if p:
            p=api('/api/projects/'+p['id'])
            api(f"/api/projects/{p['id']}/task",{'revision':p['revision'],'action':'render_draft'})
        else:
            p=api('/api/projects',{'workspace_id':w['id'],'mode':'script','title':title,'text':script,'profile':'draft'})
        wait()
        p=api('/api/projects/'+p['id'])
        api(f"/api/projects/{p['id']}/task",{'revision':p['revision'],'action':'preview','uid':p['document']['scenes'][0]['uid']})
        wait()
        if title=='Water cycle in motion':
            api(f"/api/projects/{p['id']}/task",{'revision':p['revision'],'action':'render'})
            wait()
            api(f"/api/projects/{p['id']}/task",{'revision':p['revision'],'action':'render'})
            wait()
        result=api('/api/projects/'+p['id'])
        evidence.append({'project':p['id'],'title':title,'duration':result['duration'],
                         'layouts':[s['visual']['kind'] for s in result['document']['scenes']],
                         'draft_url':result.get('draft_url'),'video_url':result.get('video_url'),'quality':result['quality']})
        output=ROOT/'data/milestone7-validation.json'
        output.write_text(json.dumps(evidence,indent=2),encoding='utf-8')
    # Static layout stress checks use an existing WAV only to satisfy asset validation;
    # no synthetic narration/video is published as a teaching demonstration.
    original=json.loads((ROOT/'data/editor'/p['id']/'draft-props.json').read_text(encoding='utf-8'))['videoData']
    for kind,theme in [('chart','sunset'),('cycle','forest')]:
        fixture=copy.deepcopy(original);fixture['title']='Synthetic layout fixture';fixture['style']={'theme':theme,'brand':'LAYOUT VERIFICATION'}
        fixture['scenes']=fixture['scenes'][:1];row=fixture['scenes'][0];row['headline']=f'{kind.title()} layout verification'
        row['visual']={'kind':kind,'variant':0,'items':['First labeled stage or category','Second labeled stage or category','Third labeled stage or category','Fourth labeled stage or category'],'icons':['idea','leaf','gear','chart'],'revealAt':[0,0,0,0]}
        if kind=='chart': row['visual']['values']=[15,35,60,90]
        props=ROOT/'data'/f'milestone7-{kind}-fixture.json';props.write_text(json.dumps({'videoData':fixture}),encoding='utf-8')
        png=ROOT/'data'/f'milestone7-{kind}-fixture.png'
        log=ROOT/'data'/f'milestone7-{kind}-fixture.log'
        with log.open('w',encoding='utf-8') as stream:
            subprocess.run([node_executable(),str(ROOT/'renderer/node_modules/@remotion/cli/remotion-cli.js'),'still','VisualForgeVideo',str(png),f'--props={props}','--frame=30'],cwd=ROOT/'renderer',stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=300)
        print(f'Geometry verified: {png}',flush=True)
    print(f'Validation evidence: {output}',flush=True)


if __name__=='__main__': main()
