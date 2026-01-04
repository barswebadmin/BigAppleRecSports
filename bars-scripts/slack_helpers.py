#!/usr/bin/env python3
"""
Shared Slack helper utilities for BARS scripts.

Provides reusable functions for common Slack operations like
dry-run previews, confirmation prompts, and change displays.
"""

import sys
import json
from typing import Dict, Any, Callable, Optional, Union, List


def format_display(data: Union[Dict, List], formatter_func: Optional[Callable[[Any], str]] = None, should_format: bool = True) -> str:
    """
    Format data for display or return raw JSON.
    
    Args:
        data: The data to display (dict, list, or other JSON-serializable type)
        formatter_func: Optional custom formatter function to format the data
        should_format: If True, use formatter_func; if False, return raw JSON
        
    Returns:
        Formatted string for display
    
    Example:
        def format_user(user):
            return f"Name: {user['name']}\nEmail: {user['email']}"
        
        # Formatted output
        output = format_display(user, format_user, should_format=True)
        
        # Raw JSON output
        output = format_display(user, format_user, should_format=False)
    """
    if should_format and formatter_func:
        return formatter_func(data)
    else:
        return json.dumps(data, indent=2)


def show_changes(
    title: str,
    changes: Dict[str, tuple],
    context_info: Optional[Dict[str, str]] = None
) -> bool:
    """
    Display what changes will be made in a standardized format.
    
    Args:
        title: Title for the changes section (e.g., "Profile updates")
        changes: Dict mapping field names to (old_value, new_value) tuples
        context_info: Optional dict of contextual info to display above changes
                     (e.g., {"User": "Chase Tucker", "Email": "chase@..."})
        
    Returns:
        True if there are actual changes, False if all values are identical
    
    Example:
        changes = {
            "title": ("Vice Commissioner", "Commissioner"),
            "phone": ("", "+1-555-123-4567")
        }
        context = {"User": "Chase Tucker", "Email": "chase@bigapplerecsports.com"}
        has_changes = show_changes("Profile updates", changes, context)
    """
    # Show context info if provided
    if context_info:
        for key, value in context_info.items():
            icon = "👤" if key == "User" else "📧" if key == "Email" else "ℹ️"
            print(f"{icon} {key}: {value}")
        print()
    
    # Show what will be updated
    print(f"🔄 {title} that will be made:")
    print("-" * 60)
    
    has_changes = False
    for field, (old_value, new_value) in changes.items():
        # Convert None to empty string for display
        old_display = old_value if old_value is not None else ""
        new_display = new_value if new_value is not None else ""
        
        if old_display == new_display:
            print(f"  {field}: '{new_display}' (no change)")
        else:
            print(f"  {field}:")
            print(f"    Old: '{old_display}'")
            print(f"    New: '{new_display}'")
            has_changes = True
    
    print("-" * 60)
    
    return has_changes


def confirm_action(
    prompt: str = "Press Enter to apply changes, or 'n' to cancel",
    cancel_message: str = "❌ Cancelled"
) -> bool:
    """
    Prompt user for confirmation before proceeding.
    
    Args:
        prompt: The confirmation prompt to display
        cancel_message: Message to show if user cancels
        
    Returns:
        True if user confirmed (pressed Enter), False if cancelled
    """
    print(f"\n{prompt}: ", end='', flush=True)
    try:
        response = input().strip().lower()
        if response == 'n':
            print(cancel_message)
            return False
        return True
    except (EOFError, KeyboardInterrupt):
        print(f"\n{cancel_message}")
        return False


def dry_run_and_confirm(
    title: str,
    changes: Dict[str, tuple],
    apply_func: Callable[[], bool],
    context_info: Optional[Dict[str, str]] = None,
    dry_run: bool = False,
    confirm_prompt: str = "Press Enter to apply changes, or 'n' to cancel",
    no_changes_message: str = "⚠️  No actual changes to make",
    applying_message: str = "⏳ Applying changes...",
    success_message: str = "✅ Changes applied successfully!",
    cancel_message: str = "❌ Cancelled"
) -> bool:
    """
    Generic dry-run and confirmation workflow for Slack operations.
    
    This function implements a safe two-step process:
    1. Preview: Show what will change
    2. Confirm: Ask user to confirm before applying
    
    Args:
        title: Title for the changes section
        changes: Dict mapping field names to (old_value, new_value) tuples
        apply_func: Callable that applies the changes (should return bool for success)
        context_info: Optional contextual info to display
        dry_run: If True, only show preview and exit
        confirm_prompt: Prompt for confirmation
        no_changes_message: Message if no actual changes detected
        applying_message: Message shown while applying
        success_message: Message on successful apply
        cancel_message: Message if user cancels
        
    Returns:
        True if changes applied successfully (or dry_run=True), False otherwise
    
    Example:
        def apply_updates():
            return client.users_profile_set(user=user_id, profile=updates)
        
        success = dry_run_and_confirm(
            title="Profile updates",
            changes={"title": ("Old", "New")},
            apply_func=apply_updates,
            context_info={"User": "Chase Tucker"},
            dry_run=False
        )
    """
    # Show what would change
    has_changes = show_changes(title, changes, context_info)
    
    if not has_changes:
        print(f"\n{no_changes_message}")
        return False
    
    # If dry-run mode, stop here
    if dry_run:
        print("\n🔍 Dry run - no changes made")
        return True
    
    # Confirm before applying
    if not confirm_action(confirm_prompt, cancel_message):
        return False
    
    # Apply changes
    print(f"\n{applying_message}")
    success = apply_func()
    
    if success:
        print(success_message)
        return True
    else:
        return False


def show_slack_user_context(user: Dict[str, Any]) -> Dict[str, str]:
    """
    Extract and format context information from a Slack user dict.
    
    Args:
        user: Slack user dict from get_user()
        
    Returns:
        Dict of formatted context info
    """
    profile = user.get("profile", {})
    return {
        "User": f"{user.get('real_name', 'Unknown')} ({user.get('name', 'Unknown')})",
        "Email": profile.get('email', 'N/A')
    }


def build_profile_changes(user: Dict[str, Any], profile_updates: Dict[str, str]) -> Dict[str, tuple]:
    """
    Build a changes dict for profile updates.
    
    Args:
        user: Slack user dict from get_user()
        profile_updates: Dict of fields to update
        
    Returns:
        Dict mapping field names to (old_value, new_value) tuples
    """
    current_profile = user.get("profile", {})
    changes = {}
    
    for field, new_value in profile_updates.items():
        old_value = current_profile.get(field, "")
        changes[field] = (old_value, new_value)
    
    return changes

