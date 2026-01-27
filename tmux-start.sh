#!/bin/bash
# Start backend and frontend in tmux sessions

SESSION_BACKEND="claude_sdk_backend"
SESSION_FRONTEND="claude_sdk_frontend"

# Kill existing sessions
tmux kill-session -t $SESSION_BACKEND 2>/dev/null
tmux kill-session -t $SESSION_FRONTEND 2>/dev/null

# Backend session
tmux new-session -d -s $SESSION_BACKEND -c backend
tmux send-keys -t $SESSION_BACKEND "source .venv/bin/activate && python main.py serve" Enter

# Frontend session
tmux new-session -d -s $SESSION_FRONTEND -c frontend
tmux send-keys -t $SESSION_FRONTEND "npm run dev" Enter

echo "Started tmux sessions:"
echo "  - $SESSION_BACKEND (backend on port 7001)"
echo "  - $SESSION_FRONTEND (frontend on port 7002)"
echo ""
echo "Attach: tmux attach -t $SESSION_BACKEND"
echo "Attach: tmux attach -t $SESSION_FRONTEND"
echo "List:   tmux ls"
