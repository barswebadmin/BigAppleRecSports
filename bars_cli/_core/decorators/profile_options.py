"""Decorator for adding profile field options to Click commands."""

from typing import Callable, Any, List, Dict, Optional
import inspect

import click_extra as click


def profile_options_from_model(model_class, include_optional: bool = True, help_texts: Optional[Dict[str, str]] = None):
    """
    Decorator to automatically add Click options for fields in a Pydantic model.
    
    Args:
        model_class: Pydantic model class (e.g., SlackUserProfile)
        include_optional: If True, include optional fields; if False, only required fields
        help_texts: Optional dict mapping field names to custom help text
        
    Example:
        @click.command('update')
        @profile_options_from_model(SlackUserProfile, include_optional=True)
        def update_cmd(ctx, real_name, display_name, title, phone, ...):
            # Options are automatically added for all fields
    """
    if help_texts is None:
        help_texts = {}
    
    # Get fields from model
    fields = []
    for field_name, field_info in model_class.model_fields.items():
        # Skip fields that shouldn't be updated via CLI
        if field_name.startswith('image_') or field_name in ('avatar_hash', 'team', 'skype', 
                                                              'status_emoji_display_info', 'status_expiration',
                                                              'huddle_state', 'huddle_state_expiration_ts',
                                                              'is_custom_image', 'real_name_normalized',
                                                              'display_name_normalized', 'status_text_canonical',
                                                              'real_name'):  # Skip read-only required fields
            continue
        
        # Include field if it's required OR if include_optional is True
        if field_info.is_required() or include_optional:
            fields.append(field_name)
    
    # Default help texts
    default_help = {
        'title': "User's title/position",
        'phone': "User's phone number",
        'status_text': "User's status text",
        'status_emoji': "User's status emoji (e.g., :tada:)",
        'email': "User's email address",
        'first_name': "User's first name",
        'last_name': "User's last name",
        'display_name': "User's display name",
        'real_name': "User's real name",
    }
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Add options in reverse order (Click applies decorators bottom-to-top)
        for field in reversed(fields):
            help_text = help_texts.get(field, default_help.get(field, f"User's {field.replace('_', ' ')}"))
            func = click.option(f'--{field}', help=help_text)(func)
        
        return func
    
    return decorator


def profile_options(fields: List[str], help_texts: Optional[Dict[str, str]] = None):
    """
    Decorator to automatically add Click options for specified profile fields.
    
    Args:
        fields: List of field names to create options for (e.g., ['title', 'phone', 'status_text'])
        help_texts: Optional dict mapping field names to custom help text
        
    Example:
        @click.command('update')
        @profile_options(['title', 'phone', 'status_text', 'status_emoji'])
        def update_cmd(ctx, title, phone, status_text, status_emoji, ...):
            # Options are automatically added
    """
    if help_texts is None:
        help_texts = {}
    
    # Default help texts
    default_help = {
        'title': "User's title/position",
        'phone': "User's phone number",
        'status_text': "User's status text",
        'status_emoji': "User's status emoji (e.g., :tada:)",
        'email': "User's email address",
        'first_name': "User's first name",
        'last_name': "User's last name",
        'display_name': "User's display name",
        'real_name': "User's real name",
    }
    
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        # Add options in reverse order (Click applies decorators bottom-to-top)
        for field in reversed(fields):
            help_text = help_texts.get(field, default_help.get(field, f"User's {field.replace('_', ' ')}"))
            func = click.option(f'--{field}', help=help_text)(func)
        
        return func
    
    return decorator

