"""
Re-export config singleton from backend/config.py for global access.
"""
import sys
from pathlib import Path

# Import from parent config.py
_backend_dir = Path(__file__).parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Import config.py module and re-export the singleton
import config as _config_module
config = getattr(_config_module, 'config')  # type: ignore
Config = getattr(_config_module, 'Config')  # type: ignore

__all__ = ["config", "Config"]
