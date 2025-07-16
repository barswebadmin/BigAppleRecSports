.PHONY: start tunnel dev stop install clean help version changelog version-bump test test-all test-unit test-integration test-services test-api test-slack test-specific

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
	@echo ""
	@echo "Testing Commands:"
	@echo "make test              - Run safe unit tests (mocked services, no external API calls)"
	@echo "make test-all          - Run all available tests (includes integration tests)"
	@echo "make test-unit         - Run unit tests only (mocked services, SAFE)"
	@echo "make test-integration  - Run integration tests (requires server)"
	@echo "make test-integration-error-codes  - Run error code HTTP tests (⚠️ may send Slack)"
	@echo "make test-integration-exceptions   - Run exception HTTP tests (⚠️ may send Slack)"
	@echo "make test-services     - Run service layer tests"
	@echo "make test-api          - Run API endpoint tests"
	@echo "make test-slack        - Run Slack message formatting tests (mocked)"
	@echo "make test-specific TEST=<test_name> - Run specific test file or test"
	@echo ""
	@echo "Examples:"
	@echo "make test-specific TEST=test_slack_message_formatting.py"
	@echo "make test-specific TEST=test_orders_api.py::test_fetch_order"
	@echo "make test-specific TEST=services/tests/test_csv_service.py"
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
	@echo "📦 Installing test dependencies..."
	pip3 install pytest pytest-asyncio pytest-mock

# Clean up
clean: stop
	@echo "🧹 Cleaning up..."
	@rm -f ngrok.log
	@rm -f *.pyc
	@rm -rf __pycache__
	@rm -rf .pytest_cache
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

# =============================================================================
# TESTING TARGETS
# =============================================================================

# Default test target - runs the most important tests
test: test-unit test-slack
	@echo "✅ Default test suite completed"

# Run all available tests
test-all: test-unit test-integration test-integration-error-codes test-integration-exceptions test-services test-api test-slack
	@echo "✅ All tests completed"

# Run unit tests (pytest-based tests) - NO external API calls
test-unit:
	@echo "🧪 Running unit tests with mocked services (no external API calls)..."
	@python3 -m pytest tests/unit/ -v
	@echo ""
	@echo "🧪 Running service-specific unit tests..."
	@python3 -m pytest services/*/tests/ -v
	@echo ""
	@echo "🧪 Running router unit tests..."
	@python3 -m pytest routers/tests/ -v
	@echo ""
	@echo "🧪 Running Slack webhook tests..."
	@python3 -m pytest routers/tests/test_slack_router.py -v

# Run integration tests (API tests that require server)
test-integration:
	@echo "🧪 Running integration tests..."
	@echo "Note: Make sure the server is running (make start)"
	@python3 -m pytest tests/integration/ -v

# Run error code integration tests (HTTP endpoint tests)
test-integration-error-codes:
	@echo "🧪 Running error code integration tests (requires running server)..."
	@echo "Note: These tests make actual HTTP requests and may send to Slack"
	@python3 -m pytest tests/integration/test_error_codes.py -v

# Run exception handling integration tests (HTTP requests)
test-integration-exceptions:
	@echo "🧪 Running exception handling integration tests..."
	@echo "⚠️  Note: These make real HTTP requests and may send Slack messages"
	@python3 tests/integration/test_mute_exceptions.py
	@echo ""
	@echo "🧪 Running sheet link tests..."
	@python3 tests/integration/test_sheet_link.py

# Run service layer tests
test-services:
	@echo "🧪 Running service layer tests..."
	@python3 -m pytest services/tests/ -v

# Run API endpoint tests
test-api:
	@echo "🧪 Running API endpoint tests..."
	@cd routers && python3 test_leadership_router.py
	@echo ""
	@echo "🧪 Testing live API endpoints..."
	@echo "Testing root endpoint:"
	@curl -s http://127.0.0.1:8000/ | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" || echo "❌ Server not running"
	@echo ""
	@echo "Testing leadership health:"
	@curl -s http://127.0.0.1:8000/leadership/health | python3 -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" || echo "❌ Server not running"

# Run Slack message formatting tests
test-slack:
	@echo "🧪 Running Slack message formatting tests..."
	@python3 run_slack_tests.py

# Run Slack webhook router tests
test-slack-webhook:
	@echo "🧪 Running Slack webhook router tests..."
	@python3 run_slack_webhook_tests.py

# Run ALL Slack tests (webhook + message formatting)
test-slack-all:
	@echo "🧪 Running ALL Slack tests..."
	@python3 run_slack_webhook_tests.py --all

# Run specific test file or test case
test-specific:
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Please specify a test to run: make test-specific TEST=<test_name>"; \
		echo "Examples:"; \
		echo "  make test-specific TEST=test_slack_message_formatting.py"; \
		echo "  make test-specific TEST=test_orders_api.py::test_fetch_order"; \
		echo "  make test-specific TEST=services/tests/test_csv_service.py"; \
		exit 1; \
	fi
	@echo "🧪 Running specific test: $(TEST)"
	@if echo "$(TEST)" | grep -q "::"; then \
		echo "Running pytest test case: $(TEST)"; \
		python3 -m pytest "$(TEST)" -v; \
	elif echo "$(TEST)" | grep -q "test_slack_message_formatting.py"; then \
		echo "Running Slack formatting tests..."; \
		python3 -m pytest "$(TEST)" -v; \
	elif echo "$(TEST)" | grep -q "\.py$$"; then \
		echo "Running Python test file: $(TEST)"; \
		python3 "$(TEST)"; \
	else \
		echo "❌ Invalid test format. Use .py file or pytest::test_name format"; \
		exit 1; \
	fi

# Quick test - just the most critical tests
test-quick:
	@echo "🧪 Running quick tests..."
	@python3 -m pytest test_error_codes_unit.py -v
	@python3 -m pytest test_slack_message_formatting.py::TestSlackMessageFormatting::test_sport_group_mentions -v

# Test with coverage (requires coverage package)
test-coverage:
	@echo "🧪 Running tests with coverage..."
	@python3 -m pip install coverage 2>/dev/null || true
	@python3 -m coverage run -m pytest test_slack_message_formatting.py
	@python3 -m coverage report
	@python3 -m coverage html
	@echo "📊 Coverage report generated in htmlcov/"

# Watch mode for tests (requires pytest-watch)
test-watch:
	@echo "🧪 Running tests in watch mode..."
	@python3 -m pip install pytest-watch 2>/dev/null || true
	@python3 -m ptw test_slack_message_formatting.py

# =============================================================================
# EXISTING TARGETS (preserved for backward compatibility)
# =============================================================================

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