# Workflow Reorganization Plan

## Current State

### Test Workflows (When They Run)

1. **`backend-tests.yml`**
   - **Triggers**: PR/push to `main` when `backend/**` changes
   - **Current Logic**: Inline pytest commands with hardcoded test paths
   - **Status**: `continue-on-error: true` (advisory only)

2. **`compilation-check.yml`**
   - **Triggers**: PR/push to `main` (all changes)
   - **Jobs**: 
     - `compilation-check` (compiles all sub-repos)
     - `backend-tests` (runs if backend compiled)
     - `gas-tests` (runs if GAS compiled)
     - `lambda-tests` (runs if Lambda compiled)
   - **Current Logic**: Inline test commands for each sub-repo
   - **Note**: Uses `pull_request_target` for PRs

3. **`google-apps-scripts-tests.yml`**
   - **Triggers**: Push to `main` when `GoogleAppsScripts/**` changes
   - **Current Logic**: Inline shell script execution
   - **Manual**: `workflow_dispatch` available

4. **`lambda-test.yml`**
   - **Triggers**: Push to `main` when `lambda-functions/**` changes
   - **Current Logic**: Calls `lambda/functions/tests/run_tests.py unit`
   - **Note**: Uses old `lambda-functions/` path

### Deploy Workflows (When They Run)

1. **`deploy-backend.yml`**
   - **Triggers**: Push to `main` when `backend/**` changes
   - **Current Logic**: 
     - Syncs secrets from SSM to Render
     - Triggers Render deployment via GitHub Action
   - **Manual**: `workflow_dispatch` available

2. **`deploy-aws.yml`**
   - **Triggers**: Push to `main` when `lambda/functions/**` changes
   - **Current Logic**: 
     - Detects changed Lambda functions
     - Deploys using unified `deploy_aws.sh` script
   - **Manual**: `workflow_dispatch` available with function selection

4. **GAS Deployment**
   - **No workflow exists** - deployment is manual via Makefile:
     - `make clasp push <project>`
     - `make clasp deploy <project>`
   - **Scripts**: `GoogleAppsScripts/remote-sync-tools/deploy.sh`

## Proposed Changes

### New Test Workflows (3 total)

1. **`.github/workflows/test-backend.yml`**
   - **Triggers**: PR/push to `main` when `backend/**` changes
   - **Logic**: `python scripts/testing/run_tests.py backend`
   - **Replaces**: `backend-tests.yml`, backend test jobs in `compilation-check.yml`

2. **`.github/workflows/test-lambda.yml`**
   - **Triggers**: PR/push to `main` when `lambda/functions/**` changes
   - **Logic**: `python scripts/testing/run_tests.py lambda`
   - **Replaces**: `lambda-test.yml`, lambda test jobs in `compilation-check.yml`

3. **`.github/workflows/test-gas.yml`**
   - **Triggers**: PR/push to `main` when `GoogleAppsScripts/**` changes
   - **Logic**: `python scripts/testing/run_tests.py gas`
   - **Replaces**: `google-apps-scripts-tests.yml`, GAS test jobs in `compilation-check.yml`

### New Deploy Workflows (3 total)

1. **`.github/workflows/deploy-backend.yml`**
   - **Triggers**: Push to `main` when `backend/**` changes
   - **Logic**: 
     - Sync secrets: `python scripts/secrets/sync_render_secrets.py --from-ssm`
     - Deploy: GitHub Action `johnbeynon/render-deploy-action`
   - **Current**: Already implemented

2. **`.github/workflows/deploy-aws.yml`**
   - **Triggers**: Push to `main` when `lambda/functions/**` changes
   - **Logic**: 
     - Run tests: `python scripts/testing/run_tests.py lambda`
     - Deploy: `bash scripts/deployment/deploy_lambda_function.sh <function>`
   - **Current**: Already implemented as `deploy-aws.yml`

3. **`.github/workflows/deploy-gas.yml`**
   - **Triggers**: Push to `main` when `GoogleAppsScripts/**` changes (optional, or manual only)
   - **Logic**: 
     - Run tests: `python scripts/testing/run_tests.py gas`
     - Deploy: `bash GoogleAppsScripts/remote-sync-tools/deploy.sh <project>`
   - **New**: First automated GAS deployment workflow

### Required Script Updates

1. **`scripts/testing/run_tests.py`** ✅ Already created
   - Supports: `backend`, `lambda`, `gas`, `all`
   - Supports: `--type unit|integration` filter

2. **`scripts/deployment/deploy_to_render.sh`** ✅ Already exists
   - Needs: Ensure it works from workflow context
   - Already supports: `--from-ssm` flag

3. **`scripts/deployment/deploy_lambda_function.sh`** ✅ Already exists
   - Needs: Update to handle multiple functions or detect changed functions
   - Currently: Single function only

4. **`scripts/deployment/deploy_gas.sh`** ⚠️ Needs creation
   - Wrapper around `GoogleAppsScripts/remote-sync-tools/deploy.sh`
   - Should detect changed GAS projects
   - Or accept project name as argument

## Migration Steps

1. **Create new test workflows** (3 files)
   - Use centralized `scripts/testing/run_tests.py`
   - Set appropriate triggers and paths

2. **Create new deploy workflows** (3 files)
   - Use centralized test script
   - Use centralized deploy scripts
   - Set appropriate triggers and paths

3. **Update/consolidate deployment scripts**
   - Ensure `deploy_lambda_function.sh` can handle batch deployments
   - Create `deploy_gas.sh` wrapper script

4. **Deprecate old workflows**
   - Mark old workflows as deprecated
   - Or delete after confirming new ones work

5. **Update `compilation-check.yml`**
   - Remove test jobs (tests now in dedicated workflows)
   - Keep only compilation checks
   - Or remove entirely if compilation is checked in test workflows

## Benefits

- **DRY**: Single source of truth for test execution
- **Consistency**: Same test logic for CI and manual runs
- **Maintainability**: Update test logic in one place
- **Clarity**: One workflow per sub-repo, clear responsibilities
- **Extensibility**: Easy to add new test types or sub-repos
