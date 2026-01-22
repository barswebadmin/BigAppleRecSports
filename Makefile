# BARS Repository Makefile
# Provides compilation and testing commands for all directories
.PHONY: help test ready backend gas GoogleAppsScripts lambda-functions start tunnel stop install clean status _get_tunnel_url test-specific clasp _run_in_new_terminal _kill_tunnel _kill_backend _check_process _deploy_lambda

# Default target
help:
	@echo "🚀 BARS Repository Commands"
	@echo "=========================="
	@echo ""
	@echo "🔧 Backend Development:"
	@echo "  make start               - Start backend server + tunnel (opens tunnel in new terminal)"
	@echo "  make backend             - Start backend server (uvicorn) in dev mode"
	@echo "  make tunnel              - Start localtunnel (tries multiple strategies with fallback)"
	@echo "  make stop                - Stop all processes"
	@echo "  make install             - Install all dependencies (Python + GAS)"
	@echo "  make clean               - Clean up processes and cache files"
	@echo "  make status              - Show running processes"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test [path]         - Run tests in directory and subdirectories (default: current dir)"
	@echo "  make ready [path]        - Test directory (fails fast on errors)"
	@echo "  make test .              - Run all tests in repository"
	@echo "  make test backend        - Run backend tests"
	@echo "  make test gas            - Run GoogleAppsScripts tests"
	@echo "  make test lambda         - Run lambda-functions tests"
	@echo ""
	@echo "🧪 Backend-Specific Tests:"
	@echo "  make test-specific TEST=<path> - Run specific test file or case"
	@echo ""
	@echo "📦 Google Apps Script Deployment:"
	@echo "  make clasp push <project> - Push GAS project to remote (with diff comparison)"
	@echo "  make clasp pull <project> - Pull GAS project from remote (with diff comparison)"
	@echo "  make clasp deploy <project> - Full deployment (push + version management)"
	@echo ""
	@echo "📋 Examples:"
	@echo "  make test lambda-functions/shopifyProductUpdateHandler"
	@echo "  make test-specific TEST=backend/test_slack_message_formatting.py"
	@echo "  make test-specific TEST=backend/test_orders_api.py::test_fetch_order"
	@echo ""
	@echo "🔧 Quick Start:"
	@echo "  1. make install          - Install dependencies"
	@echo "  2. make start            - Start server + tunnel"
	@echo "  3. make test             - Run tests"

# Handle arguments for test commands
# This allows 'make test backend' instead of 'make test DIR=backend'
ifneq ($(filter test,$(MAKECMDGOALS)),)
  # Get the argument after 'test'
  TEST_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(TEST_ARGS),)
    DIR := $(TEST_ARGS)
    # Prevent make from trying to build these as targets
    $(eval $(TEST_ARGS):;@:)
  else
    DIR := .
  endif
endif

# Default DIR if not set by arguments
DIR ?= .

# =============================================================================
# CONSTANTS
# =============================================================================

BACKEND_PYTHON := ./.venv/bin/python
TUNNEL_PORT := 8000
TUNNEL_SUBDOMAIN := bars-backend

# =============================================================================
# SHARED HELPERS
# =============================================================================

# Kill tunnel processes
_kill_tunnel:
	@pkill -f "lt -p $(TUNNEL_PORT)" || true

# Kill backend server processes
_kill_backend:
	@pkill -f uvicorn || true

# Check if a process is running
_check_process:
	@ps aux | grep -v grep | grep -q "$(PROCESS)" || exit 1

# =============================================================================
# BACKEND DEVELOPMENT COMMANDS
# =============================================================================

# Backend development helpers
_get_tunnel_url:
	@lt_cmd=$$(ps aux | grep -v grep | grep "lt -p $(TUNNEL_PORT)" | head -1); \
	subdomain=$$(echo "$$lt_cmd" | grep -oE "\-s [a-z0-9-]+" | awk '{print $$2}'); \
	if [ -n "$$subdomain" ]; then \
		echo "https://$$subdomain.loca.lt"; \
	else \
		echo "no active tunnel found"; \
	fi

