# Test Logic Consolidation Proposal

## Executive Summary

**Goal:** Consolidate all test logic from Makefile, GitHub workflows, and standalone scripts into centralized `scripts/` files that are language/project-agnostic where possible.

**Recommendation:** **Hybrid approach** - Use explicit configuration for project structure, with recursive discovery as fallback. This provides:
- Fast execution (no unnecessary scanning)
- Clear project boundaries
- Flexibility for edge cases
- Maintainability (single source of truth)

---

## Current State Analysis

### Test Execution Points

1. **Makefile** (`_test_backend_internal`, `_test_lambda_internal`, `_test_gas_internal`)
   - Inline bash logic
   - Compilation checks
   - Test discovery via `find`
   - Direct pytest/node/shell execution

2. **GitHub Workflows** (12 workflow files)
   - Duplicated inline bash logic
   - Direct pytest calls
   - Calls to standalone scripts
   - Environment variable setup

3. **Standalone Scripts**
   - `backend/scripts/run_tests.sh` - Backend API tests
   - `backend/scripts/run_consolidated_tests.py` - Slack tests
   - `backend/modules/run_integration_tests.py` - Integration tests
   - `backend/modules/integrations/slack/tests/run_slack_tests.py` - Slack formatting
   - `lambda/functions/tests/run_tests.py` - Lambda test runner
   - `GoogleAppsScripts/tests/*.sh` - GAS test scripts

### Common Patterns

1. **Environment Setup**
   ```bash
   export SHOPIFY_URL_ADMIN_DOMAIN="test-store.myshopify.com"
   export SHOPIFY_TOKEN="test_token"
   export ENVIRONMENT="test"
   export SLACK_REFUNDS_BOT_TOKEN="test_slack_token"
   ```

2. **Compilation Checks**
   - Python: `python -m py_compile`, `python -c "import ..."`
   - JavaScript: `new Function(content)`
   - JSON: `python3 -m json.tool`

3. **Test Discovery**
   - Python: `find . -name "test_*.py" -o -name "*_test.py"`
   - Shell: `find . -name "*test*.sh"`
   - JavaScript: `find . -name "*test*.js"`

4. **Test Execution**
   - Python: `pytest <path> -v`
   - Shell: `chmod +x <script> && ./<script>`
   - Node: `node <script>`

---

## Proposed Architecture

### Core Scripts (Language-Agnostic)

```
scripts/
├── test_runner.py              # Main entry point
├── test_config.py              # Project configuration
├── test_discovery.py           # Test file discovery (recursive + config)
├── test_execution.py           # Language-specific executors
├── test_environment.py        # Environment variable management
└── test_reporting.py          # Unified reporting/output
```

### Language-Specific Executors

```
scripts/test_execution/
├── __init__.py
├── python_executor.py         # pytest execution
├── shell_executor.py          # Shell script execution
├── javascript_executor.py     # Node.js execution
└── compilation_checker.py     # Compilation validation
```

---

## Configuration vs Discovery: Recommendation

### **Hybrid Approach (Recommended)**

**Primary:** Explicit configuration in `scripts/test_config.py`
**Fallback:** Recursive discovery for edge cases

**Rationale:**
- **Explicit config:** Fast, clear boundaries, maintainable
- **Recursive fallback:** Handles new test files automatically
- **Best of both:** Performance + flexibility

### Time/Implementation Comparison

| Approach | Implementation Time | Execution Speed | Maintainability | Flexibility |
|----------|-------------------|-----------------|-----------------|-------------|
| **Explicit Config** | 2-3 hours | ⚡ Fast (no scanning) | ⭐⭐⭐⭐⭐ Excellent | ⭐⭐⭐ Good |
| **Recursive Discovery** | 1 hour | 🐌 Slower (full scan) | ⭐⭐⭐ Good | ⭐⭐⭐⭐⭐ Excellent |
| **Hybrid** | 2.5-3.5 hours | ⚡ Fast (config) + fallback | ⭐⭐⭐⭐ Very Good | ⭐⭐⭐⭐⭐ Excellent |

**Recommendation: Hybrid** - 30% more implementation time, but 50% faster execution and better maintainability.

---

## Implementation Plan

### Phase 1: Core Infrastructure (2-3 hours)

1. **`scripts/test_config.py`** - Project configuration
   ```python
   PROJECTS = {
       "backend": {
           "type": "python",
           "root": "backend",
           "test_patterns": ["test_*.py", "*_test.py"],
           "test_dirs": ["tests/unit", "tests/integration", "routers/tests", "modules/*/tests"],
           "compilation_checks": ["config.py", "main.py"],
           "env_vars": {
               "SHOPIFY_URL_ADMIN_DOMAIN": "test-store.myshopify.com",
               "SHOPIFY_TOKEN": "test_token",
               "ENVIRONMENT": "test",
               "SLACK_REFUNDS_BOT_TOKEN": "test_slack_token"
           }
       },
       "lambda": {
           "type": "python",
           "root": "lambda/functions",
           "test_patterns": ["test_*.py"],
           "test_dirs": ["tests/unit", "tests/integration"],
           "compilation_checks": ["lambda_function.py"],
           "env_vars": {"AWS_DEFAULT_REGION": "us-east-1"}
       },
       "gas": {
           "type": "javascript",
           "root": "GoogleAppsScripts",
           "test_patterns": ["*test*.sh", "*test*.js"],
           "test_dirs": ["tests", "projects/*/tests"],
           "compilation_checks": ["appsscript.json"],
           "env_vars": {}
       }
   }
   ```

