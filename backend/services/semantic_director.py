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


class Concept(StrictContent):
    label: str = Field(min_length=1, max_length=60)
    sentence: int = Field(ge=0, le=20)


# Generic scenes show the concepts a learner should see appear; these kinds have no diagram elements.
CONCEPT_KINDS = {'explanation', 'example'}
MAX_CONCEPTS = 5


def concept_options(part):
    """Noun phrases the model may choose for one sentence, exactly as they are spoken."""
    from backend.services.key_terms import candidates, spoken
    return sorted({label for c in candidates(part, alternatives=True) if 3 <= len(c) <= 36 and (label := spoken(part, c))})


# Words a cut-off phrase tends to stop on ("millions of tiny", "work a little", "clean it up").
DANGLING_END = {'tiny', 'little', 'big', 'small', 'huge', 'large', 'up', 'down', 'out', 'off', 'away', 'back'}


def element_options(part):
    """Diagram labels: noun phrases, or short actions that start with a content word, never sentence fragments."""
    from backend.services.key_terms import SOLO_STOP, STOP, noun_like
    def whole(c):
        words = c.split()
        return (2 <= len(words) <= 4 and len(words[0]) >= 3 and words[0].isalpha() and words[0].lower() not in STOP
                and words[1].lower() not in {'we', 'you', 'they', 'i'}
                and words[-1].lower() not in STOP | SOLO_STOP | DANGLING_END and noun_like(c)  # never end mid-phrase
                and not any(w.lower() in {'that', 'which', 'who', 'whose'} for w in words))
    actions = [c for c in label_candidates(part) if whole(c)]
    return sorted(set(concept_options(part)) | set(actions))


def same_concept(a, b):
    """"chunk" and "chunks" are one concept on screen."""
    stem = lambda text: ' '.join(w[:-1] if w.endswith('s') and len(w) > 3 else w for w in normalized(text).split())
    return stem(a) == stem(b)


class VisualDecision(StrictContent):
    layout: Literal['auto','pipeline','branching','layers','contrast','timeline','detail'] = 'auto'
    kind: Literal['process', 'relationship', 'components', 'comparison', 'cycle', 'timeline', 'explanation', 'example', 'neural_net', 'analogy', 'takeaway']
    elements: list[Element] = Field(max_length=4)
    icon: str
    treatment: Literal['build','focus','compare'] = 'build'
    concepts: list[Concept] = Field(default_factory=list, max_length=MAX_CONCEPTS)


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
    if any(same_concept(a, b) for i, a in enumerate(labels) for b in labels[i+1:]):
        raise ValueError('Use distinct concepts; singular and plural forms of one word are the same concept.')
    if decision.icon not in ICONS:
        raise ValueError('Use a listed icon.')
    concepts = validate_concepts(decision, parts)
    return {**({'concepts': concepts} if concepts else {}),'id': scene.id, 'layout': decision.layout, 'kind': decision.kind, 'items': labels, 'cues': cues, 'icons': icons,
            'motion': {'process':'assemble','components':'assemble','relationship':'focus','comparison':'focus','timeline':'reveal','cycle':'flow','neural_net':'flow','code':'reveal'}.get(decision.kind,'reveal'),
            'icon': grounded_icon(decision.icon, scene.headline, scene), 'directed': True, 'planned': True, 'treatment':decision.treatment, 'variant': index % 2,
            'transition': 'slide' if decision.kind=='process' and index%3==1 else 'fade'}


def validate_concepts(decision, parts):
    """Concepts must be offered phrases of their sentence, distinct, and in spoken order."""
    if decision.kind not in CONCEPT_KINDS:
        if decision.concepts:
            raise ValueError('Only explanation and example scenes list concepts.')
        return []
    result, seen, previous = [], set(), 0
    for concept in decision.concepts:
        if concept.sentence >= len(parts) or concept.sentence < previous:
            raise ValueError('List concepts with valid sentence indices in spoken order.')
        if concept.label not in concept_options(parts[concept.sentence]):
            raise ValueError(f'Concept {concept.label!r} must be one of the offered phrases of sentence {concept.sentence}.')
        if concept.label.casefold() in seen:
            raise ValueError('Use distinct concepts.')
        seen.add(concept.label.casefold())
        result.append({'label': concept.label, 'sentence': concept.sentence})
        previous = concept.sentence
    return result


def salvage(data, scene, index):
    """Keep a nearly valid answer: when only duplicates or ordering were wrong, its distinct
    noun-phrase picks become explanation concepts instead of spending another model attempt."""
    try:
        decision = VisualDecision.model_validate(data)
    except ValueError:
        return None
    parts, kept = sentences(scene.narration), []
    for element in sorted(decision.elements, key=lambda e: e.sentence):
        if element.sentence < len(parts) and element.label in concept_options(parts[element.sentence])                 and not any(same_concept(element.label, k['label']) for k in kept):
            kept.append({'label': element.label, 'sentence': element.sentence})
    if len(kept) < 2:
        return None
    try:
        return validate_decision({'kind': 'explanation', 'elements': [], 'layout': 'auto', 'icon': decision.icon,
                                  'treatment': decision.treatment, 'concepts': kept[:MAX_CONCEPTS]}, scene, index)
    except ValueError:
        return None


