"""Circular import detection using multiple strategies."""

import importlib
import re
import sys
import threading
import traceback
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

from scripts.compilation_helpers.repo_path_resolvers import get_relative_path, path_to_module
from scripts.compilation_helpers.checkers._checkers_common import create_error, ensure_src_in_path


_cycle_index_cache: Optional[Dict[str, List[List[str]]]] = None


def _format_cycle_path(cycle: List[str]) -> str:
    """Format a cycle list into a readable path string."""
    return " → ".join(cycle) + f" → {cycle[0]}"


def _add_debug_message(debug_messages: Optional[List[str]], debug_lock: Optional[threading.Lock], message: str) -> None:
    """Add debug message in a thread-safe way."""
    if debug_messages is None:
        return
    
    if debug_lock:
        with debug_lock:
            debug_messages.append(message)
    else:
        debug_messages.append(message)


def _get_cycle_index(repo_root: Path) -> Dict[str, List[List[str]]]:
    """Build or retrieve the cycle index mapping modules to their cycles."""
    global _cycle_index_cache
    if _cycle_index_cache is not None:
        return _cycle_index_cache
    
    _cycle_index_cache = {}
    try:
        from circular_import_detector import CircularImportDetector  # type: ignore[import-untyped]
        detector = CircularImportDetector(str(repo_root))
        has_cycles, cycles = detector.detect_circular_imports()
        if has_cycles:
            for cycle in cycles:
                for module_name in cycle:
                    if module_name not in _cycle_index_cache:
                        _cycle_index_cache[module_name] = []
                    _cycle_index_cache[module_name].append(cycle)
    except Exception:
        pass
    
    return _cycle_index_cache


def _find_unreported_cycles(cache: Dict[str, List[List[str]]], module_name: str, found_cycles: Set[Tuple[str, ...]]) -> List[List[str]]:
    """Find cycles for a module that haven't been reported yet."""
    if module_name not in cache:
        return []
    
    return [cycle for cycle in cache[module_name] if tuple(cycle) not in found_cycles]


def _extract_modules_from_error(error_message: str) -> Set[str]:
    """Extract module names mentioned in an ImportError message."""
    patterns = [
        r"from partially initialized module '([^']+)'",
        r"from module '([^']+)'",
        r"import name '[^']+' from [^']+ '([^']+)'",
    ]
    
    mentioned_modules = set()
    for pattern in patterns:
        mentioned_modules.update(re.findall(pattern, error_message))
    
    return mentioned_modules


def _get_parent_modules(module_name: str) -> List[str]:
    """Get all parent modules (from most specific to least specific)."""
    parts = module_name.split('.')
    return ['.'.join(parts[:i]) for i in range(len(parts), 0, -1)]


def _try_find_cycles_in_index(cache: Dict[str, List[List[str]]], module_name: str, found_cycles: Set[Tuple[str, ...]]) -> List[List[str]]:
    """Try to find cycles using index lookup strategies."""
    # Strategy 1: Direct lookup
    cycles = _find_unreported_cycles(cache, module_name, found_cycles)
    if cycles:
        return cycles
    
    # Strategy 2: Try parent modules
    for parent_module in _get_parent_modules(module_name):
        cycles = _find_unreported_cycles(cache, parent_module, found_cycles)
        if cycles:
            return cycles
    
    return []


def _add_cycle_errors(import_errors: List[dict], cycles: List[List[str]], rel_path: str, found_cycles: Set[Tuple[str, ...]]) -> None:
    """Add cycle errors to the import_errors list."""
    for cycle in cycles:
        found_cycles.add(tuple(cycle))
        import_errors.append(create_error(rel_path, "CIRCULAR", "Circular import detected", import_path=_format_cycle_path(cycle)))


def _find_cycle_path_from_index(repo_root: Path, module_name: str, rel_path: str, error_message: Optional[str], debug_messages: Optional[List[str]], debug_lock: Optional[threading.Lock]) -> List[dict]:
    """Find cycle path using index lookup strategies."""
    cache = _get_cycle_index(repo_root)
    import_errors = []
    found_cycles = set()
    
    # Try direct lookup first
    cycles = _try_find_cycles_in_index(cache, module_name, found_cycles)
    if cycles:
        _add_debug_message(debug_messages, debug_lock, "[blue]Using circular import check path: index direct lookup[/blue]")
        _add_cycle_errors(import_errors, cycles, rel_path, found_cycles)
        return import_errors
    
    # Try extracting from error message
    if error_message:
        mentioned_modules = _extract_modules_from_error(error_message)
        for mentioned_module in mentioned_modules:
            cycles = _try_find_cycles_in_index(cache, mentioned_module, found_cycles)
            if cycles:
                _add_debug_message(debug_messages, debug_lock, "[blue]Using circular import check path: index error message extraction[/blue]")
                _add_cycle_errors(import_errors, cycles, rel_path, found_cycles)
                return import_errors
    
    return import_errors


