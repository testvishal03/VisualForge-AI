"""Run bounded tokenizer/continuation examples in the existing isolated worker pipeline."""
import json
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from backend.llm.gguf_llm import GGUFLLM
from backend.services.worked_examples import ROOT,identity,prepare,validate_spec
from backend.services.script_generator import write_json_atomic

if __name__=='__main__':
    source,output=map(Path,sys.argv[1:3]);inputs=json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(inputs,list) or not 1<=len(inputs)<=500:raise ValueError('Expected 1-500 short example inputs')
    for text in inputs:validate_spec({'input':text,'label':'Example','steps':[{'action':'tokens','sentence':0}]},'Example.')
    engine=GGUFLLM(offline=True,threads=2,on_progress=print)
    try:
        model=identity();results={}
        for text in dict.fromkeys(inputs):
            print('Preparing measured tokenizer example',flush=True)
            results[text]=prepare(text,engine,model,ROOT/'data/worked-example-cache')
        write_json_atomic(output,results)
    finally:engine.close()
