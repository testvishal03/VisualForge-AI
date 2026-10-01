"""Install a pinned Windows CPU runtime, the Qwen GGUF and a small embedding model inside this project."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import zipfile
import time
import re
import os
import importlib.util
from concurrent.futures import ThreadPoolExecutor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from backend.llm.gguf_llm import CONFIG, MODEL_FILE, MODEL_REVISION, MODEL_SHA256
from backend.services import embeddings

RUNTIME = 'b11206'
ARCHIVE_SHA256 = 'c17f1e3233fc5f5b8915472affa939adee0c95785882503b106d5b14aba01002'


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def download_chunks(url, partial, size):
    """Bounded transfers with resumable chunks; final SHA-256 remains authoritative."""
    chunk_size = 32 * 1024 * 1024
    folder = partial.with_suffix('.chunks')
    folder.mkdir(parents=True, exist_ok=True)
    def fetch(index):
        start, end = index * chunk_size, min(size, (index + 1) * chunk_size) - 1
        chunk = folder / f'{index:04d}.part'
        failures = 0
        while failures < 4:
            have = chunk.stat().st_size if chunk.exists() else 0
            if have == end - start + 1:
                return chunk
            if have > end - start + 1:
                raise ValueError(f'Oversized download chunk: {chunk}')
            try:
                offset = start + have
                block_end = min(end, offset + 2 * 1024 * 1024 - 1)
                transfer = chunk.with_suffix('.transfer')
                headers = chunk.with_suffix('.headers')
                result = subprocess.run(['curl.exe', '--fail', '--location', '--silent', '--show-error',
                    '--range', f'{offset}-{block_end}', '--connect-timeout', '20', '--max-time', '90',
                    '--speed-time', '30', '--speed-limit', '1024', '--output', str(transfer),
                    '--dump-header', str(headers), '--write-out', '%{http_code}',
                    url + f'?download=true&vf_range={offset}-{block_end}'],
                    capture_output=True, text=True)
                ranges = re.findall(r'content-range:\s*bytes (\d+)-(\d+)/(\d+)', headers.read_text(errors='replace'), re.I)
                if result.stdout.strip() != '206' or not ranges or tuple(map(int, ranges[-1])) != (offset, block_end, size):
                    raise OSError(f'Range download failed: {result.stderr[-300:]}')
                if not 0 < transfer.stat().st_size <= block_end - offset + 1:
                    raise ValueError('Download host did not return the requested byte count')
                with chunk.open('ab') as stream, transfer.open('rb') as source:
                    while data := source.read(1024 * 1024):
                        stream.write(data)
                transfer.unlink()
                headers.unlink()
                failures = 0
                if chunk.stat().st_size == end - start + 1:
                    print(f'Download chunk {index + 1}/{(size + chunk_size - 1) // chunk_size} complete', flush=True)
                    return chunk
            except (OSError, ValueError):
                failures += 1
                if failures == 4:
                    raise
                time.sleep(2)
        raise RuntimeError(f'Incomplete download chunk {index}')
    # Preserve completed bytes from an interrupted single-connection download.
    if partial.exists():
        with partial.open('rb') as source:
            for index in range(partial.stat().st_size // chunk_size):
                chunk = folder / f'{index:04d}.part'
                data = source.read(chunk_size)
                if not chunk.exists():
                    chunk.write_bytes(data)
    with ThreadPoolExecutor(max_workers=8) as pool:
        chunks = list(pool.map(fetch, range((size + chunk_size - 1) // chunk_size)))
    with partial.open('wb') as target:
        for chunk in chunks:
            with chunk.open('rb') as source:
                while data := source.read(1024 * 1024):
                    target.write(data)
    return chunks


def download(url, path, expected, size=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file() and digest(path) == expected:
        print(f'Verified cached {path.name}', flush=True)
        return
    partial = path.with_suffix(path.suffix + '.partial')
    print(f'Downloading {path.name}', flush=True)
    chunks = []
    if size:
        chunks = download_chunks(url, partial, size)
    else:
        subprocess.run(['curl.exe', '--fail', '--location', '--retry', '3', '--connect-timeout', '30',
                        '--max-time', '7200', '--continue-at', '-', '--output', str(partial), url], check=True)
    if digest(partial) != expected:
        raise ValueError(f'Checksum mismatch: {partial}. The model has not been activated.')
    partial.replace(path)
    for chunk in chunks:
        chunk.unlink()


def main():
    if sys.platform != 'win32':
        raise ValueError('This installer pins the Windows x64 CPU build.')
    cache = ROOT / 'backend/.cache/llama.cpp' / RUNTIME
    archive = cache / f'llama-{RUNTIME}-bin-win-cpu-x64.zip'
    download(f'https://github.com/ggml-org/llama.cpp/releases/download/{RUNTIME}/{archive.name}', archive, ARCHIVE_SHA256)
    with zipfile.ZipFile(archive) as bundle:
        for info in bundle.infolist():
            if not (cache / info.filename).resolve().is_relative_to(cache.resolve()):
                raise ValueError('Unexpected path in runtime archive')
        bundle.extractall(cache)
    server = next(cache.rglob('llama-server.exe'))
    model = ROOT / 'backend/models' / MODEL_FILE
    if model.is_file() and digest(model) == MODEL_SHA256:
        print('Verified cached GGUF model', flush=True)
    elif '--http' not in sys.argv and importlib.util.find_spec('hf_xet'):
        os.environ['HF_HOME'] = str(ROOT / 'backend/.cache/huggingface')
        os.environ['HF_XET_CACHE'] = str(ROOT / 'backend/.cache/xet')
        os.environ['HF_HUB_DISABLE_XET'] = '0'
        os.environ['HF_HUB_DISABLE_TELEMETRY'] = '1'
        os.environ['HF_XET_NUM_CONCURRENT_RANGE_GETS'] = '8'
        from huggingface_hub import hf_hub_download
        print('Downloading with Hugging Face Xet; HTTP chunks remain available with --http.', flush=True)
        staged = Path(hf_hub_download('unsloth/Qwen3-4B-Instruct-2507-GGUF', MODEL_FILE,
                       revision=MODEL_REVISION, local_dir=ROOT / 'backend/.cache/gguf-download', token=False))
        if digest(staged) != MODEL_SHA256:
            raise ValueError('GGUF checksum mismatch; model was not activated.')
        model.parent.mkdir(parents=True, exist_ok=True)
        staged.replace(model)
    else:
        download(f'https://huggingface.co/unsloth/Qwen3-4B-Instruct-2507-GGUF/resolve/{MODEL_REVISION}/{MODEL_FILE}', model, MODEL_SHA256, 2497281120)
    # bge-small-en-v1.5 (MIT, 37 MB) measures the embedding-map explainer.
    download(embeddings.MODEL_URL, embeddings.MODEL_PATH, embeddings.MODEL_SHA256)
    subprocess.run([str(server), '--version'], check=True, timeout=30,
                   creationflags=subprocess.CREATE_NO_WINDOW)
    config = {'backend': 'gguf', 'model': model.relative_to(ROOT).as_posix(),
              'server': server.relative_to(ROOT).as_posix(), 'runtime_version': RUNTIME,
              'model_sha256': MODEL_SHA256}
    temp = CONFIG.with_suffix('.tmp')
    temp.write_text(json.dumps(config, indent=2) + '\n', encoding='utf-8')
    temp.replace(CONFIG)
    print(f'GGUF CPU profile activated: {CONFIG}', flush=True)


if __name__ == '__main__':
    main()