_run_in_new_terminal:
	@echo "🌐 Opening new terminal for: $(CMD)"
	@cmd="$(CMD)"; \
	if echo "$$EDITOR" | grep -qi cursor; then \
		if ! pgrep -f "Cursor.app" >/dev/null 2>&1; then \
			echo "❌ Cursor is not running"; \
			exit 1; \
		fi; \
		if ! osascript -e 'tell application "Cursor" to activate' \
			-e 'tell application "System Events" to keystroke "`" using {control down, shift down}' \
			-e 'delay 1' \
			-e "tell application \"System Events\" to keystroke \"$$cmd\"" \
			-e 'tell application "System Events" to key code 36' 2>/dev/null; then \
			echo "❌ Failed to open Cursor terminal"; \
			exit 1; \
		fi; \
	else \
		if ! osascript -e "tell application \"Terminal\" to do script \"$$cmd\"" 2>/dev/null; then \
			echo "❌ Failed to open Terminal"; \
			exit 1; \
		fi; \
	fi

start:
	@echo "🚀 Starting backend server + tunnel..."
	@$(MAKE) -s _kill_tunnel
	@$(MAKE) -s _kill_backend
	@sleep 1
	@if ! $(MAKE) -s _run_in_new_terminal CMD='make tunnel'; then \
		echo ""; \
		echo "⚠️  Could not open new terminal automatically"; \
		echo ""; \
		echo "Please manually:"; \
		echo "  1. Open a new terminal"; \
		echo "  2. Run: make tunnel"; \
		echo ""; \
		read -p "Press Enter once the tunnel is running to continue..."; \
	fi
	@sleep 3
	@echo "✅ Starting backend server now (tunnel will start in new terminal)..."
	@$(MAKE) backend

backend:
	@echo "🚀 Starting backend server..."
	@cd backend && $(BACKEND_PYTHON) -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

tunnel:
	@echo "🌐 Starting localtunnel..."
	@$(MAKE) -s _kill_tunnel
	@sleep 1
	@if ! command -v lt >/dev/null 2>&1; then \
		echo ""; echo "❌ CRITICAL: localtunnel (lt) not found in PATH"; \
		echo "💡 Install: npm install -g localtunnel"; echo ""; \
		exit 1; \
	fi
	@sh -c '\
		try_tunnel() { \
			args="$$1"; desc="$$2"; \
			rm -f /tmp/tunnel_output.log; \
			lt -p $(TUNNEL_PORT) $$args > /tmp/tunnel_output.log 2>&1 & \
			pid=$$!; sleep 3; \
			if ps -p $$pid >/dev/null 2>&1 && grep -q "your url is" /tmp/tunnel_output.log 2>/dev/null; then \
				url=$$(grep "your url is" /tmp/tunnel_output.log | grep -oE "https://[a-z0-9-]+\.loca\.lt"); \
				echo "✅ Tunnel started: $$desc"; \
				echo "🌐 URL: $$url"; \
				return 0; \
	else \
				kill $$pid 2>/dev/null || true; \
				return 1; \
			fi; \
		}; \
		if ! try_tunnel "-s $(TUNNEL_SUBDOMAIN)" "subdomain \"$(TUNNEL_SUBDOMAIN)\""; then \
			echo "❌ Subdomain unavailable, trying auto-assigned..."; \
			if ! try_tunnel "" "auto-assigned subdomain"; then \
				echo "❌ Failed to start tunnel"; \
				cat /tmp/tunnel_output.log 2>/dev/null || true; \
				exit 1; \
			fi; \
		fi \
	'

stop:
	@echo "🛑 Stopping all processes..."
	@$(MAKE) -s _kill_tunnel
	@$(MAKE) -s _kill_backend
	@pkill -f "while true; do echo" || true
	@rm -f tunnel.log
	@echo "✅ All processes stopped"


# =============================================================================
# INSTALLATION COMMANDS
# =============================================================================

