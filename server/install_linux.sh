#!/usr/bin/env bash
# Install VisualForge AI for headless video generation on Ubuntu/Debian x64 (a server, a Docker
# image or a Kaggle notebook). Usage:
#   bash server/install_linux.sh            # CPU language model
#   bash server/install_linux.sh --cuda     # NVIDIA GPU language model (llama.cpp CUDA 12.8 build)
# Set SKIP_MODELS=1 to install only the code dependencies (models can be added later by running
# backend/scripts/download_models.py and backend/scripts/setup_gguf.py).
set -euo pipefail
cd "$(dirname "$0")/.."
FLAVOR=cpu
[[ "${1:-}" == "--cuda" ]] && FLAVOR=cuda
SUDO=""
[[ "$(id -u)" -ne 0 ]] && SUDO="sudo"
UV_VERSION=0.12.22
NODE_MAJOR=22

echo "== System libraries: OpenMP for llama.cpp, headless Chrome for Remotion =="
packages="curl unzip ca-certificates libgomp1 libnss3 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 libgbm1 libxrandr2 libxkbcommon0
  libxfixes3 libxcomposite1 libxdamage1 libpango-1.0-0 libcairo2 libcups2 libdrm2 libxshmfence1 libasound2 libasound2t64"
$SUDO apt-get update -qq
# Package names differ between releases (libasound2 became libasound2t64), so install what exists.
available=""
for p in $packages; do
  # A package that is listed but has "Candidate: (none)" cannot be installed.
  if apt-cache policy "$p" 2>/dev/null | grep 'Candidate: [^(]' >/dev/null; then available="$available $p"; fi
done
$SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq $available >/dev/null

echo "== Node.js $NODE_MAJOR =="
if ! command -v node >/dev/null || [[ "$(node -p 'process.versions.node.split(".")[0]')" -lt 20 ]]; then
  curl -fsSL "https://deb.nodesource.com/setup_${NODE_MAJOR}.x" | $SUDO bash - >/dev/null
  $SUDO env DEBIAN_FRONTEND=noninteractive apt-get install -y -qq nodejs >/dev/null
fi
node --version

echo "== Python 3.12 environment (uv $UV_VERSION) =="
if ! command -v uv >/dev/null; then
  curl -LsSf "https://astral.sh/uv/$UV_VERSION/install.sh" | sh >/dev/null
  export PATH="$HOME/.local/bin:$PATH"
fi
uv venv --quiet --python 3.12 backend/.venv
# requirements.txt adds the PyTorch CPU index for torch only; like pip, take each package from the
# index that has the pinned version (uv otherwise stops at the first index listing a name).
uv pip install --quiet --index-strategy unsafe-best-match --python backend/.venv/bin/python -r backend/requirements.txt

echo "== Renderer packages and headless Chrome =="
(cd renderer && npm ci --no-audit --no-fund --loglevel=error && npx remotion browser ensure)

if [[ "${SKIP_MODELS:-0}" != "1" ]]; then
  echo "== Models: Kokoro voice, Qwen3 4B, bge-small, llama.cpp $FLAVOR runtime =="
  backend/.venv/bin/python backend/scripts/download_models.py
  backend/.venv/bin/python backend/scripts/setup_gguf.py $([[ "$FLAVOR" == "cuda" ]] && echo --cuda)
fi
echo "== Ready. Make a video with: backend/.venv/bin/python backend/scripts/make_video.py --script lesson.txt --out output/"
