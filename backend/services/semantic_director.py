"""Local-model visual planning grounded in the exact narration, for any topic."""
import json
import re
from pathlib import Path
from typing import Literal
from pydantic import Field
from backend.schemas.video_schema import StrictContent, Scene
from backend.services.director import ICONS, sentences, direct_scene, choose_icon
from backend.services.lesson_quality import label_problem, label_candidates, improve_visual
from backend.services.json_parser import parse_json_object
from backend.services.run_state import fingerprint
from backend.services.script_generator import write_json_atomic


class Element(StrictContent):
    label: str = Field(min_length=1, max_length=60)
    sentence: int = Field(ge=0, le=20)
    icon: str


class VisualDecision(StrictContent):
    layout: Literal['auto','pipeline','branching','layers','contrast','timeline','detail'] = 'auto'
    kind: Literal['process', 'relationship', 'components', 'comparison', 'cycle', 'timeline', 'explanation', 'example', 'neural_net', 'analogy', 'takeaway']
    elements: list[Element] = Field(max_length=4)
    icon: str
    treatment: Literal['build','focus','compare'] = 'build'


def normalized(text):
    return ' '.join(re.findall(r"\b[\w]+(?:[-'][\w]+)*\b", text.casefold()))


def grounded_icon(icon, label, scene):
    # Domain-specific pictograms need topic support; generic symbols remain
    # available to the model. This prevents a water droplet on a token diagram.
    domain = {'sun','cloud','water','rain','leaf','battery','globe'}
    context = choose_icon(scene.headline+' '+scene.narration)
    return context if icon in domain and icon not in {choose_icon(label), context} else icon


def validate_decision(data, scene, index):
    decision = VisualDecision.model_validate(data)
    from backend.services.scene_direction import COMPATIBLE
    if decision.layout!='auto' and decision.kind not in COMPATIBLE[decision.layout]:
        raise ValueError('Choose a composition compatible with the diagram kind.')
    count = len(decision.elements)
    expected = {'process': (3,), 'relationship': (2, 3), 'components': (2, 3, 4),
                'comparison': (2,), 'cycle': (2, 3, 4), 'timeline': (2, 3, 4),
                'explanation': (0,), 'example': (0,), 'neural_net': (2, 3, 4), 'analogy': (0,), 'takeaway': (0,)}[decision.kind]
    if count not in expected:
        raise ValueError(f'{decision.kind} requires {expected} elements.')
    parts = sentences(scene.narration)
    cues, labels, icons = [], [], []
    for element in decision.elements:
        Scene.plain_text(element.label)
        if element.sentence >= len(parts) or element.icon not in ICONS:
            raise ValueError('Use a listed icon and a valid zero-based sentence index.')
        if label_problem(element.label):
            raise ValueError('Use a complete label, without a dangling ending or ellipsis.')
        label = normalized(element.label)
        # Labels must come from narration; diagram relationships still require
        # editorial review. Never execute or fetch model-generated content.
        if not label or f' {label} ' not in f' {normalized(parts[element.sentence])} ':
            raise ValueError(f'Label {element.label!r} must be an exact short phrase from sentence {element.sentence}: {parts[element.sentence]}')
        labels.append(element.label)
        cues.append(element.sentence)
        icons.append(grounded_icon(element.icon, element.label, scene))
    if len(set(normalized(s) for s in labels)) != count or cues != sorted(cues):
        raise ValueError('Use distinct labels in narration sentence order.')
    if decision.icon not in ICONS:
        raise ValueError('Use a listed icon.')
    return {'id': scene.id, 'layout': decision.layout, 'kind': decision.kind, 'items': labels, 'cues': cues, 'icons': icons,
            'motion': {'process':'assemble','components':'assemble','relationship':'focus','comparison':'focus','timeline':'reveal','cycle':'flow','neural_net':'flow','code':'reveal'}.get(decision.kind,'reveal'),
            'icon': grounded_icon(decision.icon, scene.headline, scene), 'directed': True, 'planned': True, 'treatment':decision.treatment, 'variant': index % 2,
            'transition': 'slide' if decision.kind=='process' and index%3==1 else 'fade'}