install:
	@echo "📦 Installing all dependencies..."
	@echo "  Syncing dependencies from backend/requirements.txt to pyproject.toml..."
	@python3 scripts/sync_pyproject_dependencies.py
	@bash scripts/setup_direnv.sh
	@python3 scripts/install_pipx_environment.py
	@echo "  Installing GAS dependencies from GoogleAppsScripts/package.json..."
	@cd GoogleAppsScripts && pnpm install
	@echo "✅ All dependencies installed!"
	@echo "✅ bars CLI is now available. Run 'bars --help' to get started."
	@echo "⚠️  Restart your shell or run 'source ~/.zshrc' to activate direnv hook."

clean: stop
	@echo "🧹 Cleaning up..."
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
	@find . -name ".pytest_cache" -type d -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cleanup complete"

status:
	@echo "📊 Process Status:"
	@echo "=================="
	@echo ""
	@echo "🖥️  Backend Server:"
	@ps aux | grep uvicorn | grep -v grep || echo "❌ Backend server not running"
	@echo ""
	@echo "🌐 Localtunnel:"
	@ps aux | grep "lt -p $(TUNNEL_PORT)" | grep -v grep || echo "❌ Localtunnel not running"
	@echo ""
	@echo "🌐 Localtunnel URL:"
	@url=$$($(MAKE) -s _get_tunnel_url); \
	if [ "$$url" = "no active tunnel found" ]; then \
		echo "❌ No active tunnel found"; \
	else \
		echo "$$url"; \
	fi
	@echo ""
	@echo "📋 Recent tunnel logs (if daemon is running):"
	@if [ -f tunnel.log ]; then \
		echo "Last 5 lines from tunnel.log:"; \
		tail -5 tunnel.log; \
	else \
		echo "No tunnel.log found (daemon not started)"; \
	fi

# =============================================================================
# TESTING COMMANDS
# =============================================================================

# Testing helpers
_test_directory:
	@if [ "$(DIR)" = "." ]; then \
		echo "🧪 Running all tests in repository..."; \
		$(MAKE) _test_backend_internal; \
		$(MAKE) _test_gas_internal; \
		$(MAKE) _test_lambda_internal; \
	elif [ -d "$(DIR)" ]; then \
		if echo "$(DIR)" | grep -q "backend"; then \
			$(MAKE) _test_backend_internal DIR=$(DIR); \
		elif echo "$(DIR)" | grep -q "GoogleAppsScripts"; then \
			$(MAKE) _test_gas_internal DIR=$(DIR); \
		elif echo "$(DIR)" | grep -q "lambda-functions"; then \
			$(MAKE) _test_lambda_internal DIR=$(DIR); \
		else \
			echo "🔍 Auto-detecting test types in $(DIR)..."; \
			if find "$(DIR)" -name "*test*.py" -o -name "test_*.py" -type f | head -1 | grep -q .; then \
				$(MAKE) _test_python_files DIR=$(DIR); \
			fi; \
			if find "$(DIR)" -name "*test*.js" -o -name "test_*.js" -type f | head -1 | grep -q .; then \
				$(MAKE) _test_js_files DIR=$(DIR); \
			fi; \
			if find "$(DIR)" -name "*.sh" -type f | grep -q test; then \
				$(MAKE) _test_shell_files DIR=$(DIR); \
			fi; \
		fi; \
	else \
		echo "❌ Directory $(DIR) does not exist"; \
		exit 1; \
	fi

# Public testing commands
test:
	@echo "🧪 Running tests in directory: $(DIR)"
	@$(MAKE) _test_directory DIR=$(DIR)

ready:
	@echo "🚀 Running test for directory: $(DIR)"
	@$(MAKE) _test_directory DIR=$(DIR)

# Note: backend, gas, lambda, etc. aliases work for test commands due to the argument parsing logic
# Use: make test backend, make test GoogleAppsScripts, make test lambda-functions

