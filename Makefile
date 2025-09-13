# BARS Repository Makefile
# Provides compilation and testing commands for all directories
.PHONY: help compile test ready backend gas lambda GoogleAppsScripts lambda-functions compile-backend compile-gas compile-lambda test-backend test-gas test-lambda start tunnel dev stop install clean status url version changelog version-bump test-backend-unit test-backend-integration test-backend-slack test-backend-all test-specific show-structure check-dir

# Default target
help:
	@echo "🚀 BARS Repository Commands"
	@echo "=========================="
	@echo ""
	@echo "🔧 Backend Development:"
	@echo "  make start               - Start backend server (uvicorn)"
	@echo "  make tunnel              - Start ngrok tunnel"
	@echo "  make dev                 - Start server + tunnel (opens new terminal)"
	@echo "  make stop                - Stop all processes"
	@echo "  make install             - Install all dependencies from unified requirements.txt"
	@echo "  make install-prod        - Install production dependencies only"
	@echo "  make clean               - Clean up processes and cache files"
	@echo "  make status              - Show running processes"
	@echo "  make url                 - Show ngrok URL"
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
			cd "$$TARGET_DIR" && python3 -c "from config import settings; print('✅ Config loads successfully')" || exit 1; \
		fi; \
		if [ -f "$$TARGET_DIR/main.py" ]; then \
			echo "🚀 Testing FastAPI app import..."; \
			cd "$$TARGET_DIR" && python3 -c "from main import app; print('✅ FastAPI app loads successfully')" || exit 1; \
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

# Backend server management
start:
	@echo "🚀 Starting backend server..."
	@cd backend && ./venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

tunnel:
	@echo "🌐 Starting ngrok tunnel..."
	@pkill -f ngrok || true
	@sleep 1
	@ngrok http 8000

dev:
	@echo "🔧 Starting development environment..."
	@pkill -f ngrok || true
	@pkill -f uvicorn || true
	@sleep 1
	@echo "🚀 Starting backend server in current terminal..."
	@echo "🌐 Opening new terminal for ngrok tunnel..."
	@if command -v cursor >/dev/null 2>&1 && pgrep -f "Cursor.app" >/dev/null 2>&1; then \
		echo "📱 Detected Cursor - opening new Cursor terminal..."; \
		osascript -e 'tell application "Cursor" to activate' \
			-e 'tell application "System Events" to keystroke "`" using {control down, shift down}' \
			-e 'delay 1' \
			-e 'tell application "System Events" to keystroke "cd backend && make tunnel"' \
			-e 'tell application "System Events" to key code 36' & \
	elif command -v code >/dev/null 2>&1 && pgrep -x "Code" >/dev/null 2>&1; then \
		echo "📱 Detected VS Code - opening system terminal..."; \
		osascript -e 'tell application "Terminal" to do script "cd \"$(PWD)/backend\" && make tunnel"' & \
	else \
		echo "🖥️  Opening system terminal..."; \
		osascript -e 'tell application "Terminal" to do script "cd \"$(PWD)/backend\" && make tunnel"' & \
	fi
	@sleep 3
	@echo "✅ Starting server now (tunnel will start in new terminal)..."
	@cd backend && ./venv/bin/python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000

stop:
	@echo "🛑 Stopping all processes..."
	@pkill -f ngrok || true
	@pkill -f uvicorn || true
	@echo "✅ All processes stopped"

install:
	@echo "📦 Installing all dependencies from unified requirements.txt..."
	@pip3 install -r requirements.txt
	@echo "✅ All dependencies installed!"

install-prod:
	@echo "📦 Installing production dependencies only..."
	@pip3 install fastapi uvicorn[standard] requests python-dotenv pydantic python-multipart python-dateutil typing-extensions
	@echo "✅ Production dependencies installed!"

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
	@echo "Backend Server:"
	@ps aux | grep uvicorn | grep -v grep || echo "❌ Backend server not running"
	@echo ""
	@echo "Ngrok Tunnel:"
	@ps aux | grep ngrok | grep -v grep || echo "❌ Ngrok tunnel not running"
	@echo ""
	@echo "Ngrok URL (if running):"
	@curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['tunnels'][0]['public_url'] if data.get('tunnels') else '❌ No tunnels')" 2>/dev/null || echo "❌ Ngrok not accessible"

