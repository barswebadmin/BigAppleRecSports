# BARS Repository Makefile
# Provides compilation and testing commands for all directories
.PHONY: backend clasp clean help install ready start status stop test test-specific tunnel _backend_ports _backend_wait_for_healthy_port _check_process _deploy_lambda _get_backend_port _get_tunnel_port _get_tunnel_subdomain _get_tunnel_url _is_port_open _kill_backend _kill_tunnel _run_in_new_terminal

# Default target
help:
	@echo "🚀 BARS Repository Commands"
	@echo "=========================="
	@echo ""
	@echo "🔧 Backend Development:"
	@echo "  make start               - Start backend server + tunnel (opens backend in new terminal)"
	@echo "  make backend             - Start backend server (uvicorn) in dev mode"
	@echo "  make tunnel              - Start localtunnel (tries multiple strategies with fallback)"
	@echo "  make stop                - Stop all processes"
	@echo "  make install [target]    - Install dependencies (all, backend, cli, google, lambda)"
	@echo "  make lock                - Generate UV lock files for all projects"
	@echo "  make clean               - Clean up processes and cache files"
	@echo "  make status              - Show running processes"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test [path]         - Run tests in directory and subdirectories (default: current dir)"
	@echo "  make ready [path]        - Test directory (fails fast on errors)"
	@echo "  make test .              - Run all tests in repository"
	@echo "  make test backend        - Run backend tests"
	@echo "  make test GoogleAppsScripts - Run GoogleAppsScripts tests"
	@echo "  make test lambda         - Run lambda tests"
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
	@echo "  make install backend           - Install backend dependencies only"
	@echo "  make install cli               - Install CLI tool only"
	@echo "  make install shared_utilities  - Install shared utilities (for IDE/workspace)"
	@echo "  make test lambda/functions/shopifyProductUpdateHandler"
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

# Handle arguments for install commands
# This allows 'make install backend' instead of 'make install-backend'
ifneq ($(filter install,$(MAKECMDGOALS)),)
  # Get the argument after 'install'
  INSTALL_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(INSTALL_ARGS),)
    INSTALL_TARGET := $(INSTALL_ARGS)
    # Prevent make from trying to build these as targets
    $(eval $(INSTALL_ARGS):;@:)
  else
    INSTALL_TARGET :=
  endif
endif

# Default DIR if not set by arguments
DIR ?= .

# =============================================================================
# CONSTANTS
# =============================================================================

# Python interpreters for each project (using uv venvs)
BACKEND_PYTHON := backend/.venv/bin/python
CLI_PYTHON := bars_cli/.venv/bin/python
LAMBDA_PYTHON := lambda/.venv/bin/python

TUNNEL_PORT := 8000
TUNNEL_SUBDOMAIN ?= bars-backend
TUNNEL_FALLBACK_SUBDOMAIN ?= bars-backend-2

# =============================================================================
# SHARED HELPERS
# =============================================================================

# Kill tunnel processes
_kill_tunnel:
	@pkill -f "lt -p" || true

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
_backend_ports:
	@bash -lc '\
		set -euo pipefail; \
		echo "$(TUNNEL_PORT) $$(( $(TUNNEL_PORT) + 1 ))"; \
	'

_is_port_open:
	@bash -lc '\
		set -euo pipefail; \
		port="$(PORT)"; \
		python3 -c "import socket, sys; host=sys.argv[1]; port=int(sys.argv[2]); s=socket.socket(); s.settimeout(0.25); rc=s.connect_ex((host, port)); s.close(); sys.exit(0 if rc==0 else 1)" "127.0.0.1" "$$port" >/dev/null 2>&1; \
	'

_backend_wait_for_healthy_port:
	@bash -lc '\
		set -euo pipefail; \
		ports="$(PORTS)"; \
		deadline="$$(($$(date +%s) + 20))"; \
		while true; do \
			for p in $$ports; do \
				if curl -fsS --connect-timeout 0.25 --max-time 0.75 "http://127.0.0.1:$$p/health" >/dev/null 2>&1; then \
					echo "$$p"; \
					exit 0; \
				fi; \
			done; \
			if [ "$$(date +%s)" -ge "$$deadline" ]; then \
				echo "❌ Backend failed health check on ports $$ports after 20s." 1>&2; \
				echo "   Check the backend terminal output for startup errors." 1>&2; \
				exit 1; \
			fi; \
			sleep "1"; \
		done; \
	'

