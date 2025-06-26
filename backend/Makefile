.PHONY: start tunnel dev stop install clean help version changelog version-bump

# Default target
help:
	@echo "🚀 Big Apple Rec Sports Backend Commands"
	@echo "========================================="
	@echo "make start    - Start the backend server"
	@echo "make tunnel   - Start ngrok tunnel"
	@echo "make dev      - Start both server and tunnel (in background)"
	@echo "make stop     - Stop all running processes"
	@echo "make install  - Install Python dependencies"
	@echo "make clean    - Clean up processes and logs"
	@echo "make test         - Test the API endpoints"
	@echo "make test-services - Test service layer functionality"
	@echo "make test-api     - Test API integration endpoints"
	@echo ""
	@echo "Version Management:"
	@echo "make version      - Show current version information"
	@echo "make changelog    - View recent changelog entries"
	@echo "make version-bump - Manually trigger version management (for testing)"
	@echo ""
	@echo "Quick Start:"
	@echo "1. Run 'make start' in one terminal"
	@echo "2. Run 'make tunnel' in another terminal"
	@echo "3. Use the ngrok URL in your Google Apps Script"

# Start the backend server
start:
	@echo "🚀 Starting backend server..."
	python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

# Start ngrok tunnel (kills existing first)
tunnel:
	@echo "🌐 Starting ngrok tunnel..."
	@pkill -f ngrok || true
	@sleep 1
	ngrok http 8000

# Development mode - start both server and tunnel
dev:
	@echo "🔧 Starting development environment..."
	@pkill -f ngrok || true
	@pkill -f uvicorn || true
	@sleep 1
	@python3 -m uvicorn main:app --reload --host 127.0.0.1 --port 8000 &
	@sleep 3
	@ngrok http 8000 &
	@echo "✅ Server and tunnel starting in background..."
	@echo "📝 Check processes with: make status"

# Stop all processes
stop:
	@echo "🛑 Stopping all processes..."
	@pkill -f ngrok || true
	@pkill -f uvicorn || true
	@echo "✅ All processes stopped"

# Install dependencies
install:
	@echo "📦 Installing dependencies..."
	pip3 install -r requirements.txt

# Clean up
clean: stop
	@echo "🧹 Cleaning up..."
	@rm -f ngrok.log
	@rm -f *.pyc
	@rm -rf __pycache__
	@echo "✅ Cleanup complete"

# Test API endpoints
test:
	@echo "🧪 Testing API endpoints..."
	@echo "Testing root endpoint:"
	@curl -s http://127.0.0.1:8000/ | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" || echo "❌ Server not running"
	@echo ""
	@echo "Testing leadership health:"
	@curl -s http://127.0.0.1:8000/leadership/health | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" || echo "❌ Server not running"

# Test services
test-services:
	@echo "🧪 Testing services..."
	@cd services && python3 test_csv_service.py
	@echo ""
	@cd services && python3 test_leadership_service.py

# Test API endpoints
test-api:
	@echo "🧪 Testing API endpoints..."
	@cd routers && python3 test_leadership_router.py

# Show running processes
status:
	@echo "📊 Process Status:"
	@echo "Backend Server:"
	@ps aux | grep uvicorn | grep -v grep || echo "❌ Backend server not running"
	@echo ""
	@echo "Ngrok Tunnel:"
	@ps aux | grep ngrok | grep -v grep || echo "❌ Ngrok tunnel not running"
	@echo ""
	@echo "Ngrok URL (if running):"
	@curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '❌ No tunnels')" 2>/dev/null || echo "❌ Ngrok not accessible"

# Get ngrok URL
url:
	@curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data=json.load(sys.stdin); print('🌐 Ngrok URL:', data['tunnels'][0]['public_url']) if data.get('tunnels') else print('❌ No ngrok tunnel running')" 2>/dev/null || echo "❌ Ngrok not accessible"

# Version Management Commands
version:
	@echo "📈 Backend Version Information:"
	@echo "=============================="
	@python3 -c "from version import get_version_info; info = get_version_info(); print(f'Version: {info[\"version\"]}'); print(f'Build: {info[\"build\"]}'); print(f'Full: {info[\"full_version\"]}'); print(f'Updated: {info[\"last_updated\"]}'); print(f'Codename: {info[\"codename\"]}')"

changelog:
	@echo "📝 Recent Changelog Entries:"
	@echo "============================="
	@head -50 CHANGELOG.md

version-bump:
	@echo "🔄 Manually triggering version management..."
	@python3 ../scripts/backend_version_manager.py 