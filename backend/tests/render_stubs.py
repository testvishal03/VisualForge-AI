"""Keep workflow tests independent of Chromium; real cache rendering has its own smoke test."""
def cached(jobs,project,data,props,pending,profile,render):
    render(['render','VisualForgeVideo',pending,f'--props={props}','--concurrency=2',*(['--scale=0.6666666666666666'] if profile=='draft' else [])],'render')
