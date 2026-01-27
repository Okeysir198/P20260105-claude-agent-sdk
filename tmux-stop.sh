#!/bin/bash
# Stop backend and frontend tmux sessions

tmux kill-session -t claude_sdk_backend 2>/dev/null && echo "Stopped claude-backend"
tmux kill-session -t claude_sdk_frontend 2>/dev/null && echo "Stopped claude-frontend"
