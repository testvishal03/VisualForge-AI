"""Owned, loopback-only llama.cpp worker for quantized CPU inference."""
import atexit
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import time
from urllib.request import Request, build_opener, ProxyHandler

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / 'backend/models/local-model.json'
MODEL_NAME = 'Qwen/Qwen3-4B-Instruct-2507'
MODEL_REVISION = 'a06e946bb6b655725eafa393f4a9745d460374c9'
MODEL_FILE = 'Qwen3-4B-Instruct-2507-Q4_K_M.gguf'
MODEL_SHA256 = '3605803b982cb64aead44f6c1b2ae36e3acdb41d8e46c8a94c6533bc4c67e597'


class GGUFLLM:
    def __init__(self, *, offline=False, threads=2, on_progress=None, config=None):
        if not 1 <= threads <= 8:
            raise ValueError('CPU threads must be between 1 and 8.')
        self.config = config if config is not None else json.loads(CONFIG.read_text(encoding='utf-8'))
        self.threads, self.on_progress = threads, on_progress
        self.model = None
        self.process = None
        self.log = None
        self.load_seconds = self.last_generation_seconds = self.last_token_count = 0
        self.model_name = MODEL_NAME
        self.metadata = {'model': MODEL_NAME, 'revision': MODEL_REVISION, 'device': 'cpu',
                         'dtype': 'Q4_K_M', 'backend': 'llama.cpp', 'context': 4096,
                         'model_sha256': MODEL_SHA256, 'runtime': self.config.get('runtime_version')}
        self.cache_identity = dict(self.metadata)
        self.key = secrets.token_urlsafe(32)
        self.http = build_opener(ProxyHandler({}))

    def _request(self, route, payload=None, timeout=10):
        req = Request(self.url + route, data=json.dumps(payload).encode() if payload is not None else None,
                      headers={'Content-Type': 'application/json', 'Authorization': 'Bearer ' + self.key})
        with self.http.open(req, timeout=timeout) as response:
            return json.load(response)

    def _load(self):
        if self.process is not None and self.process.poll() is None:
            return
        self.close()
        executable = ROOT / self.config['server']
        model = ROOT / self.config['model']
        if not executable.is_file() or not model.is_file():
            raise RuntimeError('GGUF runtime or model missing. Run backend/scripts/setup_gguf.py to install locally.')
        with socket.socket() as sock:
            sock.bind(('127.0.0.1', 0))
            port = sock.getsockname()[1]
        self.url = f'http://127.0.0.1:{port}'
        log_path = ROOT / 'backend/.cache' / f'llama-{os.getpid()}.log'
        log_path.parent.mkdir(parents=True, exist_ok=True)
        self.log = log_path.open('w', encoding='utf-8')
        started = time.perf_counter()
        if self.on_progress:
            self.on_progress('Loading Qwen3 4B Q4_K_M with llama.cpp (CPU, 4096-token context)...')
        try:
            self.process = subprocess.Popen([
                str(executable), '-m', str(model), '--host', '127.0.0.1', '--port', str(port),
                '-c', '4096', '-t', str(self.threads), '-tb', str(self.threads), '-ngl', '0',
                '-np', '1', '-b', '256', '-ub', '128', '--api-key', self.key,
                '--no-webui', '--no-context-shift',
            ], stdout=self.log, stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            atexit.register(self.close)
            while time.perf_counter() - started < 180:
                if self.process.poll() is not None:
                    raise RuntimeError(f'llama.cpp exited during startup. See {log_path}')
                try:
                    if self._request('/health', timeout=2).get('status') == 'ok':
                        self.load_seconds = time.perf_counter() - started
                        return
                except (OSError, ValueError):
                    pass
                time.sleep(.25)
            raise TimeoutError(f'llama.cpp startup timed out. See {log_path}')
        except BaseException:
            self.close()
            raise

    def generate(self, prompt, max_new_tokens=1800, temperature=0.0):
        return self.generate_json(prompt, max_new_tokens, temperature)

    def _record_memory(self):
        if os.name != 'nt' or self.process is None:
            return
        import ctypes
        from ctypes import wintypes
        class Counters(ctypes.Structure):
            _fields_ = [('cb', wintypes.DWORD), ('faults', wintypes.DWORD)] + [
                (key, ctypes.c_size_t) for key in ('peak', 'working', 'peakPaged', 'paged',
                'peakNonPaged', 'nonPaged', 'pagefile', 'peakPagefile')]
        stats = Counters()
        stats.cb = ctypes.sizeof(stats)
        api = ctypes.WinDLL('psapi', use_last_error=True).GetProcessMemoryInfo
        api.argtypes = [wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        if api(int(self.process._handle), ctypes.byref(stats), stats.cb):
            self.metadata['inference_peak_working_set_bytes'] = stats.peak

    def generate_json(self, prompt, max_new_tokens=1800, temperature=0.0, schema=None):
        if not 128 <= max_new_tokens <= 3000 or not 0 <= temperature <= 1:
            raise ValueError('Use 128-3000 new tokens and temperature between 0 and 1.')
        self._load()
        from backend.llm.prompts import SYSTEM_PROMPT
        payload = {'messages': [{'role': 'system', 'content': SYSTEM_PROMPT},
                                {'role': 'user', 'content': prompt}],
                   'max_tokens': max_new_tokens, 'temperature': temperature, 'seed': 42,
                   'stream': False, 'response_format': {'type': 'json_object'}}
        if schema is not None:
            payload['response_format'] = {'type': 'json_object', 'schema': schema}
        started = time.perf_counter()
        try:
            result = self._request('/v1/chat/completions', payload, timeout=900)
            self._record_memory()
            self.last_generation_seconds = time.perf_counter() - started
            self.last_token_count = result.get('usage', {}).get('completion_tokens', 0)
            choice = result['choices'][0]
            if choice.get('finish_reason') == 'length':
                raise ValueError('Model reached its output token limit; reduce the requested content.')
            text = choice['message']['content']
            if not isinstance(text, str) or not text.strip():
                raise ValueError('The model generated no text.')
            return text.strip()
        except Exception as exc:
            raise RuntimeError(f'Local GGUF generation failed: {exc}') from exc

    def close(self):
        atexit.unregister(self.close)
        if self.process is not None:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=10)
            self.process = None
        if self.log is not None:
            self.log.close()
            self.log = None


def create_local_llm(**kwargs):
    """Saved configuration applies to every studio worker; explicit legacy override."""
    backend = os.environ.get('VISUALFORGE_LLM', 'gguf' if CONFIG.is_file() else 'transformers')
    if backend == 'gguf':
        return GGUFLLM(**kwargs)
    if backend != 'transformers':
        raise ValueError('VISUALFORGE_LLM must be gguf or transformers.')
    from backend.llm.local_llm import LocalLLM
    return LocalLLM(**kwargs)


def model_status():
    """Inspect configuration without loading weights or starting a server."""
    backend = os.environ.get('VISUALFORGE_LLM', 'gguf' if CONFIG.is_file() else 'transformers')
    if backend == 'transformers':
        from backend.llm.local_llm import MODEL_NAME as legacy, MODEL_REVISION as revision
        return {'model': legacy, 'revision': revision, 'backend': backend, 'label': 'Qwen2.5 1.5B · CPU'}
    if backend != 'gguf':
        raise ValueError('VISUALFORGE_LLM must be gguf or transformers.')
    config = json.loads(CONFIG.read_text(encoding='utf-8'))
    return {'model': MODEL_NAME, 'revision': MODEL_REVISION, 'backend': backend,
            'runtime': config['runtime_version'], 'quantization': 'Q4_K_M',
            'ready': all((ROOT / config[key]).is_file() for key in ('server', 'model')),
            'label': 'Qwen3 4B · Q4_K_M · CPU'}
