"""Explicit script approval and optional expansion for new creator projects."""
from backend.services.run_state import fingerprint


def require_approval(project):
    if project.get('source', {}).get('approval_required'):
        if project.get('storyboard_approved') != fingerprint(project['document']):
            raise ValueError('Review and approve the current script before generating video.')


def expand(jobs, project, folder):
    """Only invoked by the explicit request-an-expanded-draft action."""
    from backend.services.script_generator import write_json_atomic
    from backend.services.long_video import perform, save
    if not project.get('source', {}).get('approval_required'):
        raise ValueError('Expansion is available in the reviewed creator workflow.')
    if project.get('long_video', {}).get('chapters'):
        perform(jobs, project, 'long_audio', None)
        project = jobs.store.load(project['id'])
        project = save(jobs.store, project, {'approve_outline': True})
        for row in project['long_video']['chapters']:
            perform(jobs, project, 'long_adjust', row['id'])
            project = jobs.store.load(project['id'])
    else:
        if not project.get('document'):
            raise ValueError('Prepare the first draft before requesting expansion.')
        write_json_atomic(folder / f"script-before-expansion-{project['revision']}.json", project['document'])
        project['source']['reference_script'] = '\n'.join(s['narration'] for s in project['document']['scenes'])
        project['source']['minutes'] = max(10, min(30, round(project['source'].get('minutes', 10))))
        project['long_video'] = {'chapters': [], 'outline_approved': None, 'script_approved': None}
        project['revision'] += 1
        write_json_atomic(folder / 'project.json', project)
        perform(jobs, project, 'long_outline', None)
        project = save(jobs.store, jobs.store.load(project['id']), {'approve_outline': True})
        perform(jobs, project, 'long_scripts', None)
    jobs.state.update(result_kind='script_review', message='Expanded draft ready. Review the changes and approve again before video generation.')
