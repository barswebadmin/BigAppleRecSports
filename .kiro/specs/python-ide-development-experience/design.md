# Python IDE Development Experience - Design Document

## Architecture Overview

The enhanced Python development experience will be built on a foundation of properly configured language servers, semantic highlighting, and real-time error detection. The solution addresses the core issues of import validation, visual feedback, and IDE reliability.

## Core Components

### 1. Language Server Configuration
**Primary**: Pyright (Microsoft's Python language server)
**Fallback**: Python LSP Server (community-driven alternative)

#### Pyright Configuration Strategy
```json
{
  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.diagnosticMode": "workspace",
  "python.analysis.autoImportCompletions": true,
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "error",
    "reportImportCycles": "error", 
    "reportUnusedImport": "warning",
    "reportUndefinedVariable": "error",
    "reportUnknownMemberType": "warning",
    "reportUnknownVariableType": "warning"
  }
}
```

#### Multi-Environment Support
The project has distinct execution environments:
- **Backend**: Uses `backend/.venv` with FastAPI, SQLAlchemy, etc.
- **CLI**: Uses pipx venv with Click, Rich, etc.
- **Lambda**: Uses layer-specific dependencies
- **Scripts**: Uses pipx venv with automation tools

### 2. Import Resolution System

#### Path Configuration
```json
{
  "python.analysis.extraPaths": [
    "backend",
    "bars_cli", 
    "lambda-layers/bars-common-utils/python",
    "shared-utilities/src"
  ],
  "terminal.integrated.env.osx": {
    "PYTHONPATH": "${workspaceFolder}/backend:${workspaceFolder}/lambda-layers/bars-common-utils/python:${workspaceFolder}/shared-utilities/src:${env:PYTHONPATH}"
  }
}
```

#### Real-time Import Validation
- **Invalid Import Detection**: Configure Pyright to immediately flag non-existent modules
- **Unused Import Detection**: Separate visual treatment for imports that exist but aren't used
- **Circular Import Detection**: Real-time detection of import cycles
- **Relative Import Support**: Proper handling of relative imports within project modules

### 3. Visual Feedback System

#### Semantic Highlighting Configuration
```json
{
  "editor.semanticHighlighting.enabled": true,
  "editor.semanticTokenColorCustomizations": {
    "rules": {
      "class": "#4EC9B0",
      "class.declaration": "#4EC9B0",
      "method": "#DCDCAA", 
      "method.declaration": "#DCDCAA",
      "function": "#DCDCAA",
      "function.declaration": "#DCDCAA",
      "module": "#9CDCFE",
      "variable.readonly": "#4FC1FF",
      "parameter": "#9CDCFE"
    }
  }
}
```

#### Error/Warning Visual Treatment
- **Import Errors**: Red squiggly underlines with "Module not found" tooltip
- **Unused Imports**: Gray/dimmed text with "Unused import" tooltip  
- **Type Errors**: Red squiggly underlines with type mismatch details
- **Syntax Errors**: Red squiggly underlines with syntax issue description
- **Warnings**: Yellow/orange underlines for non-critical issues

### 4. Diagnostic Configuration

#### Error Categorization
```python
# Error Types and Visual Treatment
ERROR_TYPES = {
    "reportMissingImports": {
        "severity": "error",
        "color": "red",
        "style": "squiggly",
        "message": "Module '{module}' not found"
    },
    "reportUnusedImport": {
        "severity": "warning", 
        "color": "gray",
        "style": "fade",
        "message": "Import '{import}' is unused"
    },
    "reportUndefinedVariable": {
        "severity": "error",
        "color": "red", 
        "style": "squiggly",
        "message": "Variable '{variable}' is not defined"
    }
}
```

#### Real-time Diagnostic Updates
- **Immediate Feedback**: Diagnostics update as user types
- **Debounced Updates**: Prevent excessive diagnostic runs during rapid typing
- **Incremental Analysis**: Only re-analyze changed files and dependencies
- **Background Processing**: Non-blocking diagnostic computation

## Implementation Details

### 1. Language Server Setup

#### Pyright Installation and Configuration
```bash
# Install Pyright globally or in project
npm install -g pyright
# OR
pip install pyright
```

#### Configuration Files
- **pyproject.toml**: Primary Pyright configuration
- **.vscode/settings.json**: IDE-specific overrides
- **pyrightconfig.json**: Project-specific settings (if needed)

#### Execution Environment Mapping
```toml
[tool.pyright.executionEnvironments]
backend = { 
    root = "backend", 
    pythonVersion = "3.14",
    extraPaths = ["modules", "shared", "config"]
}
bars_cli = { 
    root = "bars_cli", 
    pythonVersion = "3.14",
    extraPaths = ["commands", "_core"]
}
lambda = { 
    root = "lambda", 
    pythonVersion = "3.14",
    extraPaths = ["../lambda-layers/bars-common-utils/python"]
}
```

### 2. Import Resolution Enhancement

#### Module Discovery
- **Automatic Path Detection**: Scan project for Python packages
- **Virtual Environment Integration**: Detect and use appropriate venv
- **Dependency Resolution**: Map imports to installed packages
- **Relative Import Handling**: Resolve relative imports within project structure

#### Error Detection Logic
```python
def validate_import(import_statement):
    """Validate import and return appropriate diagnostic"""
    module_path = resolve_module_path(import_statement)
    
    if not module_path:
        return Diagnostic(
            severity=DiagnosticSeverity.ERROR,
            message=f"Module '{import_statement}' not found",
            code="reportMissingImports"
        )
    
    if not is_import_used(import_statement):
        return Diagnostic(
            severity=DiagnosticSeverity.WARNING,
            message=f"Import '{import_statement}' is unused", 
            code="reportUnusedImport"
        )
    
    return None  # Valid import
```

### 3. Visual Enhancement Implementation

#### Semantic Token Provider
```typescript
// Semantic highlighting for Python constructs
const PYTHON_SEMANTIC_TOKENS = {
    'class': { color: '#4EC9B0', fontStyle: 'bold' },
    'method': { color: '#DCDCAA', fontStyle: 'italic' },
    'function': { color: '#DCDCAA' },
    'module': { color: '#9CDCFE' },
    'variable': { color: '#9CDCFE' },
    'parameter': { color: '#9CDCFE', fontStyle: 'italic' }
};
```

#### Error Decoration Provider
```typescript
// Visual treatment for different error types
const ERROR_DECORATIONS = {
    'import-error': {
        backgroundColor: 'rgba(255, 0, 0, 0.1)',
        border: '1px solid red',
        borderRadius: '2px'
    },
    'unused-import': {
        opacity: '0.5',
        textDecoration: 'line-through'
    },
    'type-error': {
        backgroundColor: 'rgba(255, 165, 0, 0.1)',
        border: '1px solid orange'
    }
};
```

### 4. Performance Optimization

#### Incremental Analysis
- **File Change Detection**: Only re-analyze modified files
- **Dependency Tracking**: Update dependents when imports change
- **Caching Strategy**: Cache analysis results for unchanged files
- **Background Processing**: Perform heavy analysis in background threads

#### Memory Management
- **Selective Loading**: Load only necessary modules into memory
- **Garbage Collection**: Clean up unused analysis data
- **Resource Limits**: Set appropriate memory and CPU limits
- **Lazy Evaluation**: Defer expensive operations until needed

## Configuration Files

### .vscode/settings.json
```json
{
  "python.defaultInterpreterPath": "/Users/jrandazzo/.local/pipx/venvs/bars/bin/python",
  "python.analysis.typeCheckingMode": "strict",
  "python.analysis.diagnosticMode": "workspace", 
  "python.analysis.autoImportCompletions": true,
  "python.analysis.extraPaths": [
    "backend",
    "bars_cli",
    "lambda-layers/bars-common-utils/python", 
    "shared-utilities/src"
  ],
  "python.analysis.diagnosticSeverityOverrides": {
    "reportMissingImports": "error",
    "reportImportCycles": "error",
    "reportUnusedImport": "warning", 
    "reportUndefinedVariable": "error",
    "reportUnknownMemberType": "warning"
  },
  "editor.semanticHighlighting.enabled": true,
  "editor.semanticTokenColorCustomizations": {
    "rules": {
      "class": "#4EC9B0",
      "method": "#DCDCAA",
      "function": "#DCDCAA", 
      "module": "#9CDCFE",
      "variable": "#9CDCFE"
    }
  },
  "terminal.integrated.env.osx": {
    "PYTHONPATH": "${workspaceFolder}/backend:${workspaceFolder}/lambda-layers/bars-common-utils/python:${workspaceFolder}/shared-utilities/src:${env:PYTHONPATH}"
  }
}
```

### pyproject.toml (Enhanced)
```toml
[tool.pyright]
typeCheckingMode = "strict"
reportMissingImports = true
reportImportCycles = true
reportUnusedImport = true
reportUndefinedVariable = true
pythonVersion = "3.14"
pythonPlatform = "All"
include = ["**/*.py"]
exclude = ["**/__pycache__", "**/.venv", "**/node_modules"]

[tool.pyright.executionEnvironments]
backend = { 
    root = "backend", 
    pythonVersion = "3.14",
    extraPaths = ["modules", "shared", "config", "routers", "services"]
}
bars_cli = { 
    root = "bars_cli", 
    pythonVersion = "3.14",
    extraPaths = ["commands", "_core", "backend_services"]
}
lambda = { 
    root = "lambda", 
    pythonVersion = "3.14",
    extraPaths = ["../lambda-layers/bars-common-utils/python"]
}

[tool.pyright.diagnosticSeverityOverrides]
reportMissingImports = "error"
reportImportCycles = "error" 
reportUnusedImport = "warning"
reportUndefinedVariable = "error"
reportUnknownMemberType = "warning"
reportUnknownVariableType = "information"
```

## Testing Strategy

### Unit Tests for Configuration
- Test import resolution for all project modules
- Verify error detection accuracy
- Test visual feedback rendering
- Validate performance under load

### Integration Tests
- Test language server startup and stability
- Verify cross-module import resolution
- Test real-time diagnostic updates
- Validate IDE feature functionality

### User Acceptance Tests
- Test developer workflow scenarios
- Verify error detection timing
- Test visual feedback clarity
- Validate overall development experience

## Rollout Plan

### Phase 1: Foundation (Week 1)
- Configure Pyright with basic settings
- Set up proper execution environments
- Test basic import resolution
- Verify language server stability

### Phase 2: Enhancement (Week 2)  
- Implement real-time import validation
- Configure semantic highlighting
- Set up visual error treatments
- Test with complex import scenarios

### Phase 3: Optimization (Week 3)
- Optimize performance for large codebase
- Fine-tune diagnostic settings
- Implement advanced error detection
- Test under realistic development conditions

### Phase 4: Validation (Week 4)
- Conduct user acceptance testing
- Gather developer feedback
- Make final adjustments
- Document configuration and usage

## Success Criteria

### Functional Requirements
- ✅ Invalid imports show as errors within 1 second
- ✅ Unused imports show as warnings with distinct visual treatment
- ✅ Language server starts reliably and remains stable
- ✅ All project modules resolve correctly for imports
- ✅ Semantic highlighting works for all Python constructs

### Performance Requirements  
- ✅ Import error detection < 1 second
- ✅ Autocomplete response < 500ms
- ✅ Language server memory usage < 500MB
- ✅ Diagnostic updates don't block typing

### User Experience Requirements
- ✅ Clear visual distinction between error types
- ✅ Helpful error messages with actionable information
- ✅ Consistent IDE behavior across all project files
- ✅ Reliable go-to-definition and find-references functionality