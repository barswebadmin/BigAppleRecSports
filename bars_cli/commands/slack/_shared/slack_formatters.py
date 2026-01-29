"""Slack formatters for displaying Slack entities and errors."""

from typing import List, Callable, Optional, Any, Dict

import click_extra as click
from rich.console import Console
from rich.table import Table

from bars_cli._core.ui.display import create_info_table
from bars_cli._core.utils.json_output import output_json_error
from bars_cli.backend_services.slack.models.slack_user import SlackUser
from bars_cli.backend_services.slack.models.slack_group import SlackGroup

def format_channels(channels: list[Dict[str, Any]]) -> str:
    """Format channels list for display."""
    if not channels:
        return "No channels found."
    
    output = []
    output.append(f"\n📺 Slack Channels ({len(channels)} total):\n")
    
    # Group by type
    public_channels = [c for c in channels if not c.get('is_private', False)]
    private_channels = [c for c in channels if c.get('is_private', False)]
    
    if public_channels:
        output.append("🌐 Public Channels:")
        for channel in sorted(public_channels, key=lambda c: c.get('name', '')):
            name = channel.get('name', 'N/A')
            channel_id = channel.get('id', 'N/A')
            archived = " [ARCHIVED]" if channel.get('is_archived', False) else ""
            members = channel.get('num_members', '?')
            output.append(f"  • #{name:<30} ({channel_id}) - {members} members{archived}")
    
    if private_channels:
        output.append("\n🔒 Private Channels:")
        for channel in sorted(private_channels, key=lambda c: c.get('name', '')):
            name = channel.get('name', 'N/A')
            channel_id = channel.get('id', 'N/A')
            archived = " [ARCHIVED]" if channel.get('is_archived', False) else ""
            members = channel.get('num_members', '?')
            output.append(f"  • #{name:<30} ({channel_id}) - {members} members{archived}")
    
    return '\n'.join(output)

def format_users(users: list[SlackUser]) -> str:
    """Format users list for display."""
    if not users:
        return "No users found."
    
    output = []
    output.append(f"\n👥 Slack Users ({len(users)} total):\n")
    
    # Group by status
    # deleted and is_bot are always present in API responses, use direct access
    active_users = [u for u in users if not u.deleted and not u.is_bot]
    bots = [u for u in users if u.is_bot]
    deleted_users = [u for u in users if u.deleted]
    
    if active_users:
        output.append("✅ Active Users:")
        for user in sorted(active_users, key=lambda u: u.real_name or ''):
            name = user.real_name or 'N/A'
            user_id = user.id
            email = user.email or 'N/A'
            title = user.title or ''
            title_display = f" - {title}" if title else ""
            output.append(f"  • {name:<30} ({user_id}) {email}{title_display}")
    
    if bots:
        output.append(f"\n🤖 Bots ({len(bots)}):")
        for bot in sorted(bots, key=lambda u: u.real_name or ''):
            name = bot.real_name or 'N/A'
            bot_id = bot.id
            output.append(f"  • {name:<30} ({bot_id})")
    
    if deleted_users:
        output.append(f"\n🗑️  Deleted Users ({len(deleted_users)}):")
        for user in sorted(deleted_users, key=lambda u: u.real_name or ''):
            name = user.real_name or 'N/A'
            user_id = user.id
            output.append(f"  • {name:<30} ({user_id})")
    
    return '\n'.join(output)

def format_group(group: SlackGroup) -> str:
    """Format usergroup data for display."""
    name = group.name or 'N/A'
    handle = group.handle or 'N/A'
    group_id = group.id or 'N/A'
    description = group.description or ''
    is_disabled = group.date_delete > 0 if group.date_delete else False
    
    output = []
    output.append("\n👥 Usergroup Details:\n")
    output.append(f"  Name: {name}")
    output.append(f"  Handle: @{handle}")
    output.append(f"  Group ID: {group_id}")
    
    if description:
        output.append(f"  Description: {description}")
    
    if is_disabled:
        output.append("  ⚠️  Status: DISABLED")
    
    users = group.users or []
    user_count = len(users)
    output.append(f"  Members: {user_count}")
    
    if users:
        output.append("\n  Member IDs:")
        for user_id in users[:20]:  # Show first 20
            output.append(f"    - {user_id}")
    if len(users) > 20:
        output.append(f"    ... and {len(users) - 20} more")
    
    return '\n'.join(output)


