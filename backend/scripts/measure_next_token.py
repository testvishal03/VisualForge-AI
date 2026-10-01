"""Measure next-token probabilities for explainer prompts in an isolated model process."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.llm.gguf_llm import GGUFLLM
from backend.services.next_token import measure
from backend.services.script_generator import write_json_atomic
from backend.services.worked_examples import identity

if __name__ == '__main__':
    source, output = map(Path, sys.argv[1:3])
    prompts = json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(prompts, list) or not 1 <= len(prompts) <= 100 or any(not isinstance(p, str) or not 1 <= len(p) <= 80 for p in prompts):
        raise ValueError('Expected 1-100 short prompts')
    engine = GGUFLLM(offline=True, threads=4, on_progress=print)
    try:
        model, results = identity(), {}
        for prompt in dict.fromkeys(prompts):
            print('Measuring next-token probabilities', flush=True)
            results[prompt] = measure(prompt, engine, model)
        write_json_atomic(output, results)
    finally:
        engine.close()
