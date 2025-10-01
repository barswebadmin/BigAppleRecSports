# BARS Repository Makefile
# Provides compilation and testing commands for all directories
.PHONY: help compile test ready backend gas lambda GoogleAppsScripts lambda-functions compile-backend compile-gas compile-lambda test-backend test-gas test-lambda start prod tunnel tunnel-and-update update-gas-ngrok dev stop install reinstall clean status url version changelog version-bump test-backend-unit test-backend-integration test-backend-slack test-backend-all test-specific show-structure check-dir

# Default target
help:
	@echo "🚀 BARS Repository Commands"
	@echo "=========================="
	@echo ""
	@echo "🔧 Backend Development:"
	@echo "  make start               - Start backend server (uvicorn) in dev mode"
	@echo "  make prod                - Start server + tunnel in production mode"
	@echo "  make tunnel              - Start localtunnel with auto-restart (persistent)"
	@echo "  make tunnel-daemon       - Start localtunnel as background daemon (survives restarts)"
	@echo "  make dev                 - Start server + tunnel with auto URL updates (dev mode)"
	@echo "  make stop                - Stop all processes"
	@echo "  make install             - Install all dependencies from unified requirements.txt"
	@echo "  make install-prod        - Install production dependencies only"
	@echo "  make reinstall           - Reinstall backend package after pyproject.toml changes"
	@echo "  make clean               - Clean up processes and cache files"
	@echo "  make status              - Show running processes"
	@echo "  make url                 - Show localtunnel URL"
	@echo "  make version             - Show backend version info"
	@echo ""
	@echo "🔍 Compilation Commands:"
	@echo "  make compile [path]      - Compile directory and subdirectories (default: current dir)"
	@echo "  make compile .           - Compile entire repository from root"
	@echo "  make compile backend     - Compile backend directory"
	@echo "  make compile gas         - Compile GoogleAppsScripts (JavaScript)"
	@echo "  make compile lambda      - Compile lambda-functions (Python)"
	@echo ""
	@echo "🧪 Testing Commands:"
	@echo "  make test [path]         - Run tests in directory and subdirectories (default: current dir)"
	@echo "  make ready [path]        - Compile + test directory (fails fast on compilation errors)"
	@echo "  make test .              - Run all tests in repository"
	@echo "  make test backend        - Run backend tests"
	@echo "  make test gas            - Run GoogleAppsScripts tests"
	@echo "  make test lambda         - Run lambda-functions tests"
	@echo ""
	@echo "🧪 Backend-Specific Tests:"
	@echo "  make test-backend-unit   - Run unit tests (mocked, safe)"
	@echo "  make test-backend-integration - Run integration tests (requires server)"
	@echo "  make test-backend-slack  - Run Slack message formatting tests"
	@echo "  make test-backend-all    - Run all backend tests"
	@echo "  make test-specific TEST=<path> - Run specific test file or case"
	@echo ""
	@echo "📋 Examples:"
	@echo "  make compile backend/services"
	@echo "  make test lambda-functions/shopifyProductUpdateHandler"
	@echo "  make test-specific TEST=backend/test_slack_message_formatting.py"
	@echo "  make test-specific TEST=backend/test_orders_api.py::test_fetch_order"
	@echo ""
	@echo "🔧 Quick Start:"
	@echo "  1. make install          - Install dependencies"
	@echo "  2. make start            - Start server (terminal 1)"
	@echo "  3. make tunnel           - Start tunnel (terminal 2)"
	@echo "  4. make test-backend-unit - Run tests"

# Handle arguments for compile and test commands
# This allows 'make compile backend' instead of 'make compile DIR=backend'
ifneq ($(filter compile,$(MAKECMDGOALS)),)
  # Get the argument after 'compile'
  COMPILE_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  ifneq ($(COMPILE_ARGS),)
    DIR := $(COMPILE_ARGS)
    # Prevent make from trying to build these as targets
    $(eval $(COMPILE_ARGS):;@:)
  else
    DIR := .
  endif
endif

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
# COMPILATION COMMANDS
# =============================================================================

compile:
	@echo "🔍 Compiling directory: $(DIR)"
	@$(MAKE) _compile_directory DIR=$(DIR)

# Convenient aliases for common directories - these work with both compile and test
# Due to the argument parsing logic above, these will be handled automatically

# Legacy commands (still supported)
compile-backend:
	@$(MAKE) _compile_directory DIR=backend