test-specific:
	@if [ -z "$(TEST)" ]; then \
		echo "❌ Please specify a test to run: make test-specific TEST=<test_name>"; \
		echo "Examples:"; \
		echo "  make test-specific TEST=backend/test_slack_message_formatting.py"; \
		echo "  make test-specific TEST=backend/test_orders_api.py::test_fetch_order"; \
		echo "  make test-specific TEST=backend/services/tests/test_csv_service.py"; \
		exit 1; \
	fi
	@echo "🧪 Running specific test: $(TEST)"
	@if echo "$(TEST)" | grep -q "::"; then \
		echo "Running pytest test case: $(TEST)"; \
		cd backend && $(BACKEND_PYTHON) -m pytest "../$(TEST)" -v; \
	elif echo "$(TEST)" | grep -q "\.py$$"; then \
		echo "Running Python test file: $(TEST)"; \
		if echo "$(TEST)" | grep -q "^backend/"; then \
			cd backend && $(BACKEND_PYTHON) -m pytest "../$(TEST)" -v; \
		else \
			cd backend && $(BACKEND_PYTHON) "../$(TEST)"; \
		fi; \
	else \
		echo "❌ Invalid test format. Use .py file or pytest::test_name format"; \
		exit 1; \
	fi

# Backend testing (Python) - CI-equivalent comprehensive testing
_test_backend_internal:
	@echo "🧪 Running backend tests (CI-equivalent)..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "backend" ]; then \
		echo "🔍 Step 1: Backend compilation checks..."; \
		cd backend && \
		export SHOPIFY_URL_ADMIN_DOMAIN="test-store.myshopify.com" && \
		export SHOPIFY_TOKEN="test_token" && \
		export ENVIRONMENT="test" && \
		export SLACK_REFUNDS_BOT_TOKEN="test_slack_token" && \
		echo "📋 Checking Python syntax..." && \
		../.venv/bin/python -m py_compile config.py main.py && \
		echo "📋 Checking module imports..." && \
		../.venv/bin/python -c "import sys; sys.path.append('.'); from config import config; print('✅ Config imports successfully'); from main import app; print('✅ Main FastAPI app imports successfully'); from modules.orders import OrdersService; print('✅ Orders service imports successfully'); from modules.integrations.slack import SlackClient; print('✅ Slack Client imports successfully'); from routers.refunds import router; print('✅ Refunds router imports successfully')" && \
		echo "🧪 Step 2: Running comprehensive test suite..." && \
		if [ -d "tests/unit" ] && [ "$$(find tests/unit -name '*.py' -not -name '__init__.py' | wc -l)" -gt 0 ]; then \
			echo "🧪 Running unit tests..."; \
			../.venv/bin/python -m pytest tests/unit/ -v; \
		else \
			echo "⚠️ No unit tests found in tests/unit/, skipping..."; \
		fi && \
		echo "🧪 Running service-specific tests..." && \
		../.venv/bin/python -m pytest services/*/tests/ -v || true && \
		echo "🧪 Running router tests..." && \
		../.venv/bin/python -m pytest routers/tests/ -v || true && \
		echo "🧪 Running Slack webhook tests..." && \
		../.venv/bin/python -m pytest routers/tests/test_slack_router.py -v || true && \
		if [ -d "tests/integration" ] && [ "$$(find tests/integration -name '*.py' -not -name '__init__.py' | wc -l)" -gt 0 ]; then \
			echo "🧪 Running integration tests..."; \
			../.venv/bin/python -m pytest tests/integration/ -v; \
		else \
			echo "⚠️ No integration tests found in tests/integration/, skipping..."; \
		fi && \
		echo "✅ Backend tests completed!"; \
	else \
		echo "📋 Running tests in $(DIR)..."; \
		if find "$(DIR)" -name "test_*.py" -o -name "*_test.py" -type f | head -1 | grep -q .; then \
			cd backend && \
			export SHOPIFY_URL_ADMIN_DOMAIN="test-store.myshopify.com" && \
			export SHOPIFY_TOKEN="test_token" && \
			export ENVIRONMENT="test" && \
			export SLACK_REFUNDS_BOT_TOKEN="test_slack_token" && \
			../.venv/bin/python -m pytest "../$(DIR)" -v; \
		else \
			echo "⚠️  No Python test files found in $(DIR)"; \
		fi; \
	fi

