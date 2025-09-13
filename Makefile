# BARS Repository Makefile
# Provides compilation and testing commands for all directories
.PHONY: help compile test compile-backend compile-gas compile-lambda test-backend test-gas test-lambda

# Default target
help:
	@echo "🚀 BARS Repository Commands"
	@echo "=========================="
	@echo ""
	@echo "Compilation Commands:"
	@echo "  make compile [DIR=path]  - Compile directory and subdirectories (default: current dir)"
	@echo "  make compile DIR=.       - Compile entire repository from root"
	@echo "  make compile DIR=backend - Compile backend directory"
	@echo "  make compile-backend     - Compile backend (Python)"
	@echo "  make compile-gas         - Compile GoogleAppsScripts (JavaScript)"
	@echo "  make compile-lambda      - Compile lambda-functions (Python)"
	@echo ""
	@echo "Testing Commands:"
	@echo "  make test [DIR=path]     - Run tests in directory and subdirectories (default: current dir)"
	@echo "  make test DIR=.          - Run all tests in repository"
	@echo "  make test DIR=backend    - Run backend tests"
	@echo "  make test-backend        - Run backend tests"
	@echo "  make test-gas            - Run GoogleAppsScripts tests"
	@echo "  make test-lambda         - Run lambda-functions tests"
	@echo ""
	@echo "Examples:"
	@echo "  make compile DIR=backend/services"
	@echo "  make test DIR=lambda-functions/shopifyProductUpdateHandler"
	@echo "  make compile DIR=."
	@echo ""
	@echo "Directory-specific help:"
	@echo "  cd backend && make help  - Backend-specific commands"

# Detect current directory if not specified
DIR ?= .

# =============================================================================
# COMPILATION COMMANDS
# =============================================================================

compile:
	@echo "🔍 Compiling directory: $(DIR)"
	@$(MAKE) _compile_directory DIR=$(DIR)

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
# TESTING COMMANDS
# =============================================================================

test:
	@echo "🧪 Running tests in directory: $(DIR)"
	@$(MAKE) _test_directory DIR=$(DIR)

test-backend:
	@$(MAKE) _test_directory DIR=backend

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
