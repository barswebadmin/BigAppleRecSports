"""
Simple configuration loader that loads .env and exposes all environment variables via dot notation.
All keys are normalized to lowercase.
Supports nested dot notation (e.g., google.service_account_file -> config.google.service_account_file).
"""
from dotenv import load_dotenv
import os
import json
from typing import Dict, Any, Optional
from pydantic import ConfigDict

from backend.shared.model_config import ApiModel


class Config(ApiModel):
    """
    Programmatic configuration that loads .env and exposes all environment variables
    via dot notation (e.g., config.shopify_token, config.google.service_account_file).
    
    All environment variable keys are normalized to lowercase.
    Environment variables with dots are organized into nested structures:
    - google.service_account_file -> config.google.service_account_file
    - SLACK.BOT_TOKEN_DEV -> config.slack.bot_token_dev
    """
    
    model_config = ConfigDict(extra='allow')
    
    def __init__(self, **data: Any):
        is_root = not data
        
        # Only load .env and build from env on root Config instance (not nested ones)
        if is_root:
            # Always load .env first with override=True so .env values take precedence
            # In production (Render/etc), env vars are injected directly, so .env won't exist.
            # load_dotenv() safely returns False if .env doesn't exist (no error raised).
            load_dotenv(override=True)
            
            # Build nested structure from environment variables
            env_data = self._build_from_env()
            env_data.update(data)
            data = env_data
        
        # Recursively convert nested dicts, but keep as dicts for Pydantic
        # We'll set Config instances after initialization
        def convert_dict(v: Any) -> Any:
            if isinstance(v, dict):
                return {k: convert_dict(val) for k, val in v.items()}
            return v
        
        processed_data = {k: convert_dict(v) for k, v in data.items()}
        super().__init__(**processed_data)
        
        # Recursively convert all nested dicts to Config instances after Pydantic initialization
        def set_nested_configs(obj: 'Config') -> None:
            for key, value in self._get_all_attrs(obj).items():
                if isinstance(value, dict) and not key.startswith('_'):
                    nested_config = obj.__class__(**value)
                    object.__setattr__(obj, key, nested_config)
                    set_nested_configs(nested_config)
        
        set_nested_configs(self)
        
        # Debug: Print final config object structure (only for root instance)
        if is_root:
            pass  # Debug logging removed
        def config_to_dict(obj: Any) -> Any:
            """Recursively convert Config objects to dicts for JSON serialization."""
            if isinstance(obj, Config):
                result = {}
                attrs = obj._get_all_attrs(obj)
                for key, value in attrs.items():
                    if not key.startswith('_'):
                        result[key] = config_to_dict(value)
                return result
            elif isinstance(obj, dict):
                return {k: config_to_dict(v) for k, v in obj.items()}
            elif isinstance(obj, (list, tuple)):
                return [config_to_dict(item) for item in obj]
            else:
                return obj
        
        def mask_sensitive_values(obj: Any) -> Any:
            """Mask sensitive values in the config dict."""
            if isinstance(obj, dict):
                masked = {}
                for key, value in obj.items():
                    if isinstance(value, str) and len(value) > 14:
                        masked[key] = value[:10] + "..." + value[-4:]
                    elif isinstance(value, (dict, list)):
                        masked[key] = mask_sensitive_values(value)
                    else:
                        masked[key] = value
                return masked
            elif isinstance(obj, list):
                return [mask_sensitive_values(item) for item in obj]
            else:
                return obj
        
            try:
                config_dict = config_to_dict(self)
                masked_dict = mask_sensitive_values(config_dict)
                print(json.dumps(masked_dict, indent=2, default=str))
            except Exception as e:
                print(f"ERROR serializing config: {e}")
                import traceback
                traceback.print_exc()
            print("="*80 + "\n")
    
    @staticmethod
    def _get_all_attrs(obj: 'Config') -> Dict[str, Any]:
        """Get all attributes from __dict__ and Pydantic extra fields."""
        attrs = dict(obj.__dict__)
        if hasattr(obj, '__pydantic_extra__') and obj.__pydantic_extra__:
            attrs.update(obj.__pydantic_extra__)
        if hasattr(obj, 'model_extra') and obj.model_extra:
            attrs.update(obj.model_extra)
        return attrs
    
    @staticmethod
    def _normalize_key(part: str) -> str:
        """Normalize key part to lowercase snake_case."""
        return part.replace("-", "_").lower()
    
    @classmethod
    def _build_from_env(cls) -> Dict[str, Any]:
        """Build nested dict structure from environment variables with dot notation."""
        nested: Dict[str, Any] = {}
        flat: Dict[str, str] = {}
        
        # Sort all environment variables alphabetically to ensure consistent processing order
        # This ensures GOOGLE.SERVICE_ACCOUNT is processed before GOOGLE.SERVICE_ACCOUNT.SUBJECT
        sorted_env_items = sorted(os.environ.items())
        
        for key, value in sorted_env_items:
            if "." in key:
                # Build nested structure
                parts = [cls._normalize_key(p) for p in key.split(".") if p]
                if len(parts) >= 2:
                    cur = nested
                    for seg in parts[:-1]:
                        # Ensure we have a dict at this level
                        if seg not in cur:
                            cur[seg] = {}
                        elif not isinstance(cur[seg], dict):
                            # If we encounter a string that looks like JSON, try to parse it
                            if isinstance(cur[seg], str):
                                try:
                                    parsed_json = json.loads(cur[seg])
                                    if isinstance(parsed_json, dict):
                                        cur[seg] = parsed_json
                                    else:
                                        # Not a dict, can't navigate further, skip this nested path
                                        break
                                except (json.JSONDecodeError, TypeError):
                                    # Not valid JSON, can't navigate further, skip this nested path
                                    break
                            else:
                                # Not a dict or string, can't navigate further, skip this nested path
                                break
                        cur = cur[seg]
                    else:
                        # Only set if we successfully navigated the path
                        final_key = parts[-1]
                        # Try to parse as JSON if it looks like JSON
                        try:
                            parsed_json = json.loads(value)
                            if isinstance(parsed_json, dict):
                                cur[final_key] = parsed_json
                            else:
                                cur[final_key] = value
                        except (json.JSONDecodeError, TypeError):
                            cur[final_key] = value
            else:
                # Store flat variables
                flat[cls._normalize_key(key)] = value
        
        # Merge flat variables (flat takes precedence if conflict)
        nested.update(flat)
        return nested
    
    def __getattr__(self, name: str) -> Any:
        """Fallback getter with lowercase enforcement."""
        if name.startswith('_'):
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'")
        
        # Reject uppercase access
        if name != name.lower():
            raise AttributeError(f"'{type(self).__name__}' object has no attribute '{name}'. Use lowercase: '{name.lower()}'")
        
        # Try Pydantic's attribute access (handles model_extra/__pydantic_extra__)
        try:
            return super().__getattribute__(name)
        except AttributeError:
            pass
        
        # Check Pydantic's extra fields directly
        attrs = self._get_all_attrs(self)
        if name in attrs:
            return attrs[name]
        
        # Try lazy loading from environment
        env_prefix = name + "."
        matching = {k: v for k, v in os.environ.items() if k.lower().startswith(env_prefix)}
        if matching:
            nested_data = self._build_from_env()
            if name in nested_data:
                nested_config = self.__class__(**nested_data[name]) if isinstance(nested_data[name], dict) else nested_data[name]
                object.__setattr__(self, name, nested_config)
                return nested_config
        
        # Try single env var
        value = os.getenv(name)
        if value is not None:
            object.__setattr__(self, name, value)
            return value
        
        return None
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """Get config value by dot-notation key."""
        if "." not in key:
            return getattr(self, self._normalize_key(key), default) or os.getenv(key, default)
        
        parts = [self._normalize_key(p) for p in key.split(".") if p]
        cur: Any = self
        for seg in parts:
            if not hasattr(cur, seg):
                return os.getenv(key, default)
            cur = getattr(cur, seg)
        return cur if isinstance(cur, str) else os.getenv(key, default)
    


# Create global singleton instance
# This is the single source of truth for configuration
# Accessible via: from config import config
config = Config()

# Make it available as a module-level export
__all__ = ["Config", "config"]
