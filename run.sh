#!/usr/bin/env bash
export PATH="/opt/homebrew/opt/postgresql@17/bin:$PATH"
export PYTHONPATH="."
source .venv/bin/activate 2>/dev/null || true
exec uvicorn frontend.app:app --host 0.0.0.0 --port "${PORT:-8000}" --reload