def plan_video(video, *, engine, cache: Path, instructions=""):
    # Constrain element count during decoding, not just after the response.
    # Small local models otherwise often emit one node for a multi-node diagram.
    base = VisualDecision.model_json_schema()
    base['$defs']['Element']['properties']['icon']['enum'] = sorted(ICONS)
    limits = {'process':(3,3),'relationship':(2,3),'components':(2,4),'comparison':(2,2),
              'cycle':(2,4),'timeline':(2,4),'explanation':(0,0),'example':(0,0),
              'neural_net':(2,4),'analogy':(0,0),'takeaway':(0,0)}
    schema = {'$defs':base['$defs'], 'anyOf':[
        {'type':'object', 'properties':{'kind':{'type':'string','const':kind},
            'elements':{'type':'array','items':{'$ref':'#/$defs/Element'},'minItems':lo,'maxItems':hi},
            'icon':{'type':'string','enum':sorted(ICONS)},
            'treatment':{'type':'string','enum':['build','focus','compare']},
            'layout':{'type':'string','enum':['auto','detail',{'process':'pipeline','relationship':'branching','components':'layers','comparison':'contrast','timeline':'timeline','neural_net':'auto','code':'auto'}.get(kind,'auto')] if kind in {'process','relationship','components','comparison','timeline'} else ['auto']}},
         'required':['kind','elements','icon','layout','treatment'],'additionalProperties':False}
        for kind,(lo,hi) in limits.items()]}
    rows, warnings = [], []
    for index, scene in enumerate(video.scenes):
        extracted = direct_scene(scene, index, len(video.scenes))
        from backend.services.topic_visuals import topic_visual
        if extracted['kind'] == 'chart' or topic_visual(scene):
            # Numeric data comes only from the existing literal percentage parser.
            rows.append(improve_visual(scene, {'id': scene.id, **extracted, 'planned': True}, rows))
            continue
        parts = sentences(scene.narration)
        # Let the model select source phrases rather than generate paraphrases
        # and repeatedly fail exact-grounding checks on a small CPU model.
        choices = []
        for sentence_id, part in enumerate(parts):
            labels = label_candidates(part)
            if not labels:
                continue
            choices.append({'type':'object','properties':{'label':{'type':'string','enum':labels},
                'sentence':{'type':'integer','const':sentence_id},'icon':{'type':'string','enum':sorted(ICONS)}},
                'required':['label','sentence','icon'],'additionalProperties':False})
        schema['$defs']['Element'] = {'anyOf':choices}
        prompt = f'''Act as an educational animation director. Plan visuals for this exact narration, whatever its topic.
Topic: {video.topic}
Headline: {scene.headline}
Narration sentences (zero-based indices): {json.dumps(dict(enumerate(parts)))}
Visual revision request (preserve narration and facts): {instructions[:1000]}
Previous visual forms: {json.dumps([(r['kind'],r.get('layout','auto')) for r in rows[-2:]])}
Choose the form that explains the actual meaning: process for 3 ordered stages; relationship for 2-3 connected concepts; components for 2-4 system parts; comparison for 2 contrasted concepts; cycle for 2-4 genuinely repeating stages; timeline for 2-4 explicitly dated events. Use neural_net only for an explicitly described network of layers, never simply because the topic mentions AI. Its nodes are schematic, not measured activations. Use analogy only for an explicit analogy, takeaway for an explicit conclusion, and example for a worked example. These three and explanation have NO elements when a diagram does not fit. Do not turn every scene into the same diagram. Never invent a sequence or cycle just for visual variety.
Each element label must be a short EXACT phrase copied from its cited narration sentence, preferably a complete noun phrase or action, maximum 60 characters. Select complete concrete entities or actions. Never cut off a clause or end on an article or preposition. Labels must be distinct and appear in sentence-index order. Use only these icons: {', '.join(sorted(ICONS))}.
Choose layout: pipeline for an ordered demonstration, branching for connected concepts, layers for system parts (not necessarily a hierarchy), contrast for a comparison, timeline for dated events, detail to zoom into each concept, or auto for other forms. Use detail when a neighboring scene already uses the same composition. Preserve the meaning; do not invent hierarchy or causality. Return kind, layout, elements (label, sentence, icon), and an overall icon. Also select treatment: build to introduce objects in spoken order, focus to emphasize the current object, compare only for a narrated comparison. No code, URLs, image paths, extra facts, or rewritten narration.'''
        key = fingerprint([prompt, getattr(engine, 'cache_identity', 'local'), 'semantic-director-v3'])
        file = cache / f'{key}.json'
        row = None
        if file.is_file():
            try:
                row = validate_decision(json.loads(file.read_text(encoding='utf-8')), scene, index)
            except ValueError:
                pass
        retry = prompt
        if row is None:
            for attempt in range(3):
                print(f'Visual scene {scene.id}/{len(video.scenes)}: attempt {attempt+1}/3', flush=True)
                raw = engine.generate_json(retry, schema=schema, max_new_tokens=650) if hasattr(engine, 'generate_json') else engine.generate(retry, max_new_tokens=650)
                cache.mkdir(parents=True, exist_ok=True)
                (cache/f'{key}-attempt-{attempt+1}.txt').write_text(raw, encoding='utf-8')
                try:
                    data = parse_json_object(raw)
                    row = validate_decision(data, scene, index)
                    write_json_atomic(file, data)
                    break
                except ValueError as exc:
                    print(f'Visual decision rejected: {str(exc)[:350]}', flush=True)
                    retry = prompt + '\nCorrect this invalid decision: ' + raw[:2000] + '\nValidation error: ' + str(exc)[:500]
        if row is None:
            row = {'id': scene.id, **direct_scene(scene, index, len(video.scenes)), 'planned': True}
            warnings.append({'scene': scene.id, 'message': 'AI visual plan failed validation; used narration-based fallback.'})
            print(f'Visual scene {scene.id}: AI plan failed validation; using narration-based fallback.', flush=True)
        row = improve_visual(scene, row, rows)
        from backend.services.choreography import compile_scene
        demonstration = compile_scene(scene.model_dump(), row)
        if demonstration:row['choreography']=demonstration
        rows.append(row)
        print(f"Visual scene {scene.id}: {row['kind']} — {', '.join(row['items'])}", flush=True)
    return {'scenes': rows, 'warnings': warnings,
            'notice': 'AI-selected diagrams use labels copied from narration. Review meaning and factual accuracy before publishing.'}
