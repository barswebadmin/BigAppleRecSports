# Install/sync backend dependencies
sync-backend:
    uv sync --project backend





# Start backend dev server with hot reload
start:
    uv run --directory backend uvicorn main:app --reload --host 0.0.0.0 --port 8000
