"""Validated source-linked teaching plans; toy numbers are explicitly illustrative."""
import math
import re
from typing import Literal
from pydantic import Field, model_validator
from backend.schemas.video_schema import StrictContent
from backend.services.director import sentences


class TeachingStep(StrictContent):
    sentence: int = Field(ge=0, le=60)
    action: Literal['explain','encode','compare','retrieve','context','answer']
    label: str = Field(min_length=1, max_length=60)


class TeachingPlan(StrictContent):
    version: Literal[1] = 1
    component: Literal['explanation','embedding','vector_search','rag','python','sql']
    question: str = Field(min_length=1, max_length=150)
    objective: str = Field(min_length=1, max_length=180)
    takeaway: str = Field(min_length=1, max_length=600)
    evidence: Literal['source','illustrative','computed']
    steps: list[TeachingStep] = Field(min_length=1, max_length=20)

    @model_validator(mode='after')
    def ordered(self):
        cues = [step.sentence for step in self.steps]
        if cues != sorted(set(cues)):
            raise ValueError('Teaching steps need distinct ordered sentence cues')
        if self.evidence != ('illustrative' if self.component in {'embedding','vector_search'} else 'computed' if self.component in {'python','sql'} else 'source'):
            raise ValueError('Toy vectors must be labeled illustrative')
        if self.component == 'rag':
            actions = [step.action for step in self.steps]
            if not {'retrieve','answer'} <= set(actions) or actions.index('answer') <= actions.index('retrieve'):
                raise ValueError('RAG must retrieve sources before generating an answer')
        return self


def validate_plan(plan, narration):
    result = TeachingPlan.model_validate(plan)
    parts = sentences(narration)
    for step in result.steps:
        if step.sentence >= len(parts) or step.label.casefold() not in parts[step.sentence].casefold():
            raise ValueError('Teaching labels must occur in their narration sentence')
    if result.takeaway != parts[-1]:
        raise ValueError('Teaching takeaway must preserve the final source sentence')
    return result.model_dump()


def plan_scene(scene):
    text = scene['narration']
    parts = sentences(text)
    component = 'explanation'
    # Require mechanism evidence, not just a topic title or an incidental keyword.
    if re.search(r'\b(retriev\w*|RAG)\b', text, re.I) and re.search(r'\b(documents?|sources?|passages?)\b', text, re.I) and re.search(r'\b(answer|response|generat\w*)\b', text, re.I):
        component = 'rag'
    elif re.search(r'\b(vector|embedding)s?\b', text, re.I) and re.search(r'\b(similarity|nearest|cosine|closest)\b', text, re.I):
        component = 'vector_search'
    elif re.search(r'\bembeddings?\b', text, re.I) and re.search(r'\b(vectors?|numbers?|numerical)\b', text, re.I):
        component = 'embedding'
    # Do not overlay a conflicting toy calculation on an authored numeric example.
    if component in {'embedding','vector_search'} and re.search(r'\d', text):
        component = 'explanation'
    patterns = ([('retrieve',r'\bretriev\w*\b'), ('answer',r'\bgenerat(?:e|es|ed|ing)\b'),
                 ('context',r'\bcontext\b'), ('answer',r'\b(?:answer|response)\b'),
                 ('retrieve',r'\b(?:documents?|passages?|sources?)\b')]
                if component=='rag' else [('compare',r'\b(?:similarity|nearest|cosine|closest|compare\w*)\b'),
                 ('encode',r'\b(?:embeddings?|vectors?|numbers?|numerical)\b')])
    steps = []
    for i, part in enumerate(parts[:20]):
        action, label = 'explain', None
        for candidate, pattern in patterns if component!='explanation' else []:
            match = re.search(pattern, part, re.I)
            if match:
                action, label = candidate, match[0]
                break
        if component == 'rag' and action in {'retrieve','context','answer'}:
            noun = re.search({'retrieve':r'\b(?:relevant documents|documents?|sources?|passages?)\b',
                              'context':r'\b(?:selected passages|passages?|context)\b',
                              'answer':r'\b(?:answer|response)\b'}[action], part, re.I)
            if noun:
                label = noun[0]
        if label is None:
            # The plan remains source-linked even for ordinary scenes.
            match = re.search(r'\b[\w-]{3,40}\b', part)
            label = match[0] if match else part[:60]
        steps.append({'sentence':i,'action':action,'label':label})
    if component=='rag':
        actions=[s['action'] for s in steps]
        if not {'retrieve','answer'} <= set(actions) or actions.index('answer') < actions.index('retrieve'):
            component='explanation'
    from backend.services.code_examples import select_spec
    demo=select_spec(scene)
    if demo:component='python' if demo['kind'].startswith('python_') else 'sql'
    return validate_plan({'version':1,'component':component,
        'question':f"What does this explain about {scene['headline'].rstrip('.?!')}?",
        'objective':scene['body'], 'takeaway':parts[-1],
        'evidence':'illustrative' if component in {'embedding','vector_search'} else 'computed' if component in {'python','sql'} else 'source', 'steps':steps},text)


def plan_document(document):
    return [{'uid':scene['uid'], **plan_scene({**scene,'topic':document['topic']})} for scene in document['scenes']]


def toy_vectors():
    """Reproducible two-dimensional arithmetic, never claimed as model output."""
    query = [1.0, 0.0]
    points = [{'label':'A','vector':[1.0,0.0]}, {'label':'B','vector':[0.8,0.6]}, {'label':'C','vector':[0.0,1.0]}]
    for point in points:
        x,y = point['vector']
        point['cosine'] = round(x/math.hypot(x,y),6)
    return {'query':query, 'points':points, 'metric':'cosine', 'provenance':'illustrative'}


def timed_plan(scene, beats):
    plan = plan_scene(scene)
    if len(beats) != len(sentences(scene['narration'])):
        raise ValueError('Teaching plan requires measured narration sentence timings')
    plan['at'] = [beats[s['sentence']]['start'] for s in plan['steps']]
    if plan['component'] in {'embedding','vector_search'}:
        plan['example'] = toy_vectors()
    return plan
