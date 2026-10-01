"""Measure explainer data (next-token odds, tokenizations) in an isolated model process."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.llm.gguf_llm import GGUFLLM
from backend.services.next_token import measure, measure_tokens
from backend.services.script_generator import write_json_atomic
from backend.services.worked_examples import identity

if __name__ == '__main__':
    source, output = map(Path, sys.argv[1:3])
    request = json.loads(source.read_text(encoding='utf-8'))
    # A plain list is the original next-token request.
    request = {'next': request, 'tokens': []} if isinstance(request, list) else request
    prompts, texts = request.get('next', []), request.get('tokens', [])
    if not 1 <= len(prompts) + len(texts) <= 200 or any(not isinstance(p, str) or not 1 <= len(p) <= 200 for p in prompts + texts):
        raise ValueError('Expected 1-200 short texts')
    engine = GGUFLLM(offline=True, threads=4, on_progress=print)
    try:
        model = identity()
        results = {'next': {}, 'tokens': {}}
        for prompt in dict.fromkeys(prompts):
            print('Measuring next-token probabilities', flush=True)
            results['next'][prompt] = measure(prompt, engine, model)
        for text in dict.fromkeys(texts):
            print('Measuring tokenization', flush=True)
            results['tokens'][text] = measure_tokens(text, engine, model)
        write_json_atomic(output, results)
    finally:
        engine.close()