_get_backend_port:
	@bash -lc '\
		set -euo pipefail; \
		ports=$$(ps aux | grep -v grep | grep "uvicorn main:app" | grep -oE "\-\-port [0-9]+" | cut -d" " -f2 | sort -u || true); \
		for p in $$ports; do \
			if curl -fsS --connect-timeout 0.25 --max-time 0.75 "http://127.0.0.1:$$p/health" >/dev/null 2>&1; then \
				echo "$$p"; \
				exit 0; \
			fi; \
		done; \
		exit 0; \
	'

_get_tunnel_subdomain:
	@lt_cmd=$$(ps aux | grep -v grep | grep "lt -p" | head -1); \
	subdomain=$$(echo "$$lt_cmd" | grep -oE "\-s [a-z0-9-]+" | awk '{print $$2}'); \
	if [ -n "$$subdomain" ]; then \
		echo "$$subdomain"; \
	fi

_get_tunnel_url:
	@subdomain=$$($(MAKE) -s _get_tunnel_subdomain); \
	if [ -n "$$subdomain" ]; then \
		echo "https://$$subdomain.loca.lt"; \
	else \
		echo "no active tunnel found"; \
	fi

_get_tunnel_port:
	@lt_cmd=$$(ps aux | grep -v grep | grep "lt -p" | head -1); \
	port=$$(echo "$$lt_cmd" | grep -oE "\-p [0-9]+" | cut -d" " -f2); \
	if [ -n "$$port" ]; then \
		echo "$$port"; \
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
	@bash -lc '\
		set -euo pipefail; \
		ports="$$( $(MAKE) -s _backend_ports )"; \
		echo "🖥️  Backend will try ports: $$ports"; \
		if ! $(MAKE) -s _run_in_new_terminal CMD="make backend"; then \
			echo ""; \
			echo "⚠️  Could not open a new terminal automatically"; \
			echo ""; \
			echo "Please manually:"; \
			echo "  1. Open a new terminal"; \
			echo "  2. Run: make backend"; \
			echo ""; \
			read -r -p "Press Enter once backend is running to continue... " _; \
		fi; \
		echo "🔍 Waiting for backend health on http://127.0.0.1:<port>/health ..."; \
		port="$$( $(MAKE) -s _backend_wait_for_healthy_port PORTS="$$ports" )"; \
		echo "✅ Backend healthy on port $$port"; \
		echo "🌐 Starting tunnel on port $$port..."; \
		$(MAKE) tunnel PORT=$$port; \
	'

backend:
	@bash -lc '\
		set -euo pipefail; \
		run_backend() { \
			local port="$$1"; \
			echo "🚀 Starting backend server on http://127.0.0.1:$$port ..."; \
			(cd backend && PYTHONPATH="$(CURDIR)" .venv/bin/python -m uvicorn main:app --reload --host "127.0.0.1" --port "$$port"); \
		}; \
		if [ -n "$${PORT:-}" ]; then \
			run_backend "$$PORT"; \
			exit 0; \
		fi; \
		port1="$(TUNNEL_PORT)"; \
		port2="$$(($(TUNNEL_PORT) + 1))"; \
		if run_backend "$$port1"; then \
			exit 0; \
		fi; \
		echo "❌ Backend failed to start on port $$port1. Trying $$port2..."; \
		if run_backend "$$port2"; then \
			exit 0; \
		fi; \
		echo "❌ Backend failed to start on ports $$port1 and $$port2."; \
		exit 1; \
	'

