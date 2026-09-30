"""Authored demonstration steps; measured model results live outside editable documents."""
import json
import re
from pathlib import Path
from backend.services.run_state import fingerprint
from backend.services.director import sentences
from backend.services.script_generator import write_json_atomic

ROOT=Path(__file__).resolve().parents[2]
ACTIONS={'tokens','ids','process','generate'}

def validate_spec(spec,narration):
    if not isinstance(spec,dict) or set(spec)!={'input','label','steps'}:
        raise ValueError('Worked examples require input, label and steps')
    for name,limit in [('input',80),('label',40)]:
        value=spec[name]
        if not isinstance(value,str) or not value.strip() or len(value)>limit or any(ord(c)<32 for c in value):
            raise ValueError(f'Example {name} must be a single line of 1-{limit} characters')
    steps=spec['steps']
    if not isinstance(steps,list) or not 1<=len(steps)<=4:
        raise ValueError('Use one to four example steps')
    previous=-1
    for step in steps:
        if not isinstance(step,dict) or set(step)!={'action','sentence'} or not isinstance(step['action'],str) or step['action'] not in ACTIONS:
            raise ValueError('Unknown worked-example action')
        cue=step['sentence']
        if type(cue) is not int or not previous<cue<len(sentences(narration)):
            raise ValueError('Give each example action a different narration sentence, in order')
        previous=cue

def identity():
    config=json.loads((ROOT/'backend/models/local-model.json').read_text(encoding='utf-8'))
    model=ROOT/config['model'];stat=model.stat()
    return {'model':model.name,'sha256':config.get('model_sha256'),'runtime':config['runtime_version'],
            'size':stat.st_size,'modified':stat.st_mtime_ns}

def key_for(text,model):return fingerprint(['worked-llm-v1',text,model])

def read_result(text,model,cache):
    file=cache/f'{key_for(text,model)}.json'
    if not file.is_file():return None
    try:
        value=json.loads(file.read_text(encoding='utf-8'))
        if value['input']!=text or value['model']!=model or value['key']!=key_for(text,model):return None
        validate_result(value)
        return value
    except (OSError,ValueError,KeyError,TypeError):return None

def validate_result(result):
    if not isinstance(result,dict):raise ValueError('Invalid example result')
    if not isinstance(result.get('input'),str) or not 1<=len(result['input'])<=80 or result.get('mode')!='raw_completion':raise ValueError('Invalid measured example input')
    tokens=result['tokens']
    if not isinstance(tokens,list) or not 1<=len(tokens)<=24:raise ValueError('Shorten the input to at most 24 tokens')
    raw=b''
    for token in tokens:
        if not isinstance(token,dict) or set(token)!={'id','piece'}:raise ValueError('Invalid token')
        if type(token['id']) is not int or token['id']<0:raise ValueError('Invalid tokenizer ID')
        piece=token['piece']
        if isinstance(piece,str):raw+=piece.encode('utf-8')
        elif isinstance(piece,list) and all(type(b) is int and 0<=b<=255 for b in piece):raw+=bytes(piece)
        else:raise ValueError('Invalid tokenizer piece')
    if raw!=result['input'].encode('utf-8'):raise ValueError('Tokenizer pieces did not reconstruct the exact input')
    if not isinstance(result['continuation'],str) or len(result['continuation'])>600:raise ValueError('Invalid continuation')
    ids=result['generated_ids']
    if not isinstance(ids,list) or not 1<=len(ids)<=20 or any(type(i) is not int or i<0 for i in ids):raise ValueError('Invalid generated IDs')
    frames=result['prefixes']
    if not isinstance(frames,list) or len(frames)!=len(ids) or any(not isinstance(p,str) or len(p)>600 for p in frames) or frames[-1]!=result['continuation']:
        raise ValueError('Invalid generated-token trace')

def prepare(text,engine,model,cache):
    cached=read_result(text,model,cache)
    if cached:return cached
    engine._load()
    tokens=engine._request('/tokenize',{'content':text,'add_special':False,'parse_special':False,'with_pieces':True})['tokens']
    # Explicit token IDs prevent chat templates or special-token parsing changing the example input.
    if not 1<=len(tokens)<=24:raise ValueError('Shorten the input to at most 24 tokens')
    answer=engine._request('/completion',{'prompt':[t['id'] for t in tokens],'n_predict':12,'temperature':0,'seed':42,'stream':False,'return_tokens':True},timeout=180)
    ids=answer.get('tokens')
    if not isinstance(ids,list) or not ids or len(ids)>20:raise ValueError('The installed model runtime did not return a generated-token trace')
    prefixes=[engine._request('/detokenize',{'tokens':ids[:i]})['content'] for i in range(1,len(ids)+1)]
    # EOS may be present in IDs but absent from decoded content; do not display special tokens.
    continuation=answer['content']
    if prefixes[-1]!=continuation:raise ValueError('Generated token trace does not match the model continuation')
    result={'key':key_for(text,model),'input':text,'tokens':tokens,'continuation':continuation,
            'prefixes':prefixes,'generated_ids':ids,'model':model,'mode':'raw_completion','seed':42}
    validate_result(result);write_json_atomic(cache/f"{result['key']}.json",result)
    return result

def narration_issues(scene,result=None):
    spec=scene['visual'].get('worked')
    if not spec:return []
    issues=[]
    def add(code,text,severity='warning'):issues.append({'code':code,'message':text,'severity':severity})
    parts=sentences(scene['narration'])
    words={'tokens':r'token|split|piece|text','ids':r'id\b|identifier|number','process':r'model|process|network|context','generate':r'generat|predict|continu|output|next'}
    for step in spec['steps']:
        if not re.search(words[step['action']],parts[step['sentence']],re.I):
            add('example_narration','An example action may not match its assigned sentence. Review the action and narration together.')
    if re.search(r'\b\d+(?:\.\d+)?\s*%|\bprobability\s+(?:of\s+)?0\.\d+',scene['narration'],re.I):
        add('example_unsupported_number','This example measures token IDs and a continuation, not probabilities. Verify any numeric probability against a separate source.')
    if result:
        for count in re.findall(r'\b(?:exactly|into)\s+(\d+)\s+tokens?\b',scene['narration'],re.I):
            if int(count)!=len(result['tokens']):add('example_token_count','The stated token count disagrees with this tokenizer result.','error')
    return issues


def model_dependency(document,uid=None):
    if not any(s['visual'].get('worked') for s in (document or {}).get('scenes',[]) if uid is None or s['uid']==uid):return None
    try:return identity()
    except (OSError,ValueError,KeyError):return {'unavailable':True}


def summaries(document):
    model=model_dependency(document)
    result={}
    for scene in document['scenes']:
        spec=scene['visual'].get('worked')
        if not spec:continue
        measured=read_result(spec['input'],model,ROOT/'data/worked-example-cache') if model and not model.get('unavailable') else None
        result[scene['uid']]={'input':spec['input'],'ready':bool(measured),'sentences':sentences(scene['narration'])}
        if measured:result[scene['uid']].update(token_count=len(measured['tokens']),continuation=measured['continuation'],model=measured['model']['model'])
    return result
