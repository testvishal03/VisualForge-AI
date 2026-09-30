"""Choose a bounded video scope with the installed local model."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.llm.gguf_llm import create_local_llm
from backend.services.json_parser import parse_json_object
from backend.services.script_generator import write_json_atomic

LENGTHS=[0.5,1,2,3,4,7,8,10,15,20,30]

def choose_length(topic,engine):
    schema={'type':'object','properties':{'minutes':{'type':'number','enum':LENGTHS},'reason':{'type':'string'}},'required':['minutes','reason'],'additionalProperties':False}
    prompt='Choose the shortest useful educational video length for this request. Use 0.5-2 minutes for a focused question, 3-4 for several concepts, 7-10 for a detailed tutorial, 15-30 only for an explicitly comprehensive course. Respect an explicitly requested duration by choosing the closest supported length. Give a short plain-language reason. Return JSON with minutes and reason. Request: '+json.dumps(topic)
    result=parse_json_object(engine.generate_json(prompt,schema=schema,max_new_tokens=180,temperature=0))
    if type(result.get('minutes')) not in (int,float) or result['minutes'] not in LENGTHS or not isinstance(result.get('reason'),str) or not 1<=len(result['reason'])<=500:raise ValueError('The model returned an invalid length plan. Retry generation.')
    return result

if __name__=='__main__':
    request=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
    engine=create_local_llm(offline=True,threads=2,on_progress=print)
    try:write_json_atomic(Path(sys.argv[2]),choose_length(request['topic'],engine))
    finally:
        if hasattr(engine,'close'):engine.close()
