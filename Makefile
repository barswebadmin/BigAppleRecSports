# BARS Repository Makefile
# Provides compilation and testing commands for all directories
.PHONY: help test compile backend gas GoogleAppsScripts lambda-functions start tunnel stop install clean status _get_tunnel_url clasp _run_in_new_terminal _kill_tunnel _kill_backend _check_process _deploy_lambda

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
	@echo "  make test                - Run all tests (backend, lambda, gas)"
	@echo "  make test [path]         - Run tests for specific path (backend, lambda/functions, GoogleAppsScripts)"
	@echo ""
	@echo "🔨 Compilation Commands:"
	@echo "  make compile             - Compile all repos (backend, lambda, gas)"
	@echo "  make compile [path]      - Compile specific path (backend, lambda/functions, GoogleAppsScripts)"
	@echo ""
	@echo "📦 Google Apps Script Deployment:"
	@echo "  make clasp push <project> - Push GAS project to remote (with diff comparison)"
	@echo "  make clasp pull <project> - Pull GAS project from remote (with diff comparison)"
	@echo "  make clasp deploy <project> - Full deployment (push + version management)"
	@echo ""
	@echo "📋 Examples:"
	@echo "  make test                - Run all tests"
	@echo "  make test backend        - Run backend tests"
	@echo "  make test lambda/functions - Run lambda tests"
	@echo "  make compile             - Compile all repos"
	@echo "  make compile backend    - Compile backend"
	@echo ""
	@echo "🔧 Quick Start:"
	@echo "  1. make install          - Install dependencies"
	@echo "  2. make start            - Start server + tunnel"
	@echo "  3. make test             - Run tests"

# Handle test command arguments
ifneq ($(filter test,$(MAKECMDGOALS)),)
  TEST_PATH := $(word 2,$(MAKECMDGOALS))
  ifneq ($(TEST_PATH),)
    $(eval $(TEST_PATH):;@:)
  endif
endif

# Handle test and compile command arguments
ifneq ($(filter test compile,$(MAKECMDGOALS)),)
  TEST_PATH := $(word 2,$(MAKECMDGOALS))
  COMPILE_PATH := $(word 2,$(MAKECMDGOALS))
  ifneq ($(TEST_PATH),)
    $(eval $(TEST_PATH):;@:)
  endif
  ifneq ($(COMPILE_PATH),)
    $(eval $(COMPILE_PATH):;@:)
  endif
endif

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

# Testing command (runs compilation first, then tests)
test:
	@TEST_PATH="$(word 2,$(MAKECMDGOALS))"; \
	if [ -z "$$TEST_PATH" ]; then \
		echo "🔨 Compiling all repos first..."; \
		python3 -c "import sys; sys.path.insert(0, '.'); from scripts.compilation.compile_main import compile_all; compile_result = compile_all(); sys.exit(compile_result)"; \
		COMPILE_EXIT=$$?; \
		if [ $$COMPILE_EXIT -ne 0 ]; then \
			echo "❌ Compilation failed. Skipping tests."; \
			exit $$COMPILE_EXIT; \
		fi; \
		echo "🧪 Running all tests..."; \
		python3 -c "import sys; sys.path.insert(0, '.'); from scripts.testing.run_tests import run_all_tests; sys.exit(run_all_tests())"; \
	else \
		echo "🔨 Compiling $$TEST_PATH first..."; \
		python3 -c "import sys; sys.path.insert(0, '.'); from scripts.compilation.compile_main import compile_for_path; compile_result = compile_for_path('$$TEST_PATH'); sys.exit(compile_result)"; \
		COMPILE_EXIT=$$?; \
		if [ $$COMPILE_EXIT -ne 0 ]; then \
			echo "❌ Compilation failed. Skipping tests."; \
			exit $$COMPILE_EXIT; \
		fi; \
		echo "🧪 Running tests for: $$TEST_PATH"; \
		python3 -c "import sys; sys.path.insert(0, '.'); from scripts.testing.run_tests import run_tests_for_path; sys.exit(run_tests_for_path('$$TEST_PATH'))"; \
	fi

# Compilation command
compile:
	@COMPILE_PATH="$(word 2,$(MAKECMDGOALS))"; \
	if [ -z "$$COMPILE_PATH" ]; then \
		echo "🔨 Compiling all repos..."; \
		python3 -c "import sys; sys.path.insert(0, '.'); from scripts.compilation.compile_main import compile_all; sys.exit(compile_all())"; \
	else \
		echo "🔨 Compiling: $$COMPILE_PATH"; \
		python3 -c "import sys; sys.path.insert(0, '.'); from scripts.compilation.compile_main import compile_for_path; sys.exit(compile_for_path('$$COMPILE_PATH'))"; \
	fi

# Catch-all target to prevent Make from trying to build arguments as targets
%:
	@:

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
		bash scripts/deployment/push_google.sh "$(CLASP_PROJECT)"; \
	elif [ "$(CLASP_CMD)" = "pull" ]; then \
		bash scripts/deployment/pull_google.sh "$(CLASP_PROJECT)"; \
	elif [ "$(CLASP_CMD)" = "deploy" ]; then \
		bash scripts/deployment/deploy_google.sh "$(CLASP_PROJECT)"; \
	else \
		echo "❌ Unknown command: $(CLASP_CMD)"; \
		echo "Valid commands: push, pull, deploy"; \
		exit 1; \
	fi