# ============================================================================
# Error Formatting
# ============================================================================

def format_error(
    error_msg: str,
    error_type: Optional[str] = None,
    json_output: bool = False,
    should_display: bool = True
) -> None:
    """Format and display error message.
    
    Args:
        error_msg: Error message text
        error_type: Optional error type name
        json_output: Whether to output JSON format
        should_display: Whether to display the error
    """
    if not should_display:
        return
    
    if json_output:
        output_json_error(error_msg, error_type=error_type)
    else:
        if error_type:
            click.echo(f"❌ Unexpected error ({error_type}): {error_msg}", err=True)
        else:
            click.echo(f"❌ {error_msg}", err=True)


# ============================================================================
# Rich-based Formatters
# ============================================================================

def format_grouped_list(
    items: List[Any],
    *,
    title: str,
    group_func: Callable[[Any], str],
    format_item_func: Callable[[Any], str],
    console: Optional[Console] = None,
    empty_message: str = "No items found."
) -> None:
    """Format a list of items grouped by a function, displayed as Rich tables.
    
    Common pattern for formatting lists with grouping (e.g., active/deleted users,
    public/private channels).
    
    Args:
        items: List of items to format
        title: Main title for the output
        group_func: Function that returns group name for each item
        format_item_func: Function that formats each item as a string
        console: Optional Rich Console instance (creates new if None)
        empty_message: Message to display if items list is empty
    """
    if console is None:
        console = Console()
    
    if not items:
        console.print(f"[dim]{empty_message}[/dim]")
        return
    
    # Group items
    groups: Dict[str, List[Any]] = {}
    for item in items:
        group_name = group_func(item)
        if group_name not in groups:
            groups[group_name] = []
        groups[group_name].append(item)
    
    # Display header
    console.print(f"\n[bold cyan]{title} ({len(items)} total):[/bold cyan]\n")
    
    # Display each group
    for group_name, group_items in groups.items():
        console.print(f"[bold]{group_name}:[/bold]")
        for item in sorted(group_items, key=lambda x: format_item_func(x)):
            console.print(f"  • {format_item_func(item)}")
        console.print()


def format_key_value_details(
    data: Dict[str, Any],
    *,
    title: str,
    field_mappings: List[tuple],
    console: Optional[Console] = None,
    show_empty: bool = False
) -> None:
    """Format key-value details as a Rich info table.
    
    Common pattern for displaying entity details (e.g., user, group, channel).
    
    Args:
        data: Dictionary containing the data
        title: Title for the details section
        field_mappings: List of (display_name, data_key, formatter_func) tuples.
            formatter_func is optional and can be None for direct value access.
        console: Optional Rich Console instance (creates new if None)
        show_empty: Whether to show fields with empty/None values
    """
    if console is None:
        console = Console()
    
    rows = []
    for display_name, data_key, formatter in field_mappings:
        value = data.get(data_key) if isinstance(data, dict) else getattr(data, data_key, None)
        
        if formatter:
            value = formatter(value)
        else:
            value = value or 'N/A'
        
        if value and value != 'N/A' or show_empty:
            rows.append((display_name, value))
    
    if rows:
        table = create_info_table(rows, title=title, show_header=False)
        console.print(table)
        console.print()


def format_list_with_table(
    items: List[Any],
    *,
    title: str,
    columns: List[tuple],
    format_row_func: Callable[[Any], List[str]],
    console: Optional[Console] = None,
    empty_message: str = "No items found."
) -> None:
    """Format a list of items as a Rich table.
    
    Common pattern for displaying tabular data (e.g., line items, transactions).
    
    Args:
        items: List of items to display
        title: Table title
        columns: List of (column_name, justify) tuples (justify can be "left", "right", "center", or None)
        format_row_func: Function that takes an item and returns a list of string values for the row
        console: Optional Rich Console instance (creates new if None)
        empty_message: Message to display if items list is empty
    """
    if console is None:
        console = Console()
    
    if not items:
        console.print(f"[dim]{empty_message}[/dim]")
        return
    
    table = Table(title=title, show_header=True)
    
    for col_name, justify in columns:
        table.add_column(col_name, justify=justify)
    
    for item in items:
        row_values = format_row_func(item)
        table.add_row(*row_values)
    
    console.print(table)
    console.print()