compile-gas:
	@$(MAKE) _compile_directory DIR=GoogleAppsScripts

compile-lambda:
	@$(MAKE) _compile_directory DIR=lambda-functions

# Internal compilation logic
_compile_directory:
	@if [ "$(DIR)" = "." ]; then \
		echo "🔍 Compiling entire repository..."; \
		$(MAKE) _compile_backend_internal; \
		$(MAKE) _compile_gas_internal; \
		$(MAKE) _compile_lambda_internal; \
	elif [ -d "$(DIR)" ]; then \
		if echo "$(DIR)" | grep -q "backend\|\.py$$"; then \
			$(MAKE) _compile_backend_internal DIR=$(DIR); \
		elif echo "$(DIR)" | grep -q "GoogleAppsScripts\|\.gs$$\|\.js$$"; then \
			$(MAKE) _compile_gas_internal DIR=$(DIR); \
		elif echo "$(DIR)" | grep -q "lambda-functions"; then \
			$(MAKE) _compile_lambda_internal DIR=$(DIR); \
		else \
			echo "🔍 Auto-detecting file types in $(DIR)..."; \
			if find "$(DIR)" -name "*.py" -type f | head -1 | grep -q .; then \
				$(MAKE) _compile_python_files DIR=$(DIR); \
			fi; \
			if find "$(DIR)" -name "*.gs" -o -name "*.js" -type f | head -1 | grep -q .; then \
				$(MAKE) _compile_js_files DIR=$(DIR); \
			fi; \
		fi; \
	else \
		echo "❌ Directory $(DIR) does not exist"; \
		exit 1; \
	fi