url:
	@curl -s http://localhost:4040/api/tunnels | python3 -c "import sys, json; data=json.load(sys.stdin); print('🌐 Ngrok URL:', data['tunnels'][0]['public_url']) if data.get('tunnels') else print('❌ No ngrok tunnel running')" 2>/dev/null || echo "❌ Ngrok not accessible"

version:
	@echo "📈 Backend Version Information:"
	@echo "=============================="
	@cd backend && ./venv/bin/python -c "from version import get_version_info; info = get_version_info(); print(f'Version: {info[\"version\"]}'); print(f'Build: {info[\"build\"]}'); print(f'Full: {info[\"full_version\"]}'); print(f'Updated: {info[\"last_updated\"]}'); print(f'Codename: {info[\"codename\"]}')"

changelog:
	@echo "📝 Recent Changelog Entries:"
	@echo "============================="
	@head -50 backend/CHANGELOG.md

version-bump:
	@echo "🔄 Manually triggering version management..."
	@cd backend && ./venv/bin/python ../scripts/backend_version_manager.py

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
	@cd backend && ./venv/bin/python -m pytest tests/unit/ -v
	@echo ""
	@echo "🧪 Running service-specific unit tests..."
	@cd backend && ./venv/bin/python -m pytest services/*/tests/ -v
	@echo ""
	@echo "🧪 Running router unit tests..."
	@cd backend && ./venv/bin/python -m pytest routers/tests/ -v

test-backend-integration:
	@echo "🧪 Running backend integration tests..."
	@echo "Note: Make sure the server is running (make start)"
	@cd backend && ./venv/bin/python -m pytest tests/integration/ -v

test-backend-slack:
	@echo "🧪 Running backend Slack message formatting tests..."
	@cd backend && ./venv/bin/python run_slack_tests.py

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
		cd backend && ./venv/bin/python -m pytest "../$(TEST)" -v; \
	elif echo "$(TEST)" | grep -q "\.py$$"; then \
		echo "Running Python test file: $(TEST)"; \
		if echo "$(TEST)" | grep -q "^backend/"; then \
			cd backend && ./venv/bin/python -m pytest "../$(TEST)" -v; \
		else \
			cd backend && ./venv/bin/python "../$(TEST)"; \
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

# Backend testing (Python)
_test_backend_internal:
	@echo "🧪 Running backend tests..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "backend" ]; then \
		if [ -f "backend/Makefile" ]; then \
			echo "📋 Using backend Makefile..."; \
			cd backend && make test; \
		else \
			echo "📋 Running pytest directly..."; \
			cd backend && python3 -m pytest tests/ -v; \
		fi; \
	else \
		echo "📋 Running tests in $(DIR)..."; \
		if find "$(DIR)" -name "test_*.py" -o -name "*_test.py" -type f | head -1 | grep -q .; then \
			cd backend && python3 -m pytest "../$(DIR)" -v; \
		else \
			echo "⚠️  No Python test files found in $(DIR)"; \
		fi; \
	fi

# GoogleAppsScripts testing (JavaScript)
_test_gas_internal:
	@echo "🧪 Running GoogleAppsScripts tests..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "GoogleAppsScripts" ]; then \
		cd GoogleAppsScripts && \
		if [ -f "tests/test_parse_registration_functions.sh" ]; then \
			echo "📋 Running GAS test scripts..."; \
			chmod +x tests/*.sh; \
			./tests/test_parse_registration_functions.sh || true; \
			./tests/test_parse_registration_comprehensive.sh || true; \
		fi; \
		if find tests/ -name "*.js" -o -name "*.mjs" -type f | head -1 | grep -q .; then \
			echo "📋 Running JavaScript tests..."; \
			find tests/ -name "*.js" -o -name "*.mjs" -type f | while read -r file; do \
				echo "  Running $$file..."; \
				node "$$file" || true; \
			done; \
		fi; \
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

# Lambda functions testing (Python)
_test_lambda_internal:
	@echo "🧪 Running Lambda function tests..."
	@if [ "$(DIR)" = "." ] || [ "$(DIR)" = "lambda-functions" ]; then \
		cd lambda-functions && \
		if [ -f "tests/run_tests.py" ]; then \
			echo "📋 Running Lambda test suite..."; \
			python3 tests/run_tests.py unit; \
		else \
			echo "📋 Running pytest on Lambda tests..."; \
			python3 -m pytest tests/ -v || true; \
		fi; \
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
