"""
Auto-export utility for dynamic module discovery and export.
Use in __init__.py files to automatically export all public functions/classes.
"""
import importlib
import pkgutil
from typing import List, Dict, Any, Sequence


def auto_export_module(module_path: Sequence[str], module_globals: Dict[str, Any]) -> List[str]:
    """
    Auto-discover and export all public functions/classes from a module.
    
    Args:
        module_path: __path__ from the calling module
        module_globals: globals() from the calling module
        
    Returns:
        List of exported symbol names for __all__
    """
    exports: List[str] = []
    
    for importer, modname, ispkg in pkgutil.iter_modules(module_path):
        if not ispkg and not modname.startswith('_'):
            module = importlib.import_module(f'.{modname}', module_globals['__name__'])
            
            # Export all public attributes (functions and classes only)
            for attr_name in dir(module):
                if not attr_name.startswith('_'):
                    attr = getattr(module, attr_name)
                    # Only export functions and classes, not modules or other objects
                    if (callable(attr) or isinstance(attr, type)) and not hasattr(attr, '__file__'):
                        # Avoid overwriting if module name conflicts with function name
                        if attr_name not in module_globals or not hasattr(module_globals[attr_name], '__file__'):
                            module_globals[attr_name] = attr
                            if attr_name not in exports:
                                exports.append(attr_name)
    
    return exports
