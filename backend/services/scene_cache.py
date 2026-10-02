"""Cache frame ranges in their full composition context; mux narration only once."""
import json
import math
import time
from pathlib import Path
import subprocess
from backend.services.run_state import fingerprint, file_hash
from backend.services.script_generator import write_json_atomic
from backend.services.process_runner import execute, node_executable
from backend.services.render_assets import RENDER_CONCURRENCY


def segments(data, timeline, version, profile):
    rows=timeline['scenes']; spans=[]
    if timeline['introFrames']:spans.append(('intro',0,timeline['introFrames'],[]))
    for i,row in enumerate(rows):
        spans.append((str(row['scene']['id']),row['from'],row['durationInFrames'],[r['scene'] for r in rows[max(0,i-1):i+2]]))
    if timeline['outroFrames']:spans.append(('outro',timeline['outroFrom'],timeline['outroFrames'],[rows[-1]['scene']]))
    return [{'id':uid,'from':start,'frames':count,'key':fingerprint(['scene-cache-v1',version,profile,data.get('title'),data.get('style'),start,count,neighbors])} for uid,start,count,neighbors in spans]


def intact(folder, key):
    try:
        record=json.loads((folder/f'{key}.json').read_text(encoding='utf-8'))
        clip=folder/f'{key}.mp4'
        return record if clip.is_file() and record['sha256']==file_hash(clip) else None
    except (OSError,ValueError,KeyError):return None


def assemble_audio(root, data, timeline, output):
    import numpy as np
    import soundfile as sf
    rate=sf.info(root/'renderer/public'/data['scenes'][0]['audio']).samplerate
    cursor=0
    with sf.SoundFile(output,'w',samplerate=rate,channels=1,subtype='PCM_16',format='WAV') as dest:
        def silence(samples):
            while samples>0:
                size=min(samples,rate*10);dest.write(np.zeros(size,dtype='float32'));samples-=size
        for row in timeline['scenes']:
            start=round(row['from']/30*rate)
            silence(start-cursor);cursor=start
            with sf.SoundFile(root/'renderer/public'/row['scene']['audio']) as source:
                if source.samplerate!=rate or source.channels!=1:raise ValueError('Narration must use matching mono sample rates')
                for block in source.blocks(blocksize=rate*10,dtype='float32'):
                    dest.write(block);cursor+=len(block)
        silence(round(timeline['durationInFrames']/30*rate)-cursor)
    if data.get('style',{}).get('music'):
        from backend.services.music import mix
        voice,_=sf.read(output,dtype='float64')
        sf.write(output,mix(voice,rate),rate,subtype='PCM_16',format='WAV')


def render_cached(jobs, project, data, props, pending, profile, render):
    started=time.monotonic();root=jobs.root;folder=jobs.store.folder(project['id'])
    cache=folder/'scene-cache';cache.mkdir(exist_ok=True)
    timeline=json.loads(subprocess.check_output([node_executable(),'--experimental-strip-types',str(root/'renderer/scripts/timeline.ts'),str(props)],cwd=root))
    plan=segments(data,timeline,jobs.version,profile);built=[];reused=[]
    for index,part in enumerate(plan):
        if jobs.cancel.is_set():raise InterruptedError('Cancelled; completed scene clips are cached.')
        key=part['key'];clip=cache/f'{key}.mp4'
        jobs.state.update(scene_index=index+1,scene_total=len(plan),message=f"Scene clip {index+1}/{len(plan)}; {len(reused)} reused")
        if intact(cache,key):reused.append(part['id']);continue
        temporary=cache/f'{key}.pending.mp4'
        render(['render','VisualForgeVideo',temporary,f'--props={props}',f"--frames={part['from']}-{part['from']+part['frames']-1}",'--muted',f'--concurrency={RENDER_CONCURRENCY}',*(['--scale=0.6666666666666666'] if profile=='draft' else [])],'render')
        from backend.services.media_tools import ffmpeg as ffmpeg_tool, ffprobe
        probe=json.loads(subprocess.check_output([str(ffprobe(root)),'-v','error','-show_streams','-of','json',str(temporary)]))
        video=next(s for s in probe['streams'] if s['codec_type']=='video')
        if int(video['nb_frames'])!=part['frames']:raise ValueError('Cached scene has the wrong number of frames')
        if video['codec_name']!='h264' or video['r_frame_rate']!='30/1' or (video['width'],video['height'])!=((1280,720) if profile=='draft' else (1920,1080)):
            raise ValueError('Cached scene has an unexpected render format')
        execute([ffmpeg_tool(root),'-v','error','-xerror','-i',temporary,'-c:v','rawvideo','-f','null','-'],cwd=cache,log=folder/'logs/clip-validation.log',cancel_event=jobs.cancel)
        temporary.replace(clip)
        write_json_atomic(cache/f'{key}.json',{'sha256':file_hash(clip),'frames':part['frames']})
        built.append(part['id'])
    listing=cache/'concat.txt'
    listing.write_text('\n'.join(f"file '{part['key']}.mp4'" for part in plan),encoding='utf-8')
    audio=cache/'narration.wav';assemble_audio(root,data,timeline,audio)
    jobs.state.update(phase='assemble',message='Assembling scene clips with continuous narration')
    from backend.services.media_tools import ffmpeg as ffmpeg_tool
    ffmpeg=ffmpeg_tool(root)
    execute([ffmpeg,'-y','-v','error','-f','concat','-safe','1','-i',listing,'-i',audio,'-map','0:v:0','-map','1:a:0','-c:v','copy','-c:a','libmp3lame','-b:a','192k','-ar','48000','-t',str(timeline['durationInFrames']/30),'-movflags','+faststart',pending],cwd=cache,log=folder/'logs/assemble.log',cancel_event=jobs.cancel)
    metrics={'rendered':built,'reused':reused,'seconds':round(time.monotonic()-started,2),'segments':len(plan),'profile':profile}
    jobs.state['scene_cache']=metrics
    write_json_atomic(folder/'scene-cache-report.json',metrics)
    return timeline


def thumbnails(jobs,project,data,final,profile):
    folder=jobs.store.folder(project['id']);offset=90 if data.get('style',{}).get('showIntro') else 0
    by_id={i+1:s['uid'] for i,s in enumerate(project['document']['scenes'])}
    for scene in data['scenes']:
        uid=by_id[scene['id']];key=jobs.output_key(project,uid,'draft')
        current=jobs.store.load(project['id'])
        at=(offset+min(math.floor(scene['duration']*30),math.floor(scene['duration']*15)))/30
        if not jobs.artifact_ready(current,current.get('previews',{}).get(uid),uid):
            output=folder/f'preview-{uid}.png'
            from backend.services.media_tools import ffmpeg as ffmpeg_tool
            execute([ffmpeg_tool(jobs.root),'-y','-v','error','-ss',str(at),'-i',final,'-frames:v','1',output],cwd=folder,log=folder/'logs/thumbnails.log',cancel_event=jobs.cancel)
            jobs.store.update_artifact(project['id'],'preview',{'key':key,'file':output.name,'sha256':file_hash(output),'profile':'draft','styled':True},uid)
        offset+=math.ceil((scene['duration']+.5)*30)