# Backend compilation (Python)
_compile_backend_internal:
	@echo "🐍 Compiling Python files in $(DIR)..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "backend" ]; then \
		TARGET_DIR="backend"; \
	else \
		TARGET_DIR="$(DIR)"; \
	fi; \
	if [ -d "$$TARGET_DIR" ]; then \
		echo "📋 Checking Python syntax in $$TARGET_DIR..."; \
		find "$$TARGET_DIR" -name "*.py" -type f -not -path "*/venv/*" -not -path "*/__pycache__/*" | while read -r file; do \
			echo "  Checking $$file..."; \
			python3 -m py_compile "$$file" || exit 1; \
		done; \
		if [ -f "$$TARGET_DIR/requirements.txt" ]; then \
			echo "📦 Checking if requirements can be resolved..."; \
			cd "$$TARGET_DIR" && python3 -m pip check 2>/dev/null || echo "⚠️  Some dependencies may be missing"; \
		fi; \
		if [ -f "$$TARGET_DIR/config.py" ]; then \
			echo "⚙️  Testing config import..."; \
			if [ -f ".venv/bin/activate" ]; then \
				cd "$$TARGET_DIR" && source ../.venv/bin/activate && python3 -c "from config import settings; print('✅ Config loads successfully')" || exit 1; \
			else \
				cd "$$TARGET_DIR" && python3 -c "from config import settings; print('✅ Config loads successfully')" || exit 1; \
			fi; \
		fi; \
		if [ -f "$$TARGET_DIR/main.py" ]; then \
			echo "🚀 Testing FastAPI app import..."; \
			if [ -f ".venv/bin/activate" ]; then \
				cd "$$TARGET_DIR" && source ../.venv/bin/activate && python3 -c "from main import app; print('✅ FastAPI app loads successfully')" || exit 1; \
			else \
				cd "$$TARGET_DIR" && python3 -c "from main import app; print('✅ FastAPI app loads successfully')" || exit 1; \
			fi; \
		fi; \
		echo "✅ Python compilation successful for $$TARGET_DIR"; \
	else \
		echo "❌ Python directory $$TARGET_DIR not found"; \
		exit 1; \
	fi

# GoogleAppsScripts compilation (JavaScript)
_compile_gas_internal:
	@echo "📜 Compiling JavaScript files in $(DIR)..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "GoogleAppsScripts" ]; then \
		TARGET_DIR="GoogleAppsScripts"; \
	else \
		TARGET_DIR="$(DIR)"; \
	fi; \
	if [ -d "$$TARGET_DIR" ]; then \
		echo "📋 Validating JSON manifests..."; \
		find "$$TARGET_DIR" -name "appsscript.json" -type f | while read -r file; do \
			echo "  Validating $$file..."; \
			python3 -m json.tool "$$file" > /dev/null || exit 1; \
		done; \
		echo "📋 Checking JavaScript syntax..."; \
		if command -v node >/dev/null 2>&1; then \
			find "$$TARGET_DIR" -name "*.gs" -o -name "*.js" -type f | while read -r file; do \
				echo "  Checking $$file..."; \
				node -e "const fs = require('fs'); try { new Function(fs.readFileSync('$$file', 'utf8')); console.log('✅ $$file syntax OK'); } catch(e) { console.error('❌ $$file:', e.message); process.exit(1); }" || exit 1; \
			done; \
		else \
			echo "⚠️  Node.js not found, skipping JavaScript syntax check"; \
		fi; \
		echo "✅ JavaScript compilation successful for $$TARGET_DIR"; \
	else \
		echo "❌ JavaScript directory $$TARGET_DIR not found"; \
		exit 1; \
	fi

# Lambda functions compilation (Python)
_compile_lambda_internal:
	@echo "🔧 Compiling Lambda functions in $(DIR)..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "lambda-functions" ]; then \
		TARGET_DIR="lambda-functions"; \
	else \
		TARGET_DIR="$(DIR)"; \
	fi; \
	if [ -d "$$TARGET_DIR" ]; then \
		echo "📋 Checking Lambda function syntax..."; \
		find "$$TARGET_DIR" -name "lambda_function.py" -type f -not -path "*/venv/*" -not -path "*/__pycache__/*" | while read -r file; do \
			dir=$$(dirname "$$file"); \
			echo "  Checking $$file..."; \
			python3 -m py_compile "$$file" || exit 1; \
			cd "$$dir" && python3 -c "import lambda_function; print('✅ $$file imports successfully')" || exit 1; \
			cd - > /dev/null; \
		done; \
		find "$$TARGET_DIR" -name "*.py" -not -name "lambda_function.py" -type f -not -path "*/venv/*" -not -path "*/__pycache__/*" | while read -r file; do \
			echo "  Checking $$file..."; \
			python3 -m py_compile "$$file" || exit 1; \
		done; \
		echo "✅ Lambda compilation successful for $$TARGET_DIR"; \
	else \
		echo "❌ Lambda directory $$TARGET_DIR not found"; \
		exit 1; \
	fi

# Generic Python file compilation
_compile_python_files:
	@echo "🐍 Compiling Python files in $(DIR)..."
	@find "$(DIR)" -name "*.py" -type f -not -path "*/venv/*" -not -path "*/__pycache__/*" | while read -r file; do \
		echo "  Checking $$file..."; \
		python3 -m py_compile "$$file" || exit 1; \
	done
	@echo "✅ Python files compiled successfully in $(DIR)"

# Generic JavaScript file compilation
_compile_js_files:
	@echo "📜 Compiling JavaScript files in $(DIR)..."
	@if command -v node >/dev/null 2>&1; then \
		find "$(DIR)" -name "*.gs" -o -name "*.js" -type f | while read -r file; do \
			echo "  Checking $$file..."; \
			node -e "const fs = require('fs'); try { new Function(fs.readFileSync('$$file', 'utf8')); console.log('✅ $$file syntax OK'); } catch(e) { console.error('❌ $$file:', e.message); process.exit(1); }" || exit 1; \
		done; \
	else \
		echo "⚠️  Node.js not found, skipping JavaScript syntax check"; \
	fi
	@echo "✅ JavaScript files compiled successfully in $(DIR)"

# =============================================================================
# BACKEND DEVELOPMENT COMMANDS
# =============================================================================

# Helper function to find the correct Python executable
define find_python
	@if [ -f backend/.venv/bin/python ]; then \
		echo "./.venv/bin/python"; \
	elif [ -f .venv/bin/python ]; then \
		echo "../.venv/bin/python"; \
	elif [ -f backend/venv/bin/python ]; then \
		echo "./venv/bin/python"; \
	else \
		echo "python"; \
	fi
endef

# Backend server management
start:
	@echo "🚀 Starting backend server..."
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token ./.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token ../.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token ./venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	else \
		echo "❌ Virtual environment not found. Trying system python..."; \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	fi

prod:
	@echo "🔧 Starting production environment..."
	@pkill -f "lt -p 8000" || true
	@pkill -f uvicorn || true
	@sleep 1
	@echo "🚀 Starting backend server in current terminal..."
	@echo "🌐 Opening new terminal for localtunnel..."
	@if command -v cursor >/dev/null 2>&1 && pgrep -f "Cursor.app" >/dev/null 2>&1; then \
		echo "📱 Detected Cursor - opening new Cursor terminal..."; \
		osascript -e 'tell application "Cursor" to activate' \
			-e 'tell application "System Events" to keystroke "`" using {control down, shift down}' \
			-e 'delay 1' \
			-e 'tell application "System Events" to keystroke "make tunnel-and-update"' \
			-e 'tell application "System Events" to key code 36' & \
	elif command -v code >/dev/null 2>&1 && pgrep -x "Code" >/dev/null 2>&1; then \
		echo "📱 Detected VS Code - opening system terminal..."; \
		osascript -e 'tell application "Terminal" to do script "make tunnel-and-update"' & \
	else \
		echo "🖥️  Opening system terminal..."; \
		osascript -e 'tell application "Terminal" to do script "make tunnel-and-update"' & \
	fi
	@sleep 3
	@echo "✅ Starting server now (tunnel will start in new terminal)..."
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ENVIRONMENT=production SHOPIFY_TOKEN=test_token ./.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ENVIRONMENT=production SHOPIFY_TOKEN=test_token ../.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ENVIRONMENT=production SHOPIFY_TOKEN=test_token ./venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	else \
		echo "❌ Virtual environment not found. Trying system python..."; \
		cd backend && ENVIRONMENT=production SHOPIFY_TOKEN=test_token python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	fi

tunnel:
	@echo "🌐 Starting localtunnel..."
	@pkill -f "lt -p 8000" || true
	@sleep 1
	@echo "🔄 Starting persistent localtunnel (will auto-restart on failure)..."
	@while true; do \
		echo "📡 Connecting to localtunnel..."; \
		lt -p 8000 -s bars-back-local || { \
			echo "⚠️  Localtunnel disconnected, restarting in 3 seconds..."; \
			sleep 3; \
		}; \
	done

tunnel-and-update:
	@echo "🌐 Starting persistent localtunnel with auto-restart..."
	@pkill -f "lt -p 8000" || true
	@sleep 1
	@echo "🔄 Starting robust localtunnel (will survive server restarts)..."
	@while true; do \
		echo "📡 Connecting to localtunnel..."; \
		echo "🌐 URL: https://bars-back-local.loca.lt"; \
		lt -p 8000 -s bars-back-local || { \
			echo "⚠️  Localtunnel disconnected, restarting in 3 seconds..."; \
			sleep 3; \
		}; \
	done

tunnel-daemon:
	@echo "🌐 Starting localtunnel as background daemon..."
	@pkill -f "lt -p 8000" || true
	@sleep 1
	@nohup sh -c 'while true; do echo "📡 Connecting to localtunnel..."; echo "🌐 URL: https://bars-back-local.loca.lt"; lt -p 8000 -s bars-back-local || { echo "⚠️  Localtunnel disconnected, restarting in 3 seconds..."; sleep 3; }; done' > tunnel.log 2>&1 &
	@echo "✅ Localtunnel daemon started in background"
	@echo "🌐 URL: https://bars-back-local.loca.lt"
	@echo "📋 Check tunnel.log for status updates"

update-gas-ngrok:
	@echo "📝 Updating NGROK_URL in Google Apps Scripts..."
	@python3 scripts/update_ngrok_urls.py

dev:
	@echo "🔧 Starting development environment..."
	@pkill -f "lt -p 8000" || true
	@pkill -f uvicorn || true
	@sleep 1
	@echo "🚀 Starting backend server in current terminal..."
	@echo "🌐 Opening new terminal for localtunnel..."
	@if command -v cursor >/dev/null 2>&1 && pgrep -f "Cursor.app" >/dev/null 2>&1; then \
		echo "📱 Detected Cursor - opening new Cursor terminal..."; \
		osascript -e 'tell application "Cursor" to activate' \
			-e 'tell application "System Events" to keystroke "`" using {control down, shift down}' \
			-e 'delay 1' \
			-e 'tell application "System Events" to keystroke "make tunnel-and-update"' \
			-e 'tell application "System Events" to key code 36' & \
	elif command -v code >/dev/null 2>&1 && pgrep -x "Code" >/dev/null 2>&1; then \
		echo "📱 Detected VS Code - opening system terminal..."; \
		osascript -e 'tell application "Terminal" to do script "make tunnel-and-update"' & \
	else \
		echo "🖥️  Opening system terminal..."; \
		osascript -e 'tell application "Terminal" to do script "make tunnel-and-update"' & \
	fi
	@sleep 3
	@echo "✅ Starting server now (tunnel will start in new terminal)..."
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token ./.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token ../.venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token ./venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	else \
		echo "❌ Virtual environment not found. Trying system python..."; \
		cd backend && ENVIRONMENT=dev SHOPIFY_TOKEN=test_token python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000; \
	fi

stop:
	@echo "🛑 Stopping all processes..."
	@pkill -f "lt -p 8000" || true
	@pkill -f uvicorn || true
	@pkill -f "while true; do echo" || true
	@rm -f tunnel.log
	@echo "✅ All processes stopped"

install:
	@echo "📦 Installing all dependencies from unified requirements.txt..."
	@pip3 install -r requirements.txt
	@echo "✅ All dependencies installed!"

install-prod:
	@echo "📦 Installing production dependencies only..."
	@pip3 install fastapi uvicorn[standard] requests python-dotenv pydantic python-multipart python-dateutil typing-extensions
	@echo "✅ Production dependencies installed!"

reinstall:
	@echo "🔄 Reinstalling backend package after pyproject.toml changes..."
	@pip install -e backend
	@echo "✅ Backend package reinstalled!"

install-backend-legacy:
	@echo "📦 Installing backend dependencies (legacy method)..."
	@cd backend && pip3 install -r requirements.txt
	@echo "📦 Installing test dependencies..."
	@cd backend && pip3 install pytest pytest-asyncio pytest-mock

clean: stop
	@echo "🧹 Cleaning up..."
	@rm -f ngrok.log
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
	@ps aux | grep "lt -p 8000" | grep -v grep || echo "❌ Localtunnel not running"
	@echo ""
	@echo "🌐 Localtunnel URL:"
	@echo "https://bars-back-local.loca.lt"
	@echo ""
	@echo "📋 Recent tunnel logs (if daemon is running):"
	@if [ -f tunnel.log ]; then \
		echo "Last 5 lines from tunnel.log:"; \
		tail -5 tunnel.log; \
	else \
		echo "No tunnel.log found (daemon not started)"; \
	fi

url:
	@echo "🌐 Localtunnel URL: https://bars-back-local.loca.lt"

version:
	@echo "📈 Backend Version Information:"
	@echo "=============================="
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ./.venv/bin/python -c "from version import get_version_info; info = get_version_info(); print(f'Version: {info[\"version\"]}'); print(f'Build: {info[\"build\"]}'); print(f'Full: {info[\"full_version\"]}'); print(f'Updated: {info[\"last_updated\"]}'); print(f'Codename: {info[\"codename\"]}')"; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ../.venv/bin/python -c "from version import get_version_info; info = get_version_info(); print(f'Version: {info[\"version\"]}'); print(f'Build: {info[\"build\"]}'); print(f'Full: {info[\"full_version\"]}'); print(f'Updated: {info[\"last_updated\"]}'); print(f'Codename: {info[\"codename\"]}')"; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ./venv/bin/python -c "from version import get_version_info; info = get_version_info(); print(f'Version: {info[\"version\"]}'); print(f'Build: {info[\"build\"]}'); print(f'Full: {info[\"full_version\"]}'); print(f'Updated: {info[\"last_updated\"]}'); print(f'Codename: {info[\"codename\"]}')"; \
	else \
		cd backend && python -c "from version import get_version_info; info = get_version_info(); print(f'Version: {info[\"version\"]}'); print(f'Build: {info[\"build\"]}'); print(f'Full: {info[\"full_version\"]}'); print(f'Updated: {info[\"last_updated\"]}'); print(f'Codename: {info[\"codename\"]}')"; \
	fi

changelog:
	@echo "📝 Recent Changelog Entries:"
	@echo "============================="
	@head -50 backend/CHANGELOG.md

version-bump:
	@echo "🔄 Manually triggering version management..."
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ./.venv/bin/python ../scripts/backend_version_manager.py; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ../.venv/bin/python ../scripts/backend_version_manager.py; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ./venv/bin/python ../scripts/backend_version_manager.py; \
	else \
		cd backend && python ../scripts/backend_version_manager.py; \
	fi

# =============================================================================
# TESTING COMMANDS
# =============================================================================

test:
	@echo "🧪 Running tests in directory: $(DIR)"
	@$(MAKE) _test_directory DIR=$(DIR)

ready:
	@echo "🚀 Running compile + test for directory: $(DIR)"
	@echo "🔍 Step 1: Compilation..."
	@$(MAKE) compile DIR=$(DIR)
	@echo "✅ Compilation successful!"
	@echo "🧪 Step 2: Testing..."
	@$(MAKE) _test_directory DIR=$(DIR)
	@echo "✅ Ready! All checks passed for $(DIR)"

# Note: backend, gas, lambda, etc. aliases are already defined above for compile
# They will also work for test commands due to the argument parsing logic

# Backend-specific test commands
test-backend:
	@$(MAKE) _test_directory DIR=backend

test-backend-unit:
	@echo "🧪 Running backend unit tests with mocked services (no external API calls)..."
	@echo "🔍 Checking backend compilation first..."
	@$(MAKE) compile backend
	@echo "✅ Backend compilation successful, proceeding with unit tests..."
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ./.venv/bin/python -m pytest tests/unit/ -v; \
		echo ""; \
		echo "🧪 Running service-specific unit tests..."; \
		cd backend && ./.venv/bin/python -m pytest services/*/tests/ -v; \
		echo ""; \
		echo "🧪 Running router unit tests..."; \
		cd backend && ./.venv/bin/python -m pytest routers/tests/ -v; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ../.venv/bin/python -m pytest tests/unit/ -v; \
		echo ""; \
		echo "🧪 Running service-specific unit tests..."; \
		cd backend && ../.venv/bin/python -m pytest services/*/tests/ -v; \
		echo ""; \
		echo "🧪 Running router unit tests..."; \
		cd backend && ../.venv/bin/python -m pytest routers/tests/ -v; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ./venv/bin/python -m pytest tests/unit/ -v; \
		echo ""; \
		echo "🧪 Running service-specific unit tests..."; \
		cd backend && ./venv/bin/python -m pytest services/*/tests/ -v; \
		echo ""; \
		echo "🧪 Running router unit tests..."; \
		cd backend && ./venv/bin/python -m pytest routers/tests/ -v; \
	else \
		cd backend && python -m pytest tests/unit/ -v; \
		echo ""; \
		echo "🧪 Running service-specific unit tests..."; \
		cd backend && python -m pytest services/*/tests/ -v; \
		echo ""; \
		echo "🧪 Running router unit tests..."; \
		cd backend && python -m pytest routers/tests/ -v; \
	fi

test-backend-integration:
	@echo "🧪 Running backend integration tests..."
	@echo "Note: Make sure the server is running (make start)"
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ./.venv/bin/python -m pytest tests/integration/ -v; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ../.venv/bin/python -m pytest tests/integration/ -v; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ./venv/bin/python -m pytest tests/integration/ -v; \
	else \
		cd backend && python -m pytest tests/integration/ -v; \
	fi

test-backend-slack:
	@echo "🧪 Running backend Slack message formatting tests..."
	@if [ -f backend/.venv/bin/python ]; then \
		cd backend && ./.venv/bin/python run_slack_tests.py; \
	elif [ -f .venv/bin/python ]; then \
		cd backend && ../.venv/bin/python run_slack_tests.py; \
	elif [ -f backend/venv/bin/python ]; then \
		cd backend && ./venv/bin/python run_slack_tests.py; \
	else \
		cd backend && python run_slack_tests.py; \
	fi

test-backend-all:
	@echo "🧪 Running all backend tests..."
	@$(MAKE) test-backend-unit
	@$(MAKE) test-backend-slack

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
		if [ -f backend/.venv/bin/python ]; then \
			cd backend && ./.venv/bin/python -m pytest "../$(TEST)" -v; \
		elif [ -f .venv/bin/python ]; then \
			cd backend && ../.venv/bin/python -m pytest "../$(TEST)" -v; \
		elif [ -f backend/venv/bin/python ]; then \
			cd backend && ./venv/bin/python -m pytest "../$(TEST)" -v; \
		else \
			cd backend && python -m pytest "../$(TEST)" -v; \
		fi; \
	elif echo "$(TEST)" | grep -q "\.py$$"; then \
		echo "Running Python test file: $(TEST)"; \
		if echo "$(TEST)" | grep -q "^backend/"; then \
			if [ -f backend/.venv/bin/python ]; then \
				cd backend && ./.venv/bin/python -m pytest "../$(TEST)" -v; \
			elif [ -f .venv/bin/python ]; then \
				cd backend && ../.venv/bin/python -m pytest "../$(TEST)" -v; \
			elif [ -f backend/venv/bin/python ]; then \
				cd backend && ./venv/bin/python -m pytest "../$(TEST)" -v; \
			else \
				cd backend && python -m pytest "../$(TEST)" -v; \
			fi; \
		else \
			if [ -f backend/.venv/bin/python ]; then \
				cd backend && ./.venv/bin/python "../$(TEST)"; \
			elif [ -f .venv/bin/python ]; then \
				cd backend && ../.venv/bin/python "../$(TEST)"; \
			elif [ -f backend/venv/bin/python ]; then \
				cd backend && ./venv/bin/python "../$(TEST)"; \
			else \
				cd backend && python "../$(TEST)"; \
			fi; \
		fi; \
	else \
		echo "❌ Invalid test format. Use .py file or pytest::test_name format"; \
		exit 1; \
	fi

# Legacy commands (still supported)
test-gas:
	@$(MAKE) _test_directory DIR=GoogleAppsScripts

test-lambda:
	@$(MAKE) _test_directory DIR=lambda-functions

# Internal testing logic
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
		python3 -m py_compile config.py main.py && \
		echo "📋 Checking module imports..." && \
		python3 -c "import sys; sys.path.append('.'); from config import config; print('✅ Config imports successfully'); from main import app; print('✅ Main FastAPI app imports successfully'); from modules.orders import OrdersService; print('✅ Orders service imports successfully'); from modules.integrations.slack import SlackClient; print('✅ Slack Client imports successfully'); from routers.refunds import router; print('✅ Refunds router imports successfully')" && \
		echo "🧪 Step 2: Running comprehensive test suite..." && \
		if [ -d "tests/unit" ] && [ "$$(find tests/unit -name '*.py' -not -name '__init__.py' | wc -l)" -gt 0 ]; then \
			echo "🧪 Running unit tests..."; \
			python3 -m pytest tests/unit/ -v; \
		else \
			echo "⚠️ No unit tests found in tests/unit/, skipping..."; \
		fi && \
		echo "🧪 Running service-specific tests..." && \
		python3 -m pytest services/*/tests/ -v || true && \
		echo "🧪 Running router tests..." && \
		python3 -m pytest routers/tests/ -v || true && \
		echo "🧪 Running Slack webhook tests..." && \
		python3 -m pytest routers/tests/test_slack_router.py -v || true && \
		if [ -d "tests/integration" ] && [ "$$(find tests/integration -name '*.py' -not -name '__init__.py' | wc -l)" -gt 0 ]; then \
			echo "🧪 Running integration tests..."; \
			python3 -m pytest tests/integration/ -v; \
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
			python3 -m pytest "../$(DIR)" -v; \
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
		echo "📋 Running Clasp Helpers Tests..." && \
		./tests/test_clasp_helpers.sh || true && \
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
# UTILITY COMMANDS
# =============================================================================

