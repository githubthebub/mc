# autoedit: web UI + job worker in one container. Build from the repository root:
#   docker build -f autoedit/Dockerfile -t autoedit .
FROM ubuntu:24.04

ENV DEBIAN_FRONTEND=noninteractive PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 \
    PATH=/opt/venv/bin:$PATH \
    AUTOEDIT_PROJECTS_DIR=/data/projects \
    AUTOEDIT_MODELS_DIR=/data/models \
    AUTOEDIT_SKILL_DIR=/app/.claude/skills/video-editor \
    AUTOEDIT_PROFILES_DIR=/app/autoedit/profiles \
    HF_HOME=/data/models/hf

# ffmpeg 6.1 with libass; fonts for captions and cards; EGL/GLES for mediapipe's face detector
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 python3-venv ffmpeg fonts-dejavu-core libegl1 libgles2 libgl1 libglib2.0-0 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && python3 -m venv /opt/venv

WORKDIR /app
COPY autoedit/pyproject.toml autoedit/README.md /app/autoedit/
COPY autoedit/src /app/autoedit/src
COPY autoedit/profiles /app/autoedit/profiles
COPY .claude/skills/video-editor /app/.claude/skills/video-editor
# editable install keeps the package next to profiles/ and the skill, where it looks for them
RUN pip install -e "/app/autoedit[web]"
COPY autoedit/deploy/entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

EXPOSE 8080
VOLUME ["/data"]
ENTRYPOINT ["/app/entrypoint.sh"]
