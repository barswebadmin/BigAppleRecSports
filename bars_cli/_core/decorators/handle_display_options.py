"""Decorator for handling display and exit options in CLI commands."""

import json
import sys
from functools import wraps
from typing import Callable, Any, Optional

import click


def handle_display_options(
    display: bool = True,
    exit_on_error: bool = True
):
    """
    Decorator to handle display and exit logic for CLI commands.
    
    Applied to commands to control whether they display output and exit on errors.
    Can be overridden per invocation by setting ctx.display_override and ctx.exit_override.
    
    Args:
        display: Whether to display output (default: True)
        exit_on_error: Whether to exit on error (default: True)
    
    The decorated function should return the result. Display and exit are handled by the decorator.
    Commands should handle their own formatting - the decorator only controls when to display/exit.
    
    Example:
        @click.command('get')
        @handle_display_options(display=True, exit_on_error=True)
        @click.pass_context
        def get_cmd(ctx, ...):
            # ... logic ...
            if not user:
                return None  # Decorator will handle display/exit
            click.echo(format_user(user))  # Command handles formatting
            return user  # Return result for programmatic use
    """
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Find context in args or kwargs
            # Click passes context as the first argument when @click.pass_context is used
            ctx = None
            for arg in args:
                if isinstance(arg, click.Context):
                    ctx = arg
                    break
            if not ctx:
                ctx = kwargs.get('ctx')
            if not ctx:
                # Try to get from click's current context
                try:
                    ctx = click.get_current_context(silent=True)
                except RuntimeError:
                    pass
            
            # Get display/exit overrides from context.obj if set
            # Using ctx.obj instead of ctx.meta because:
            # - ctx.meta is shared across ALL contexts (risky for per-command overrides)
            # - ctx.obj is per-context, with child contexts inheriting from parent
            # - This allows update() to set overrides that get() sees via inheritance
            #   without affecting update's own context
            
            def find_in_context_tree(ctx: Optional[click.Context], key: str) -> Optional[Any]:
                """Recursively walk up the context tree to find a value."""
                current = ctx
                while current:
                    if current.obj and key in current.obj:
                        return current.obj[key]
                    current = current.parent
                return None
            
            if ctx:
                ctx.ensure_object(dict)
                # First check for explicit overrides in current context
                override_display = ctx.obj.get('display_override', None)
                override_exit = ctx.obj.get('exit_override', None)
                
                # If not set, recursively walk up the tree to find defaults
                if override_display is None:
                    override_display = find_in_context_tree(ctx.parent, 'display_override')
                if override_exit is None:
                    override_exit = find_in_context_tree(ctx.parent, 'exit_override')
                
                # Store decorator's default parameters in ctx.obj for child contexts to inherit
                # Only set if not already present (don't override explicit values)
                if 'display_override' not in ctx.obj:
                    ctx.obj['display_override'] = display
                if 'exit_override' not in ctx.obj:
                    ctx.obj['exit_override'] = exit_on_error
            else:
                override_display = None
                override_exit = None
            
            # Use override if found, otherwise use decorator's default parameter
            should_display = override_display if override_display is not None else display
            should_exit = override_exit if override_exit is not None else exit_on_error
            
            # json_output is application config, stays in ctx.obj
            json_output = ctx.obj.get('json_output', False) if ctx and ctx.obj else False
            
            try:
                result = func(*args, **kwargs)
                
                # Skip display/exit logic for groups (they delegate to subcommands)
                # Groups are identified by checking if ctx.command is a Group
                is_group = ctx and hasattr(ctx, 'command') and isinstance(ctx.command, click.Group)
                
                # If result is None and we should exit, exit with error (but not for groups)
                if result is None and should_exit and not is_group:
                    if should_display:
                        # Try to get command name from multiple sources
                        command_name = "unknown"
                        if ctx:
                            if hasattr(ctx, 'command') and ctx.command:
                                command_name = getattr(ctx.command, 'name', 'unknown')
                            elif hasattr(ctx, 'info_name') and ctx.info_name:
                                command_name = ctx.info_name
                            elif hasattr(ctx, 'command_path') and ctx.command_path:
                                command_name = ctx.command_path
                        if json_output:
                            click.echo(json.dumps({"error": "Command failed: No result returned", "command": command_name}, indent=2))
                        else:
                            click.echo(f"❌ Command '{command_name}' failed: No result returned", err=True)
                            click.echo("💡 This usually means:", err=True)
                            click.echo("   - The command returned None instead of raising an exception", err=True)
                            click.echo("   - An error condition was not properly handled", err=True)
                            click.echo("   - Check the command logic for missing error handling", err=True)
                    if should_exit:
                        sys.exit(1)
                
                # Respect exit_override for successful returns too
                # If exit_override=False, don't exit even on success (return normally)
                # If exit_override=True (default), Click will handle normal exit after return
                # We only prevent exit here if explicitly set to False
                return result
                
            except click.ClickException as e:
                # Click exceptions already have good error messages
                if should_exit:
                    if should_display:
                        if json_output:
                            # Try to get command name
                            command_name = "unknown"
                            if ctx and hasattr(ctx, 'command') and ctx.command:
                                command_name = getattr(ctx.command, 'name', 'unknown')
                            click.echo(json.dumps({"error": str(e), "type": "ClickException", "command": command_name}, indent=2))
                        else:
                            click.echo(str(e), err=True)
                    sys.exit(1)
                raise
            except Exception as e:
                error_type = type(e).__name__
                error_msg = str(e)
                # Try to get command name from multiple sources
                command_name = "unknown"
                if ctx:
                    if hasattr(ctx, 'command') and ctx.command:
                        command_name = getattr(ctx.command, 'name', 'unknown')
                    elif hasattr(ctx, 'info_name') and ctx.info_name:
                        command_name = ctx.info_name
                
                if should_exit:
                    if should_display:
                        if json_output:
                            click.echo(json.dumps({
                                "error": error_msg,
                                "type": error_type,
                                "command": command_name
                            }, indent=2))
                        else:
                            click.echo(f"❌ Command '{command_name}' failed", err=True)
                            click.echo(f"   Error Type: {error_type}", err=True)
                            click.echo(f"   Error Message: {error_msg}", err=True)
                            click.echo(f"\n💡 Full traceback:", err=True)
                            import traceback
                            click.echo(traceback.format_exc(), err=True)
                    sys.exit(1)
                raise
        
        # Preserve Click command attributes (params, etc.) that @wraps might not copy
        if hasattr(func, '__click_params__'):
            setattr(wrapper, '__click_params__', func.__click_params__)
        if hasattr(func, 'params'):
            setattr(wrapper, 'params', func.params)
        
        return wrapper
    return decorator

