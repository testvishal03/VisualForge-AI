"""User acceptance advances a playlist; exports alone do not."""
from backend.services.run_state import fingerprint
from backend.services.script_generator import write_json_atomic


def content_key(store, project):
    if 'long_video' in project:
        from backend.services.long_video import script_key
        return script_key(store, project)
    return fingerprint(project.get('document'))


def accepted(store, project):
    record = project.get('accepted_export') or {}
    return bool(record and record.get('content') == content_key(store, project) and
                any(artifact and artifact.get('sha256') == record.get('sha256')
                    for artifact in (project.get('render'), project.get('draft_render'))))


def accept(jobs, project):
    artifact = next((a for a in (project.get('render'), project.get('draft_render'))
                     if jobs.artifact_ready(project, a)), None)
    if artifact is None:
        raise ValueError('Generate and review the current video before marking it finished.')
    project['accepted_export'] = {'content':content_key(jobs.store, project), 'sha256':artifact['sha256']}
    project['revision'] += 1
    write_json_atomic(jobs.store.folder(project['id'])/'project.json', project)
    return project


def delete_projects(store, workspaces, ids):
    """Delete only validated project directories, never shared models/audio caches."""
    import shutil
    root = store.directory.resolve()
    targets = []
    for pid in ids:
        target = store.folder(pid)
        if target.is_symlink() or target.is_junction() or target.resolve().parent != root:
            raise ValueError('Unsafe project directory; deletion refused.')
        for child in target.rglob('*'):
            if child.is_symlink() or child.is_junction() or not child.resolve().is_relative_to(root):
                raise ValueError('Linked project contents cannot be permanently deleted.')
        targets.append((pid, target))
    catalog = workspaces.read()
    for pid, target in targets:
        if target.exists():shutil.rmtree(target)
        for workspace in catalog:
            workspace['episodes'] = [episode for episode in workspace['episodes'] if episode != pid]
        write_json_atomic(workspaces.path, catalog)
