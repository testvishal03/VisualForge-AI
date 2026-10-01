"""Measured embedding maps from a small local sentence-embedding model (bge-small-en-v1.5).

The installed llama.cpp runtime serves the model in embedding mode. A map measurement keeps
the exact labels, the model identity, every pairwise cosine similarity and a 2D layout made
by classical multidimensional scaling of the cosine distances, so the drawn distances follow
the real vectors as closely as two dimensions allow. Without the model the map stays in its
labelled illustrative form.
"""
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
from urllib.request import ProxyHandler, Request, build_opener

from backend.services.run_state import fingerprint
from backend.services.script_generator import write_json_atomic

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / 'data/embedding-cache'
MODEL_NAME = 'bge-small-en-v1.5'
MODEL_REPO = 'CompendiumLabs/bge-small-en-v1.5-gguf'
MODEL_REVISION = 'd32f8c040ea3b516330eeb75b72bcc2d3a780ab7'
MODEL_FILE = 'bge-small-en-v1.5-q8_0.gguf'
MODEL_SHA256 = 'ec38e8da142596baa913124ae50550de284b6916bf59577ef2f0cb9660c2f514'
MODEL_PATH = ROOT / 'backend/models/embeddings' / MODEL_FILE
MODEL_URL = f'https://huggingface.co/{MODEL_REPO}/resolve/{MODEL_REVISION}/{MODEL_FILE}'
IDENTITY = f'{MODEL_NAME}-q8_0@{MODEL_SHA256[:12]}'


def installed():
    return MODEL_PATH.is_file()


class EmbeddingModel:
    """A loopback-only llama.cpp server for the embedding model, started on first use."""

    def __init__(self, server=None, threads=2):
        if server is None:
            from backend.llm.gguf_llm import CONFIG
            server = ROOT / json.loads(CONFIG.read_text(encoding='utf-8'))['server']
        self.server, self.threads = Path(server), threads
        self.process = self.log = None
        self.key = secrets.token_urlsafe(32)
        self.http = build_opener(ProxyHandler({}))

    def _request(self, route, payload=None, timeout=60):
        req = Request(self.url + route, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        with self.http.open(req, timeout=timeout) as response:
            return json.load(response)

    def _load(self):
        if self.process is not None and self.process.poll() is None:
            return
        if not self.server.is_file() or not installed():
            raise RuntimeError('Embedding model missing. Run backend/scripts/setup_gguf.py to install it.')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        self.url = f'http://127.0.0.1:{port}'
        log_path = ROOT / 'backend/.cache' / f'embeddings-{os.getpid()}.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = log_path.open('w', encoding='utf-8')
        self.process = subprocess.Popen([
            str(self.server), '-m', str(MODEL_PATH), '--host', '127.0.0.1', '--port', str(port),
            '--embeddings', '--pooling', 'cls', '-c', '512', '-t', str(self.threads), '-ngl', '0',
            '--api-key', self.key, '--no-webui',
        ], stdout=self.log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
        started = time.perf_counter()
        while time.perf_counter() - started < 60:
            if self.process.poll() is not None:
                self.close()
                raise RuntimeError(f'The embedding server exited during startup. See {log_path}')
            try:
                if self._request('/health', timeout=2).get('status') == 'ok':
                    return
            except (OSError, ValueError):
                pass
            time.sleep(.2)
        self.close()
        raise TimeoutError(f'The embedding server did not start. See {log_path}')

    def embed(self, texts):
        """Unit-length vectors, one per text, in order."""
        import numpy as np
        self._load()
        rows = sorted(self._request('/v1/embeddings', {'input': list(texts)})['data'], key=lambda r: r['index'])
        vectors = np.array([r['embedding'] for r in rows], dtype=float)
        if vectors.shape[0] != len(texts) or not vectors.size:
            raise ValueError('The embedding server returned the wrong number of vectors')
        return vectors / np.linalg.norm(vectors, axis=1, keepdims=True)

    def close(self):
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None


def layout(similarity):
    """2D positions by classical MDS of cosine distance, centred, with the widest spread along x.

    Coordinates share one scale (the larger axis spans 1), so relative distances are kept.
    """
    import numpy as np
    s = np.asarray(similarity, dtype=float)
    d2 = (1 - s) ** 2
    n = len(s)
    j = np.eye(n) - np.ones((n, n)) / n
    values, vectors = np.linalg.eigh(-.5 * j @ d2 @ j)
    top = np.argsort(values)[::-1][:2]
    xy = vectors[:, top] * np.sqrt(np.clip(values[top], 0, None))
    # A fixed orientation, so the same measurement always draws the same way.
    for axis in range(2):
        if xy[0, axis] > 0:
            xy[:, axis] *= -1
    span = max(np.ptp(xy[:, 0]), np.ptp(xy[:, 1]), 1e-9)
    xy = (xy - (xy.max(axis=0) + xy.min(axis=0)) / 2) / span
    return [[round(float(x), 4), round(float(y), 4)] for x, y in xy]


def nearest_links(similarity):
    """Each point joined to its most similar neighbour; pairs listed once, by first index."""
    links = {}
    for a, row in enumerate(similarity):
        b = max((j for j in range(len(row)) if j != a), key=lambda j: row[j])
        links[tuple(sorted((a, b)))] = round(float(row[b]), 3)
    return [{'a': a, 'b': b, 'sim': sim} for (a, b), sim in sorted(links.items())]


def key_for(labels, model=IDENTITY):
    return fingerprint(['embedding-map-v1', list(labels), model])


def validate(result, labels=None, model=IDENTITY):
    if not isinstance(result, dict) or result.get('mode') != 'embedding_map':
        raise ValueError('Invalid embedding measurement')
    if labels is not None and (result.get('labels') != list(labels) or result.get('model') != model or result.get('key') != key_for(labels, model)):
        raise ValueError('Measurement belongs to other labels or another model')
    n = len(result.get('labels') or [])
    sims, xy = result.get('similarity'), result.get('xy')
    if not 2 <= n <= 8 or not isinstance(sims, list) or len(sims) != n or not isinstance(xy, list) or len(xy) != n:
        raise ValueError('Expected 2-8 labels with a similarity row and a position each')
    for i, row in enumerate(sims):
        if not isinstance(row, list) or len(row) != n or any(type(v) not in (int, float) or not -1.001 <= v <= 1.001 for v in row) or abs(row[i] - 1) > .01:
            raise ValueError('Invalid similarity matrix')
    if any(not isinstance(p, list) or len(p) != 2 or any(type(v) not in (int, float) or abs(v) > .51 for v in p) for p in xy):
        raise ValueError('Invalid map positions')
    return result


def read(labels, cache=CACHE, model=IDENTITY):
    try:
        return validate(json.loads((cache / f'{key_for(labels, model)}.json').read_text(encoding='utf-8')), labels, model)
    except (OSError, ValueError, KeyError, TypeError):
        return None


def measure(labels, embedder, cache=CACHE, model=IDENTITY):
    """Similarities and a 2D layout for `labels`, from the model's own vectors; cached per model."""
    labels = list(labels)
    cached = read(labels, cache, model)
    if cached:
        return cached
    vectors = embedder.embed(labels)
    similarity = [[round(float(v), 4) for v in row] for row in vectors @ vectors.T]
    result = validate({'mode': 'embedding_map', 'labels': labels, 'model': model, 'key': key_for(labels, model),
                       'similarity': similarity, 'xy': layout(similarity)}, labels, model)
    write_json_atomic(cache / f'{result["key"]}.json', result)
    return result