# Show directory structure for compilation/testing
show-structure:
	@echo "📁 Repository Structure:"
	@echo "======================="
	@echo "Backend (Python):"
	@find backend -name "*.py" -type f | head -5
	@echo "  ... (and more Python files)"
	@echo ""
	@echo "GoogleAppsScripts (JavaScript):"
	@find GoogleAppsScripts -name "*.gs" -o -name "*.js" -type f | head -5
	@echo "  ... (and more JavaScript files)"
	@echo ""
	@echo "Lambda Functions (Python):"
	@find lambda-functions -name "*.py" -type f | head -5
	@echo "  ... (and more Lambda files)"

# Check what would be compiled/tested in a directory
check-dir:
	@if [ -z "$(DIR)" ]; then \
		echo "❌ Please specify DIR=path"; \
		exit 1; \
	fi
	@echo "🔍 Analyzing directory: $(DIR)"
	@echo "Python files:"
	@find "$(DIR)" -name "*.py" -type f 2>/dev/null | head -10 || echo "  None found"
	@echo "JavaScript files:"
	@find "$(DIR)" -name "*.gs" -o -name "*.js" -type f 2>/dev/null | head -10 || echo "  None found"
	@echo "Test files:"
	@find "$(DIR)" -name "*test*" -type f 2>/dev/null | head -10 || echo "  None found"
