"""Source-grounded visual plans shared by review, preview, and full rendering."""
import re
from backend.services.director import sentences

TITLES = {'encoding':'From text to a vector','meaning-space':'Meaning in vector space',
          'dimensions':'Beyond a two-dimensional view','retrieval':'Search by meaning',
          'rag':'Retrieve context, then generate','tokens':'Text becomes tokens',
          'context':'What fits in the context window','attention':'Connect relevant tokens',
          'generation':'Generate one token at a time','vector-database':'Store and search vectors'}
ACTIONS = {'encoding':'encode','meaning-space':'cluster','dimensions':'project','retrieval':'search',
           'rag':'retrieve','tokens':'split','context':'fill','attention':'connect',
           'generation':'predict','vector-database':'index'}


def mechanism(scene):
    text = scene['narration']
    v = scene.get('visual', {})
    if v.get('worked') or v.get('demo') or v.get('kind') in {'code','chart','stat_card','water_cycle','neural_net'}:
        return 'authored'
    if re.search(r'\b(retriev\w*|RAG)\b',text,re.I) and re.search(r'\b(context|LLM|language model|answer)\b',text,re.I):return 'rag'
    checks = [
        ('context', r'\bcontext window\b|\b(?:context|token) (?:limit|capacity|budget)\b'),
        ('tokens', r'\b(?:tokeniz\w*|split\w* into tokens|broken into tokens|token IDs?)\b'),
        ('attention', r'\battention\b.*\b(?:tokens?|words?|queries|keys|values|relationships)\b'),
        ('generation', r'\b(?:next[- ]token|next word|one token at a time|autoregressive)\b'),
        ('vector-database', r'\bvector (?:database|index)\b.*\b(?:stor\w*|search\w*|insert\w*|index\w*)\b'),
    ]
    for kind, pattern in checks:
        if re.search(pattern,text,re.I):return kind
    if re.search(r'\b(retriev\w*|RAG)\b',text,re.I) and re.search(r'\b(context|LLM|language model|answer)\b',text,re.I):return 'rag'
    if re.search(r'\b(semantic search|keyword search|similarity search|closest matches|query vector)\b',text,re.I):return 'retrieval'
    if re.search(r'\b(dimensions?|dimensional)\b',text,re.I) and re.search(r'\b(embedding|vector)s?\b',text,re.I):return 'dimensions'
    if re.search(r'\b(embedding|vector)s?\b',text,re.I) and re.search(r'\b(close|closer|nearby|farther|distance|cluster|geometry|space|similar meanings|relationships between)\b',text,re.I):return 'meaning-space'
    if re.search(r'\bembeddings?\b',text,re.I) and re.search(r'\b(numerical|numbers|converts?|represented|representation|model|vector)\b',text,re.I):return 'encoding'
    return 'fallback'


def plan_document(document):
    rows=[]
    for scene in document['scenes']:
        kind=mechanism(scene)
        # Existing executable demonstrations have priority even with automatic inputs.
        from backend.services.code_examples import select_spec
        if select_spec({**scene,'topic':document['topic']}):kind='authored'
        objects=[]
        for match in re.finditer(r'\b(?:tokens?|context|query|documents?|vectors?|embeddings?|model|answer|keys|values|words?|database)\b',scene['narration'],re.I):
            label=match[0].lower()
            if label not in objects:objects.append(label)
        previous=rows[-1] if rows else None
        carry=next((o for o in objects if previous and o in previous['objects']),None)
        same=bool(previous and previous['kind']==kind and kind in TITLES)
        from backend.services.choreography import compile_scene
        choreography=compile_scene(scene)
        rows.append({'choreography':choreography, 'uid':scene['uid'],'kind':kind,'title':TITLES.get(kind,scene['headline']),
            'question':f"How does this work: {scene['headline'].rstrip('.?!')}?", 'objects':objects[:8],
            'steps':[{'sentence':i,'action':ACTIONS.get(kind,'explain'),'text':part} for i,part in enumerate(sentences(scene['narration']))],
            'view':'detail' if same and previous['view']=='overview' else 'overview',
            'carry':carry,'supported':kind!='fallback',
            'transition':'continue' if same else 'zoom' if kind=='dimensions' else 'flow' if kind in {'rag','encoding','vector-database'} else 'fade'})
    warnings=[]
    for i,row in enumerate(rows):
        if row.get('choreography'):
            if len(row['choreography']['objects'])>4:warnings.append({'scene':i+1,'message':'Several objects share this scene. Check label readability in the preview.'})
            continue
        if row['kind']=='fallback':warnings.append({'scene':i+1,'message':'No specialized demonstration matches this passage. Review the existing diagram or card in the preview.'})
        if i>=2 and row['kind']==rows[i-1]['kind']==rows[i-2]['kind']:
            warnings.append({'scene':i+1,'message':'This visual mechanism repeats across three scenes. Detail views vary the focus; consider combining repeated explanations.'})
    return {'scenes':rows,'warnings':warnings,'specialized':sum(r['kind'] in TITLES for r in rows),'total':len(rows)}


def timed_plan(plan, beats):
    return {**plan,'at':[beats[s['sentence']]['start'] for s in plan['steps']]}


def preview(jobs, project, folder):
    if 'long_video' not in project:
        return jobs._perform(project,'style_preview',None,'',folder)
    from backend.services.long_video import nested_jobs
    nested=nested_jobs(jobs,project)
    children=[nested.store.load(row['id']) for row in project['long_video']['chapters']]
    children=[child for child in children if child.get('document')]
    if not children:raise ValueError('Prepare a script before previewing visuals.')
    child=max(children,key=lambda c:len({r['kind'] for r in plan_document(c['document'])['scenes'] if r['supported']}))
    nested._perform(child,'style_preview',None,'',nested.store.folder(child['id']))
    jobs.state['message']='Representative chapter preview ready. Full narration is preserved.'
