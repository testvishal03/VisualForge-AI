"""Measured next-token probabilities from the installed local model, for the next-token explainer.

The model's own pre-sampling probabilities for the token after a prompt are recorded with
the exact prompt and model identity, so a cached measurement is reused only for the same
model file. Nothing here is estimated: a missing or failed measurement leaves the explainer
in its labelled illustrative form.
"""
import json
import math
from pathlib import Path

from backend.services.run_state import fingerprint
from backend.services.script_generator import write_json_atomic

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'data/next-token-cache'
TOP = 5  # requested from the model; at most three visible tokens are shown


def key_for(text, model):
    return fingerprint(['next-token-v1', text, model])


def validate(result, text=None, model=None):
    if not isinstance(result, dict) or result.get('mode') != 'next_token':
        raise ValueError('Invalid next-token measurement')
    if text is not None and (result.get('input') != text or result.get('model') != model or result.get('key') != key_for(text, model)):
        raise ValueError('Measurement belongs to another prompt or model')
    rows = result.get('candidates')
    if not isinstance(rows, list) or not 1 <= len(rows) <= TOP:
        raise ValueError('Expected one to five measured candidates')
    previous = 1.0
    for row in rows:
        if not isinstance(row, dict) or set(row) != {'token', 'prob'} or not isinstance(row['token'], str) or not 1 <= len(row['token']) <= 40:
            raise ValueError('Invalid measured candidate')
        if type(row['prob']) not in (int, float) or not 0 <= row['prob'] <= previous + 1e-9:
            raise ValueError('Probabilities must be descending between 0 and 1')
        previous = row['prob']
    return result


def read(text, model, cache=CACHE):
    file = cache / f'{key_for(text, model)}.json'
    try:
        return validate(json.loads(file.read_text(encoding='utf-8')), text, model)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def visible(token):
    """Display form of a token piece; whitespace-only or control pieces are not shown as words."""
    shown = token.strip()
    return shown if shown and shown.isprintable() and len(shown) <= 20 else None


def measure(text, engine, model, cache=CACHE):
    """Top next-token probabilities after `text`, exactly as the model scores them before sampling."""
    cached = read(text, model, cache)
    if cached:
        return cached
    engine._load()
    tokens = engine._request('/tokenize', {'content': text, 'add_special': False, 'parse_special': False})['tokens']
    ids = [t['id'] if isinstance(t, dict) else t for t in tokens]
    if not 1 <= len(ids) <= 32:
        raise ValueError('Use a prompt of at most 32 tokens')
    answer = engine._request('/completion', {'prompt': ids, 'n_predict': 1, 'temperature': 0, 'seed': 42, 'stream': False,
                                             'n_probs': TOP, 'post_sampling_probs': False}, timeout=300)
    step = (answer.get('completion_probabilities') or [{}])[0]
    rows = step.get('top_logprobs') or []
    if not rows:
        raise ValueError('The installed runtime did not report next-token probabilities')
    candidates = [{'token': row['token'], 'prob': round(math.exp(row['logprob']), 6)} for row in rows[:TOP]
                  if isinstance(row.get('token'), str) and isinstance(row.get('logprob'), (int, float))]
    candidates.sort(key=lambda c: -c['prob'])
    result = validate({'mode': 'next_token', 'input': text, 'model': model, 'key': key_for(text, model), 'candidates': candidates}, text, model)
    write_json_atomic(cache / f'{result["key"]}.json', result)
    return result


def shown(result, limit=3):
    """The visible candidates and their probabilities, for the animation."""
    rows = [(visible(c['token']), c['prob']) for c in result['candidates']]
    rows = [(token, prob) for token, prob in rows if token][:limit]
    return [t for t, _ in rows], [p for _, p in rows]


def tokens_key(text, model):
    return fingerprint(['tokens-v1', text, model])


def validate_tokens(result, text=None, model=None):
    if not isinstance(result, dict) or result.get('mode') != 'tokens':
        raise ValueError('Invalid tokenization measurement')
    if text is not None and (result.get('input') != text or result.get('model') != model or result.get('key') != tokens_key(text, model)):
        raise ValueError('Tokenization belongs to another text or model')
    pieces, ids = result.get('pieces'), result.get('ids')
    if not isinstance(pieces, list) or not isinstance(ids, list) or not 1 <= len(pieces) == len(ids) <= 40:
        raise ValueError('Expected 1-40 tokens with one ID each')
    if any(not isinstance(p, str) for p in pieces) or any(type(i) is not int or i < 0 for i in ids):
        raise ValueError('Invalid token piece or ID')
    if ''.join(pieces) != result['input']:
        raise ValueError('Token pieces must rebuild the exact text')
    return result


def read_tokens(text, model, cache=CACHE):
    try:
        return validate_tokens(json.loads((cache/f'{tokens_key(text, model)}.json').read_text(encoding='utf-8')), text, model)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def measure_tokens(text, engine, model, cache=CACHE):
    """The installed model's own tokenization of `text`: pieces and IDs that rebuild it exactly."""
    cached = read_tokens(text, model, cache)
    if cached:
        return cached
    engine._load()
    rows = engine._request('/tokenize', {'content': text, 'add_special': False, 'parse_special': False, 'with_pieces': True})['tokens']
    pieces = [r['piece'] if isinstance(r['piece'], str) else bytes(r['piece']).decode('utf-8', 'replace') for r in rows]
    result = validate_tokens({'mode': 'tokens', 'input': text, 'model': model, 'key': tokens_key(text, model),
                              'pieces': pieces, 'ids': [r['id'] for r in rows]}, text, model)
    write_json_atomic(cache/f'{result["key"]}.json', result)
    return result
