#!/bin/bash
# Docker entrypoint: provisions persistent workspace venv on first run,
# then executes the original CMD.

VENV_DIR="/home/appuser/workspace/.venv"

if [ ! -d "$VENV_DIR" ]; then
    echo "Creating persistent workspace venv at $VENV_DIR ..."
    python -m venv "$VENV_DIR"
    echo "Workspace venv created."
fi

exec "$@"