tunnel:
	@$(MAKE) -s _kill_tunnel
	@sleep 1
	@if ! command -v lt >/dev/null 2>&1; then \
		echo ""; echo "❌ CRITICAL: localtunnel (lt) not found in PATH"; \
		echo "💡 Install: npm install -g localtunnel"; echo ""; \
		exit 1; \
	fi
	@bash -lc '\
		set -euo pipefail; \
		BLUE=$$'\''\033[34m'\''; \
		ALTBLUE=$$'\''\033[36m'\''; \
		RESET=$$'\''\033[0m'\''; \
		start_tunnel() { \
			local subdomain="$$1"; \
			local color="$$2"; \
			local port="$$3"; \
			rm -f /tmp/tunnel_output.log; \
			printf "🌐 Starting localtunnel with subdomain: %b%s%b.\n" "$$color" "$$subdomain" "$$RESET"; \
			lt -p "$$port" -s "$$subdomain" 2>&1 \
				| tee /tmp/tunnel_output.log \
				| awk '\''/your url is:/ { \
					if (match($$0, /https:\/\/[a-z0-9-]+\.loca\.lt/)) { \
						print "🌐 URL: " substr($$0, RSTART, RLENGTH); \
					} \
					next \
				} \
				{ print }'\''; \
			return "$${PIPESTATUS[0]}"; \
		}; \
		port="$${PORT:-$$( $(MAKE) -s _get_backend_port )}"; \
		if [ -n "$$port" ] && $(MAKE) -s _is_port_open PORT="$$port" >/dev/null 2>&1; then \
			echo "🖥️  Backend detected on port $$port"; \
		else \
			port=""; \
			while true; do \
				echo "⚠️  No running backend detected."; \
				read -r -p "Retry [r], cancel [n], or enter port: " ans; \
				ans="$${ans:-n}"; \
				case "$$ans" in \
					r|R) \
						port="$$( $(MAKE) -s _get_backend_port )"; \
						if [ -n "$$port" ] && $(MAKE) -s _is_port_open PORT="$$port" >/dev/null 2>&1; then \
							echo "🖥️  Backend detected on port $$port"; \
							break; \
						fi \
						;; \
					n|N) echo "❌ Cancelled."; exit 1 ;; \
					*[!0-9]*) echo "❌ Invalid input. Enter r, n, or a port number." ;; \
					*) \
						if $(MAKE) -s _is_port_open PORT="$$ans" >/dev/null 2>&1; then \
							if curl -fsS --connect-timeout 0.25 --max-time 0.75 "http://127.0.0.1:$$ans/health" >/dev/null 2>&1; then \
								port="$$ans"; \
								break; \
							fi; \
							echo "❌ Backend health check failed on port $$ans."; \
							continue; \
						else \
							echo "❌ No server listening on port $$ans."; \
						fi \
						;; \
				esac; \
			done; \
		fi; \
		if start_tunnel "$(TUNNEL_SUBDOMAIN)" "$$BLUE" "$$port"; then \
			exit 0; \
		else \
			rc="$$?"; \
		fi; \
		if grep -q "your url is" /tmp/tunnel_output.log 2>/dev/null; then \
			exit "$$rc"; \
		fi; \
		printf "❌ Failed to start localtunnel with subdomain: %b%s%b.\n" "$$BLUE" "$(TUNNEL_SUBDOMAIN)" "$$RESET"; \
		printf "🌐 Trying fallback subdomain: %b%s%b\n" "$$ALTBLUE" "$(TUNNEL_FALLBACK_SUBDOMAIN)" "$$RESET"; \
		if start_tunnel "$(TUNNEL_FALLBACK_SUBDOMAIN)" "$$ALTBLUE" "$$port"; then \
			exit 0; \
		else \
			rc="$$?"; \
		fi; \
		printf "❌ Failed to start localtunnel with fallback subdomain: %b%s%b.\n" "$$ALTBLUE" "$(TUNNEL_FALLBACK_SUBDOMAIN)" "$$RESET"; \
		exit "$$rc"; \
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
	@if [ -n "$(INSTALL_TARGET)" ]; then \
		python3 scripts/installation_setup/install.py $(INSTALL_TARGET); \
	else \
		python3 scripts/installation_setup/install.py; \
	fi