SEQUENCE = r'\b(?:first(?:ly)?|second(?:ly)?|third|next|then|finally|lastly|afterwards?|before|once|step|stages?|begins?|starts?|ends?|until)\b'


def decide(data, scene, index):
    try:
        row = validate_decision(data, scene, index)
        # Small models call most scenes a "process". Without narrated sequence words there are no
        # ordered steps to show, so the model's own noun picks become the scene's concepts instead.
        if row['kind'] == 'process' and not re.search(SEQUENCE, scene.narration, re.I):
            return salvage(data, scene, index) or row
        return row
    except ValueError as exc:
        if 'distinct' in str(exc) or 'order' in str(exc):
            row = salvage(data, scene, index)
            if row:
                return row
        raise


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
            'layout':{'type':'string','enum':['auto','detail',{'process':'pipeline','relationship':'branching','components':'layers','comparison':'contrast','timeline':'timeline','neural_net':'auto','code':'auto'}.get(kind,'auto')] if kind in {'process','relationship','components','comparison','timeline'} else ['auto']},
            'concepts':{'type':'array','items':{'$ref':'#/$defs/Concept'},'minItems':0,'maxItems':MAX_CONCEPTS if kind in CONCEPT_KINDS else 0}},
         'required':['kind','elements','icon','layout','treatment','concepts'],'additionalProperties':False}
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
            labels = element_options(part)
            if not labels:
                continue
            choices.append({'type':'object','properties':{'label':{'type':'string','enum':labels},
                'sentence':{'type':'integer','const':sentence_id},'icon':{'type':'string','enum':sorted(ICONS)}},
                'required':['label','sentence','icon'],'additionalProperties':False})
        schema['$defs']['Element'] = {'anyOf':choices}
        # Concept choices are the sentence's own noun phrases, so a pick is always a verbatim quote.
        offered = [{'type':'object','properties':{'label':{'type':'string','enum':options},'sentence':{'type':'integer','const':i}},
                    'required':['label','sentence'],'additionalProperties':False}
                   for i, part in enumerate(parts) if (options := concept_options(part))]
        schema['$defs']['Concept'] = {'anyOf':offered} if offered else {'type':'object','properties':{},'additionalProperties':False}
        for option in schema['anyOf']:
            if option['properties']['kind']['const'] in CONCEPT_KINDS:
                option['properties']['concepts']['minItems'] = min(2, len(offered))
                option['properties']['concepts']['maxItems'] = MAX_CONCEPTS if offered else 0
        prompt = f'''Act as an educational animation director. Plan visuals for this exact narration, whatever its topic.
Topic: {video.topic}
Headline: {scene.headline}
Narration sentences (zero-based indices): {json.dumps(dict(enumerate(parts)))}
Visual revision request (preserve narration and facts): {instructions[:1000]}
Previous visual forms: {json.dumps([(r['kind'],r.get('layout','auto')) for r in rows[-2:]])}
Choose the form that explains the actual meaning: process for 3 ordered stages; relationship for 2-3 connected concepts; components for 2-4 system parts; comparison for 2 contrasted concepts; cycle for 2-4 genuinely repeating stages; timeline for 2-4 explicitly dated events. Use neural_net only for an explicitly described network of layers, never simply because the topic mentions AI. Its nodes are schematic, not measured activations. Use analogy only for an explicit analogy, takeaway for an explicit conclusion, and example for a worked example. These three and explanation have NO elements when a diagram does not fit. Do not turn every scene into the same diagram. Never invent a sequence or cycle just for visual variety.
Each element label must be a short EXACT phrase copied from its cited narration sentence, preferably a complete noun phrase or action, maximum 60 characters. Select complete concrete entities or actions. Never cut off a clause or end on an article or preposition. Labels must be distinct and appear in sentence-index order. Use only these icons: {', '.join(sorted(ICONS))}.
Choose layout: pipeline for an ordered demonstration, branching for connected concepts, layers for system parts (not necessarily a hierarchy), contrast for a comparison, timeline for dated events, detail to zoom into each concept, or auto for other forms. Use detail when a neighboring scene already uses the same composition. Preserve the meaning; do not invent hierarchy or causality. Return kind, layout, elements (label, sentence, icon), and an overall icon. Also select treatment: build to introduce objects in spoken order, focus to emphasize the current object, compare only for a narrated comparison. No code, URLs, image paths, extra facts, or rewritten narration.
For explanation and example scenes, also list concepts: the 2-5 things a learner should see appear, in sentence order, as the explanation proceeds. Choose concrete nouns or noun phrases that the sentence is actually about (for example a system, object or piece of data), never verbs, adjectives or vague words such as point, way or comparison. For every other kind, concepts is an empty list.'''
        key = fingerprint([prompt, getattr(engine, 'cache_identity', 'local'), 'semantic-director-v6-noun-labels'])
        file = cache / f'{key}.json'
        row = None
        if file.is_file():
            try:
                row = decide(json.loads(file.read_text(encoding='utf-8')), scene, index)
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
                    row = decide(data, scene, index)
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