# GoogleAppsScripts testing (JavaScript) - CI-equivalent comprehensive testing
_test_gas_internal:
	@echo "🧪 Running GoogleAppsScripts tests (CI-equivalent)..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "GoogleAppsScripts" ]; then \
		cd GoogleAppsScripts && \
		echo "🔍 Step 1: JSON validation..." && \
		echo "📋 Validating appsscript.json files..." && \
		find . -name "appsscript.json" -exec python3 -m json.tool {} \; > /dev/null && \
		echo "✅ All appsscript.json files are valid JSON" && \
		echo "🔍 Step 2: Security scan..." && \
		echo "📋 Checking for hardcoded secrets..." && \
		if grep -r "shpat_\|xoxb-\|https://hooks.slack.com" --include="*.gs" . | grep -v "shared-utilities/secretsUtils.gs" | grep -v "instructions.gs"; then \
			echo "❌ Found hardcoded secrets in scripts!"; \
			exit 1; \
		else \
			echo "✅ No hardcoded secrets found"; \
		fi && \
		echo "🧪 Step 3: Running test suites..." && \
		chmod +x tests/*.sh && \
		chmod +x projects/*/tests/*.sh && \
		echo "📋 Running Product Creation Function Tests..." && \
		cd projects/create-products-from-registration-info/tests && \
		node run_consolidated_tests.js && \
		cd - && \
		echo "📋 Running Process Refunds Exchanges Tests..." && \
		./projects/process-refunds-exchanges/tests/run_tests.sh || true && \
		echo "📋 Running Leadership Discount Codes Tests..." && \
		./projects/leadership-discount-codes/tests/test_leadership_discount_codes.sh || true && \
		echo "📋 Running Instructions Tests..." && \
		./tests/test_instructions.sh && \
		if find tests/ -name "*.js" -o -name "*.mjs" -type f | head -1 | grep -q .; then \
			echo "📋 Running additional JavaScript tests..."; \
			find tests/ -name "*.js" -o -name "*.mjs" -type f | while read -r file; do \
				echo "  Running $$file..."; \
				node "$$file" || true; \
			done; \
		fi && \
		echo "✅ GoogleAppsScripts tests completed!"; \
	else \
		echo "📋 Running tests in $(DIR)..."; \
		if find "$(DIR)" -name "*.sh" -type f | grep -q test; then \
			find "$(DIR)" -name "*test*.sh" -type f | while read -r file; do \
				echo "  Running $$file..."; \
				chmod +x "$$file"; \
				"$$file" || true; \
			done; \
		fi; \
	fi

# Lambda functions testing (Python) - CI-equivalent comprehensive testing
_test_lambda_internal:
	@echo "🧪 Running Lambda function tests (CI-equivalent)..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "lambda-functions" ]; then \
		cd lambda-functions && \
		echo "🔍 Step 1: Lambda compilation checks..." && \
		echo "📋 Checking Lambda function syntax..." && \
		for dir in */; do \
			echo "🔍 Checking $$dir..."; \
			cd "$$dir" && \
			python3 -m py_compile *.py 2>/dev/null && \
			python3 -c "import lambda_function; print('✅ $$dir imports successfully')" && \
			cd ..; \
		done && \
		echo "🧪 Step 2: Running Lambda test suite..." && \
		if [ -f "tests/run_tests.py" ]; then \
			echo "📋 Running Lambda test suite..."; \
			python3 tests/run_tests.py unit; \
		else \
			echo "📋 Running pytest on Lambda tests..."; \
			python3 -m pytest tests/ -v || true; \
		fi && \
		echo "✅ Lambda function tests completed!"; \
	else \
		echo "📋 Running tests in $(DIR)..."; \
		if find "$(DIR)" -name "test_*.py" -type f | head -1 | grep -q .; then \
			python3 -m pytest "$(DIR)" -v || true; \
		else \
			echo "⚠️  No test files found in $(DIR)"; \
		fi; \
	fi

# Generic Python test runner
_test_python_files:
	@echo "🧪 Running Python tests in $(DIR)..."
	@if find "$(DIR)" -name "test_*.py" -o -name "*_test.py" -type f | head -1 | grep -q .; then \
		if [ -d "backend" ]; then \
			cd backend && python3 -m pytest "../$(DIR)" -v; \
		else \
			python3 -m pytest "$(DIR)" -v; \
		fi; \
	else \
		echo "⚠️  No Python test files found in $(DIR)"; \
	fi

