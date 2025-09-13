# BigAppleRecSports

## 📦 Installation

### Quick Setup
```bash
# Install all dependencies
make install

# Start development server
make start
```

### Installation Options
```bash
# Development (all dependencies)
make install

# Production only
make install-prod

# Manual installation
pip install -r requirements.txt
```

### Dependencies
All project dependencies are managed in the root `requirements.txt` file, organized by:
- **Backend**: FastAPI, uvicorn, requests, pydantic
- **Testing**: pytest, pytest-asyncio, httpx
- **Lambda Functions**: typing-extensions (most use standard library)
- **Google Apps Scripts**: No Python dependencies (uses GAS runtime)
