#!/bin/sh
# Persistent state lives on the /data volume: projects, the job queue, downloaded models, and the
# music/SFX/avatar libraries (the profiles point at ~/autoedit-assets, linked here to /data/assets).
set -e
mkdir -p /data/projects /data/models /data/assets
if [ ! -e "$HOME/autoedit-assets" ]; then ln -s /data/assets "$HOME/autoedit-assets"; fi
if [ -z "$AUTOEDIT_PASSWORD" ]; then
  echo "AUTOEDIT_PASSWORD is not set: run  fly secrets set AUTOEDIT_PASSWORD=..." >&2
  exit 1
fi
if [ -z "$ANTHROPIC_API_KEY" ]; then
  echo "warning: ANTHROPIC_API_KEY is not set; plans fall back to dead-air removal only" >&2
fi
exec autoedit serve --host 0.0.0.0 --port "${PORT:-8080}" --with-worker
