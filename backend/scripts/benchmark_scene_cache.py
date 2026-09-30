"""Validate cache assembly using an existing preview, without approving an episode."""
import json
import sys
import threading
from pathlib import Path
from types import SimpleNamespace
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.services.editor_store import EditorStore, renderer_version
from backend.services.scene_cache import render_cached
from backend.services.process_runner import execute,node_executable
from backend.services.script_generator import write_json_atomic
from backend.scripts.validate_render import validate

root=Path(__file__).resolve().parents[2]
data=json.loads((root/'data/editor/8ac669012aac/style-props.json').read_text(encoding='utf-8'))['videoData']
store=EditorStore(root/'data/scene-cache-benchmark')
project=store.create('Scene cache validation')
folder=store.folder(project['id']);props=folder/'props.json';write_json_atomic(props,{'videoData':data})
jobs=SimpleNamespace(root=root,store=store,version=renderer_version(root),state={},cancel=threading.Event())
def render(args,name):
    execute([node_executable(),root/'renderer/node_modules/@remotion/cli/remotion-cli.js',*args],cwd=root/'renderer',log=folder/'render.log',cancel_event=jobs.cancel)
reports=[]
for name in ['first','reused']:
    output=folder/f'{name}.mp4'
    render_cached(jobs,project,data,props,output,'draft',render)
    report=validate(output,props,'draft');reports.append({'cache':jobs.state['scene_cache'],'validation':report})
    print(name,json.dumps(jobs.state['scene_cache']),flush=True)
write_json_atomic(root/'data/scene-cache-benchmark.json',{'folder':str(folder),'runs':reports})
