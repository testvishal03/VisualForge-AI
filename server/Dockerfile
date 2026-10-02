# Headless VisualForge AI on Linux. Build from the project root:
#   docker build -f server/Dockerfile -t visualforge .                       # CPU
#   docker build -f server/Dockerfile --build-arg FLAVOR=cuda -t visualforge-gpu .
# Then:  docker run --rm -v "$PWD/output:/app/output" -v "$PWD/lesson.txt:/app/lesson.txt:ro" visualforge \
#          --script lesson.txt --out output/
# For the GPU image add --gpus all and -e VISUALFORGE_GPU_LAYERS=99 -e VISUALFORGE_PLANNING_LIMIT=999.
FROM ubuntu:24.04
ARG FLAVOR=cpu
ARG SKIP_MODELS=0
ENV DEBIAN_FRONTEND=noninteractive PATH="/root/.local/bin:$PATH" PYTHONUNBUFFERED=1
RUN apt-get update -qq && apt-get install -y -qq curl ca-certificates >/dev/null && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY . /app
RUN SKIP_MODELS=$SKIP_MODELS bash server/install_linux.sh $([ "$FLAVOR" = "cuda" ] && echo --cuda) && rm -rf /root/.cache
ENTRYPOINT ["backend/.venv/bin/python", "backend/scripts/make_video.py"]
