"""Measure explainer data (next-token odds, tokenizations, embedding maps) in an isolated model process."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from backend.llm.gguf_llm import GGUFLLM
from backend.services import embeddings
from backend.services.next_token import measure, measure_tokens
from backend.services.script_generator import write_json_atomic
from backend.services.worked_examples import identity

if __name__ == '__main__':
    source, output = map(Path, sys.argv[1:3])
    request = json.loads(source.read_text(encoding='utf-8'))
    # A plain list is the original next-token request.
    request = {'next': request, 'tokens': []} if isinstance(request, list) else request
    prompts, texts, maps = request.get('next', []), request.get('tokens', []), request.get('maps', [])
    if not 1 <= len(prompts) + len(texts) + len(maps) <= 200 or any(not isinstance(p, str) or not 1 <= len(p) <= 200 for p in prompts + texts):
        raise ValueError('Expected 1-200 short texts')
    if any(not isinstance(m, list) or not 2 <= len(m) <= 8 or any(not isinstance(x, str) or not 1 <= len(x) <= 40 for x in m) for m in maps):
        raise ValueError('Expected maps of 2-8 short labels')
    results = {'next': {}, 'tokens': {}, 'maps': {}}
    if prompts or texts:
        # The language model loads only for its own measurements.
        engine = GGUFLLM(offline=True, threads=4, on_progress=print)
        try:
            model = identity()
            for prompt in dict.fromkeys(prompts):
                print('Measuring next-token probabilities', flush=True)
                results['next'][prompt] = measure(prompt, engine, model)
            for text in dict.fromkeys(texts):
                print('Measuring tokenization', flush=True)
                results['tokens'][text] = measure_tokens(text, engine, model)
        finally:
            engine.close()
    if maps:
        embedder = embeddings.EmbeddingModel(threads=4)
        try:
            for labels in maps:
                print('Measuring embedding similarities', flush=True)
                results['maps']['\n'.join(labels)] = embeddings.measure(labels, embedder)
        finally:
            embedder.close()
    write_json_atomic(output, results)