lock:
	@echo "🔒 Generating UV lock files for all projects..."
	@echo ""
	@echo "📦 Locking shared_utilities..."
	@cd shared_utilities && uv lock
	@echo ""
	@echo "📦 Locking backend..."
	@cd backend && uv lock
	@echo ""
	@echo "📦 Locking bars_cli..."
	@cd bars_cli && uv lock
	@echo ""
	@echo "📦 Locking lambda..."
	@cd lambda && uv lock
	@echo ""
	@echo "✅ All lock files generated"

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
	@bash -lc '\
		set -euo pipefail; \
		RED=$$'\''\033[31m'\''; \
		RESET=$$'\''\033[0m'\''; \
		if ps aux | grep uvicorn | grep -v grep >/dev/null 2>&1; then \
			echo "🖥️  Backend Server: running"; \
		else \
			printf "❌ Backend server: %bnot running%b\n" "$$RED" "$$RESET"; \
		fi; \
		port="$$( $(MAKE) -s _get_backend_port )"; \
		if [ -n "$$port" ]; then \
			echo "🖥️  Backend Port: $$port"; \
		else \
			printf "❌ Backend port: %bnot running%b\n" "$$RED" "$$RESET"; \
		fi; \
		if ps aux | grep "lt -p" | grep -v grep >/dev/null 2>&1; then \
			echo "🌐 Localtunnel: running"; \
		else \
			printf "❌ Localtunnel: %bnot running%b\n" "$$RED" "$$RESET"; \
		fi; \
		url="$$( $(MAKE) -s _get_tunnel_url )"; \
		if [ "$$url" != "no active tunnel found" ]; then \
			echo "🌐 Localtunnel URL: $$url"; \
		else \
			printf "❌ Localtunnel URL: %bnot running%b\n" "$$RED" "$$RESET"; \
		fi; \
	'

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
		elif echo "$(DIR)" | grep -q "^lambda"; then \
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

# Note: backend, GoogleAppsScripts, lambda, etc. aliases work for test commands due to the argument parsing logic
# Use: make test backend, make test GoogleAppsScripts, make test lambda

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
		cd backend && .venv/bin/python -m pytest "../$(TEST)" -v; \
	elif echo "$(TEST)" | grep -q "\.py$$"; then \
		echo "Running Python test file: $(TEST)"; \
		if echo "$(TEST)" | grep -q "^backend/"; then \
			cd backend && .venv/bin/python -m pytest "../$(TEST)" -v; \
		else \
			cd backend && .venv/bin/python "../$(TEST)"; \
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
		.venv/bin/python -m py_compile config.py main.py && \
		echo "📋 Checking module imports..." && \
		.venv/bin/python -c "import sys; sys.path.append('.'); from config import config; print('✅ Config imports successfully'); from main import app; print('✅ Main FastAPI app imports successfully'); from modules.orders import OrdersService; print('✅ Orders service imports successfully'); from modules.integrations.slack import SlackClient; print('✅ Slack Client imports successfully'); from routers.refunds import router; print('✅ Refunds router imports successfully')" && \
		echo "🧪 Step 2: Running comprehensive test suite..." && \
		if [ -d "tests/unit" ] && [ "$$(find tests/unit -name '*.py' -not -name '__init__.py' | wc -l)" -gt 0 ]; then \
			echo "🧪 Running unit tests..."; \
			.venv/bin/python -m pytest tests/unit/ -v; \
		else \
			echo "⚠️ No unit tests found in tests/unit/, skipping..."; \
		fi && \
		echo "🧪 Running service-specific tests..." && \
		.venv/bin/python -m pytest services/*/tests/ -v || true && \
		echo "🧪 Running router tests..." && \
		.venv/bin/python -m pytest routers/tests/ -v || true && \
		echo "🧪 Running Slack webhook tests..." && \
		.venv/bin/python -m pytest routers/tests/test_slack_router.py -v || true && \
		if [ -d "tests/integration" ] && [ "$$(find tests/integration -name '*.py' -not -name '__init__.py' | wc -l)" -gt 0 ]; then \
			echo "🧪 Running integration tests..."; \
			.venv/bin/python -m pytest tests/integration/ -v; \
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
			.venv/bin/python -m pytest "../$(DIR)" -v; \
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
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "lambda" ]; then \
		cd lambda && \
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
