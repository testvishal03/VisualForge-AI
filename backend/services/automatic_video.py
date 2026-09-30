"""One user action runs the existing resumable stages through validated export."""
import json
from backend.services.script_generator import write_json_atomic
from backend.services.process_runner import python_stage

def perform(jobs,project,folder):
    if not project.get('source',{}).get('automatic'):raise ValueError('This project uses the manual editor workflow.')
    if jobs.cancel.is_set():raise InterruptedError('Cancelled')
    if project['source']['mode']=='prompt' and not project['source'].get('length_plan'):
        source,output=folder/'length-request.json',folder/'length-plan.json'
        write_json_atomic(source,{'topic':project['topic']})
        jobs.state.update(phase='planning-length',log=str(folder/'logs/length.log'),log_offset=0)
        python_stage(jobs.root/'backend/scripts/plan_length.py',[source,output],root=jobs.root,folder=folder,name='length',timeout=600,cancel_event=jobs.cancel)
        plan=json.loads(output.read_text(encoding='utf-8'))
        from backend.scripts.plan_length import LENGTHS
        if type(plan.get('minutes')) not in (int,float) or plan['minutes'] not in LENGTHS:raise ValueError('Invalid automatic duration')
        project['source'].update(minutes=plan['minutes'],length_plan=plan)
        if plan['minutes']>=7:project['long_video']={'chapters':[],'outline_approved':None,'script_approved':None}
        project['revision']+=1
        write_json_atomic(folder/'project.json',project)
    jobs.state['target_minutes']=project['source']['minutes']
    if 'long_video' not in project:
        if project['source'].get('approval_required') and project.get('document'):
            from backend.services.run_state import fingerprint
            if project.get('storyboard_approved') == fingerprint(project['document']):
                return jobs._perform(project,'render_draft' if project['source']['profile']=='draft' else 'render',None,'',folder)
        return jobs._perform(project,'generate',None,'',folder)
    from backend.services.long_video import perform as chapter_task,save
    if not project['long_video']['chapters']:
        chapter_task(jobs,project,'long_outline',None)
    project=jobs.store.load(project['id'])
    # The user selected automatic generation; these are workflow gates, not a claim of human review.
    project=save(jobs.store,project,{'approve_outline':True})
    chapter_task(jobs,project,'long_scripts',None)
    project=jobs.store.load(project['id'])
    if project['source'].get('approval_required'):
        from backend.services.long_video import script_key
        if project['long_video']['script_approved'] != script_key(jobs.store,project):
            jobs.state.update(result_kind='script_review',message='Script ready. Review and approve before generating video.')
            return
    else:
        project=save(jobs.store,project,{'approve_script':True})
    if jobs.cancel.is_set():raise InterruptedError('Cancelled')
    chapter_task(jobs,project,'long_render_draft' if project['source']['profile']=='draft' else 'long_render',None)