def _extract_modules_from_traceback(tb: List[traceback.FrameSummary], src_root: Path) -> List[str]:
    """Extract module names from traceback frames."""
    modules = []
    seen = set()
    
    for frame in tb:
        frame_path = Path(frame.filename)
        if src_root not in frame_path.parents and frame_path.parent != src_root:
            continue
        
        try:
            frame_module = path_to_module(frame_path, src_root)
            if frame_module and frame_module not in seen:
                modules.append(frame_module)
                seen.add(frame_module)
        except Exception:
            pass
    
    return modules


def _build_cycle_from_modules(modules: List[str]) -> Optional[str]:
    """Build a cycle path from a list of modules."""
    if len(modules) < 2:
        return None
    
    # Check if first module appears again (indicating a cycle)
    if modules[0] in modules[1:]:
        cycle_start_idx = modules[1:].index(modules[0]) + 1
        cycle = modules[:cycle_start_idx + 1]
        return _format_cycle_path(cycle)
    
    # No clear cycle, but show path with loop-back
    return _format_cycle_path(modules)


def _extract_cycle_from_traceback(exception: Exception, module_name: str, src_root: Path) -> Optional[str]:
    """Extract circular import cycle path from exception traceback."""
    try:
        tb = traceback.extract_tb(exception.__traceback__)
        if not tb:
            return None
        
        modules = _extract_modules_from_traceback(tb, src_root)
        if module_name and module_name not in modules:
            modules.append(module_name)
        
        return _build_cycle_from_modules(modules)
    except Exception:
        return None


def _cleanup_partial_module(module_name: str) -> None:
    """Remove partially initialized module from sys.modules."""
    if module_name not in sys.modules:
        return
    
    try:
        mod = sys.modules[module_name]
        if hasattr(mod, '__name__') and not hasattr(mod, '__file__'):
            del sys.modules[module_name]
    except (KeyError, AttributeError):
        pass


def _is_circular_import_error(error_msg: str) -> bool:
    """Check if error message indicates a circular import."""
    error_lower = error_msg.lower()
    return "circular import" in error_lower or "partially initialized" in error_lower


def _handle_circular_import(exception: ImportError, module_name: str, rel_path: str, src_root: Path, debug_messages: Optional[List[str]], debug_lock: Optional[threading.Lock]) -> List[dict]:
    """Handle a circular import error by finding the cycle path."""
    repo_root = src_root.parent
    error_msg = str(exception)
    import_errors = []
    
    # Try index lookup strategies
    try:
        import_errors = _find_cycle_path_from_index(repo_root, module_name, rel_path, error_msg, debug_messages, debug_lock)
    except Exception:
        pass
    
    # Fallback to traceback extraction
    if not import_errors:
        try:
            cycle_path = _extract_cycle_from_traceback(exception, module_name, src_root)
            if cycle_path:
                _add_debug_message(debug_messages, debug_lock, "[blue]Using circular import check path: traceback extraction[/blue]")
                import_errors.append(create_error(rel_path, "CIRCULAR", f"Circular import detected: {error_msg}", import_path=cycle_path))
            else:
                _add_debug_message(debug_messages, debug_lock, "[blue]Using circular import check path: module name fallback[/blue]")
                import_errors.append(create_error(rel_path, "CIRCULAR", f"Circular import detected: {error_msg}", import_path=module_name))
        except Exception:
            import_errors.append(create_error(rel_path, "CIRCULAR", f"Circular import detected: {error_msg}", import_path=module_name))
    
    return import_errors


def check_circular_imports(file_path: Path, src_root: Path, debug_messages: Optional[List[str]] = None, debug_lock: Optional[threading.Lock] = None) -> Tuple[bool, List[dict]]:
    """Check for import errors (circular imports and missing modules) by attempting to import the module."""
    rel_path = get_relative_path(file_path, src_root)
    
    try:
        module_name = path_to_module(file_path, src_root)
        if not module_name:
            return True, []

        ensure_src_in_path(src_root)
        _cleanup_partial_module(module_name)
        
        try:
            importlib.import_module(module_name)
            return True, []
        except ImportError as e:
            error_msg = str(e)
            
            if _is_circular_import_error(error_msg):
                import_errors = _handle_circular_import(e, module_name, rel_path, src_root, debug_messages, debug_lock)
                return len(import_errors) == 0, import_errors
            
            # Not circular, but still an import error
            return False, [create_error(rel_path, "IMPORT", error_msg, import_path=module_name)]
        except Exception:
            return True, []
    except Exception:
        return True, []