# Generic JavaScript test runner
_test_js_files:
	@echo "🧪 Running JavaScript tests in $(DIR)..."
	@if command -v node >/dev/null 2>&1; then \
		find "$(DIR)" -name "*test*.js" -o -name "test_*.js" -type f | while read -r file; do \
			echo "  Running $$file..."; \
			node "$$file" || true; \
		done; \
	else \
		echo "⚠️  Node.js not found, cannot run JavaScript tests"; \
	fi

# Generic shell test runner
_test_shell_files:
	@echo "🧪 Running shell tests in $(DIR)..."
	@find "$(DIR)" -name "*test*.sh" -type f | while read -r file; do \
		echo "  Running $$file..."; \
		chmod +x "$$file"; \
		"$$file" || true; \
	done

# =============================================================================
# LAMBDA DEPLOYMENT COMMANDS
# =============================================================================

_deploy_lambda:
	@if [ -z "$(LAMBDA_FUNCTION)" ]; then \
		echo "🚀 Deploying all Lambda functions..."; \
		echo ""; \
		FUNCTIONS=$$(find lambda/functions -maxdepth 1 -type d -name "*Lambda*" -o -name "*Handler*" | grep -v "^lambda/functions$$" | xargs -n1 basename | sort); \
		if [ -z "$$FUNCTIONS" ]; then \
			echo "❌ No Lambda functions found"; \
			exit 1; \
		fi; \
		for FUNC in $$FUNCTIONS; do \
			if [ -f "lambda/functions/$$FUNC/lambda_function.py" ]; then \
				echo ""; \
				echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
				echo "📦 Function: $$FUNC"; \
				echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"; \
				bash scripts/deploy_lambda_function.sh "$$FUNC"; \
			fi; \
		done; \
	else \
		bash scripts/deploy_lambda_function.sh "$(LAMBDA_FUNCTION)"; \
	fi

# =============================================================================
# GOOGLE APPS SCRIPT DEPLOYMENT COMMANDS
# =============================================================================

# Handle clasp command arguments
ifneq ($(filter clasp,$(MAKECMDGOALS)),)
  # Get arguments after 'clasp'
  CLASP_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(CLASP_ARGS),)
    CLASP_CMD := $(word 1,$(CLASP_ARGS))
    CLASP_PROJECT := $(word 2,$(CLASP_ARGS))
    # Prevent make from trying to build these as targets
    $(eval $(CLASP_ARGS):;@:)
  endif
endif

clasp:
	@if [ -z "$(CLASP_CMD)" ]; then \
		echo "❌ Command required (push, pull, or deploy)"; \
		echo "Usage: make clasp <command> <project-name>"; \
		echo "Commands:"; \
		echo "  push    - Push GAS project to remote (with diff comparison)"; \
		echo "  pull    - Pull GAS project from remote (with diff comparison)"; \
		echo "  deploy  - Full deployment (push + version management)"; \
		echo ""; \
		echo "Examples:"; \
		echo "  make clasp push waitlist-script-comprehensive"; \
		echo "  make clasp pull waitlist-script-comprehensive"; \
		echo "  make clasp deploy waitlist-script-comprehensive"; \
		exit 1; \
	fi
	@if [ -z "$(CLASP_PROJECT)" ]; then \
		echo "❌ Project name required"; \
		echo "Usage: make clasp $(CLASP_CMD) <project-name>"; \
		echo "Example: make clasp $(CLASP_CMD) waitlist-script-comprehensive"; \
		exit 1; \
	fi
	@if [ "$(CLASP_CMD)" = "push" ]; then \
		bash GoogleAppsScripts/remote-sync-tools/push.sh "$(CLASP_PROJECT)"; \
	elif [ "$(CLASP_CMD)" = "pull" ]; then \
		bash GoogleAppsScripts/remote-sync-tools/pull.sh "$(CLASP_PROJECT)"; \
	elif [ "$(CLASP_CMD)" = "deploy" ]; then \
		bash GoogleAppsScripts/remote-sync-tools/deploy.sh "$(CLASP_PROJECT)"; \
	else \
		echo "❌ Unknown command: $(CLASP_CMD)"; \
		echo "Valid commands: push, pull, deploy"; \
		exit 1; \
	fi
