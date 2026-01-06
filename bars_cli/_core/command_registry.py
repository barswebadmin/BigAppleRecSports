"""Command discovery and registration utilities for Click CLI."""

import importlib
import inspect
import pkgutil
from typing import List, Optional, Set

import click


_DISCOVERED: Set[str] = set()


def _is_click_command(obj) -> bool:
    """Check if object is a Click command."""
    return isinstance(obj, click.Command)


def _is_click_group(obj) -> bool:
    """Check if object is a Click group."""
    return isinstance(obj, click.Group)


def _register_from_module(
    cli: click.Group,
    module,
    parent_group: Optional[click.Group] = None
) -> None:
    """Register commands and groups from a module.
    
    Args:
        cli: Root CLI group
        module: Python module to scan for commands
        parent_group: Optional parent group to add commands to
    """
    target = parent_group if parent_group else cli
    first_group = None  # Track the first group found in this module
    
    for _, obj in inspect.getmembers(module):
        if _is_click_group(obj):
            name = getattr(obj, "name", None)
            if not name or name in _DISCOVERED:
                continue
            
            # Register group: use parent_group if provided, otherwise use first_group or root
            if parent_group:
                parent_group.add_command(obj, name)
            elif first_group is not None:
                # If we've already found a group in this module, register subsequent groups under it
                first_group.add_command(obj, name)
            else:
                cli.add_command(obj, name)
                # This is the first group - remember it for subsequent groups/commands
                first_group = obj
            _DISCOVERED.add(name)
            # Update target so subsequent commands in this module register under this group
            target = obj
            
        elif _is_click_command(obj):
            name = getattr(obj, "name", None)
            if not name or name in _DISCOVERED:
                continue
            
            target.add_command(obj, name)
            
            # Also register at root level for direct access
            if name not in cli.commands:
                cli.add_command(obj, name)
            
            _DISCOVERED.add(name)


def discover_commands(
    cli: click.Group,
    package,
    parent_group: Optional[click.Group] = None
) -> None:
    """Discover and register all commands from a package.
    
    Recursively scans package for Click commands and groups.
    
    Args:
        cli: Root CLI group
        package: Python package to scan
        parent_group: Optional parent group for nested commands
        
    Example:
        import bars_cli.commands as commands_pkg
        discover_commands(cli, commands_pkg)
    """
    if not hasattr(package, '__path__'):
        return
    
    for modinfo in pkgutil.iter_modules(package.__path__):
        # Skip private modules
        if modinfo.name.startswith("_"):
            continue
        
        full_module_name = f"{package.__name__}.{modinfo.name}"
        
        try:
            if modinfo.ispkg:
                # Handle sub-packages recursively
                subpackage = importlib.import_module(full_module_name)
                _register_from_module(cli, subpackage, parent_group)
                
                # Check if we found a group in this subpackage to use as parent for recursive discovery
                # This matches engine-cli logic: use groups that were just discovered
                current_group = parent_group
                for _, obj in inspect.getmembers(subpackage):
                    if _is_click_group(obj):
                        name = getattr(obj, "name", None)
                        if name and name in _DISCOVERED:
                            # Use this group as the parent for commands in this subpackage
                            current_group = obj
                            break
                
                # Recursively discover in subpackage
                if hasattr(subpackage, '__path__'):
                    discover_commands(cli, subpackage, current_group)
            else:
                # Handle modules
                module = importlib.import_module(full_module_name)
                _register_from_module(cli, module, parent_group)
        except Exception:
            # Skip modules that fail to import
            continue


def get_command(
    cli_group: click.Group,
    cmd_name: str,
    search_nested: bool = True
) -> Optional[click.Command]:
    """Get command from group, optionally searching nested groups.
    
    Args:
        cli_group: Click group to search in
        cmd_name: Name of command to find
        search_nested: If True, search nested groups recursively
        
    Returns:
        Command if found, None otherwise
    """
    # Check direct commands first
    if cmd_name in cli_group.commands:
        return cli_group.commands[cmd_name]
    
    # Try get_command (handles lazy loading)
    try:
        ctx = click.Context(cli_group)
        cmd = cli_group.get_command(ctx, cmd_name)
        if cmd:
            return cmd
    except Exception:
        pass
    
    # Search nested groups
    if search_nested:
        for name, group in cli_group.commands.items():
            if isinstance(group, click.Group):
                ctx = click.Context(group)
                cmd = group.get_command(ctx, cmd_name)
                if cmd:
                    return cmd
    
    return None


def list_all_commands(cli_group: click.Group, include_hidden: bool = False) -> List[str]:
    """List all commands including those from nested groups.
    
    Args:
        cli_group: Click group to list commands from
        include_hidden: Include hidden commands
        
    Returns:
        Sorted list of all command names
    """
    commands = set()
    
    def _collect_commands(group: click.Group) -> None:
        """Recursively collect commands from a group."""
        if not isinstance(group, click.Group):
            return
        
        for cmd_name, cmd_obj in group.commands.items():
            if cmd_obj is None:
                continue
            
            # Skip hidden commands unless requested
            if cmd_obj.hidden and not include_hidden:
                continue
            
            if isinstance(cmd_obj, click.Group):
                # Recursively collect from sub-groups
                _collect_commands(cmd_obj)
            else:
                # Add command name
                commands.add(cmd_name)
    
    _collect_commands(cli_group)
    return sorted(commands)