2. **`scripts/test_environment.py`** - Environment management
   ```python
   def setup_test_environment(project_name: str) -> dict:
       """Setup environment variables for a project."""
       config = PROJECTS[project_name]
       env = os.environ.copy()
       env.update(config["env_vars"])
       return env
   ```

3. **`scripts/test_discovery.py`** - Test file discovery
   ```python
   def discover_tests(project_name: str, use_config: bool = True) -> List[Path]:
       """Discover test files using config first, then recursive fallback."""
       config = PROJECTS[project_name]
       
       if use_config:
           # Fast path: use configured directories
           test_files = []
           for pattern in config["test_patterns"]:
               for test_dir in config["test_dirs"]:
                   test_files.extend(Path(config["root"]) / test_dir.glob(pattern))
       else:
           # Fallback: recursive discovery
           test_files = recursive_discover(config["root"], config["test_patterns"])
       
       return sorted(set(test_files))
   ```

### Phase 2: Language Executors (2-3 hours)

4. **`scripts/test_execution/python_executor.py`**
   ```python
   def run_python_tests(test_files: List[Path], env: dict, verbose: bool = True) -> int:
       """Execute pytest on test files."""
       cmd = ["python", "-m", "pytest"] + [str(f) for f in test_files]
       if verbose:
           cmd.append("-v")
       return subprocess.run(cmd, env=env).returncode
   ```

5. **`scripts/test_execution/shell_executor.py`**
   ```python
   def run_shell_tests(test_files: List[Path], env: dict) -> int:
       """Execute shell test scripts."""
       for test_file in test_files:
           os.chmod(test_file, 0o755)
           result = subprocess.run([str(test_file)], env=env)
           if result.returncode != 0:
               return result.returncode
       return 0
   ```

6. **`scripts/test_execution/compilation_checker.py`**
   ```python
   def check_compilation(project_name: str) -> bool:
       """Run compilation checks for a project."""
       config = PROJECTS[project_name]
       if config["type"] == "python":
           return check_python_compilation(config)
       elif config["type"] == "javascript":
           return check_js_compilation(config)
       return True
   ```

### Phase 3: Main Runner (1-2 hours)

7. **`scripts/test_runner.py`** - Main entry point
   ```python
   def main():
       parser = argparse.ArgumentParser()
       parser.add_argument("project", choices=["backend", "lambda", "gas", "all"])
       parser.add_argument("--skip-compilation", action="store_true")
       parser.add_argument("--recursive", action="store_true", help="Use recursive discovery instead of config")
       args = parser.parse_args()
       
       projects = [args.project] if args.project != "all" else PROJECTS.keys()
       
       for project in projects:
           env = setup_test_environment(project)
           if not args.skip_compilation:
               if not check_compilation(project):
                   print(f"❌ Compilation check failed for {project}")
                   return 1
           
           test_files = discover_tests(project, use_config=not args.recursive)
           if not test_files:
               print(f"⚠️  No tests found for {project}")
               continue
           
           executor = get_executor(PROJECTS[project]["type"])
           result = executor.run_tests(test_files, env)
           if result != 0:
               return result
       
       return 0
   ```

### Phase 4: Integration (1-2 hours)

8. **Update Makefile**
   ```makefile
   _test_backend_internal:
   	@python3 scripts/test_runner.py backend

   _test_lambda_internal:
   	@python3 scripts/test_runner.py lambda

   _test_gas_internal:
   	@python3 scripts/test_runner.py gas
   ```

9. **Update GitHub Workflows**
   ```yaml
   - name: Run Backend Tests
     run: |
       python3 scripts/test_runner.py backend
   ```

---

## Migration Strategy

### Step 1: Create Core Scripts (Non-Breaking)
- Add new scripts alongside existing logic
- Test in parallel with existing workflows

### Step 2: Update Makefile (Low Risk)
- Replace `_test_*_internal` targets
- Keep public `test` command unchanged

### Step 3: Update Workflows (Gradual)
- Update one workflow at a time
- Test each before moving to next

### Step 4: Remove Standalone Scripts (Final)
- Delete `backend/scripts/run_tests.sh`
- Delete `backend/scripts/run_consolidated_tests.py`
- Keep `lambda/functions/tests/run_tests.py` if it has unique logic

---

## Benefits

1. **Single Source of Truth** - All test logic in `scripts/`
2. **DRY Principle** - No duplicated logic between Makefile/workflows
3. **Maintainability** - Change test logic in one place
4. **Consistency** - Same test execution everywhere
5. **Extensibility** - Easy to add new projects/languages
6. **Performance** - Config-based discovery is fast
7. **Flexibility** - Recursive fallback for edge cases

---

## Estimated Time

- **Phase 1 (Core):** 2-3 hours
- **Phase 2 (Executors):** 2-3 hours
- **Phase 3 (Runner):** 1-2 hours
- **Phase 4 (Integration):** 1-2 hours
- **Testing & Refinement:** 1-2 hours

**Total: 7-12 hours**

---

## Next Steps

1. Review and approve proposal
2. Create `scripts/test_config.py` with project definitions
3. Implement core infrastructure
4. Migrate one project at a time (backend → lambda → gas)
5. Update Makefile and workflows incrementally
