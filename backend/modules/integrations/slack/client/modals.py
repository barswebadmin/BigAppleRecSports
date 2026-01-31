"""
Modal handling functions for Slack interactions.
Pure functions for opening, updating, and managing Slack modals.
"""

import logging
import sys
from pathlib import Path
from typing import Any, Optional

from slack_sdk.models.views import View

# Lazy import to avoid circular dependencies - import when actually used
def _get_slack_block_builder():
    """Lazy import of SlackBlockBuilder to avoid circular dependencies."""
    # Import from backend modules directly
    try:
        from modules.integrations.slack.builders.block_builders import SlackBlockBuilder
        return SlackBlockBuilder
    except ImportError:
        # Try relative import as fallback
        try:
            from ..builders.block_builders import SlackBlockBuilder
            return SlackBlockBuilder
        except ImportError:
            # If all else fails, raise a helpful error
            raise ImportError(
                "SlackBlockBuilder not found. "
                "Make sure backend/modules/integrations/slack/builders/block_builders.py exists."
            )

# Import lazily when actually used
SlackBlockBuilder = None

logger = logging.getLogger(__name__)


def show_modal(
    client: Any,
    trigger_id: str,
    modal_view: View,
    loading_message: str = "Loading..."
) -> Optional[str]:
    """
    Show a modal with a loading state first, then update to the actual modal.
    
    Always shows a loading state while processing, with automatic fallback if loading fails.
    
    Args:
        client: Slack WebClient instance
        trigger_id: Trigger ID from the action/command
        modal_view: Typed View object from SlackBlockBuilder.modal()
        loading_message: Custom loading message to display
    
    Returns:
        view_id of the displayed modal, or None if failed
    
    Example:
        # Lazy load SlackBlockBuilder
        global SlackBlockBuilder
        if SlackBlockBuilder is None:
            SlackBlockBuilder = _get_slack_block_builder()
        
        modal_view = SlackBlockBuilder.modal(
            title="My Modal",
            blocks=[...],
            submit_text="Submit",
            callback_id="my_modal",
            private_metadata="..."
        )
        view_id = show_modal(client, trigger_id, modal_view)
    """
    try:
        # Always show loading modal first, then update to actual modal
        view_id = show_loading_modal(client, trigger_id, loading_message)
        if view_id:
            # Update loading modal to actual modal
            try:
                client.views_update(view_id=view_id, view=modal_view)
                logger.info(f"Updated loading modal to actual modal (view_id: {view_id})")
                return view_id
            except Exception as update_error:
                logger.error(f"Error updating loading modal: {update_error}")
                # Fallback: try opening directly
                try:
                    modal_response = client.views_open(trigger_id=trigger_id, view=modal_view)
                    fallback_view_id = modal_response.get("view", {}).get("id") if modal_response else None
                    logger.info(f"Opened modal directly as fallback (view_id: {fallback_view_id})")
                    return fallback_view_id
                except Exception as e:
                    logger.error(f"Error opening modal directly: {e}")
                    return None
        else:
            # Fallback: open modal directly if loading failed
            logger.warning("Loading modal failed to open, opening actual modal directly")
            try:
                modal_response = client.views_open(trigger_id=trigger_id, view=modal_view)
                fallback_view_id = modal_response.get("view", {}).get("id") if modal_response else None
                logger.info(f"Opened modal directly (view_id: {fallback_view_id})")
                return fallback_view_id
            except Exception as e:
                logger.error(f"Error opening modal directly: {e}")
                return None
    except Exception as e:
        logger.error(f"Error showing modal: {e}")
        return None


def show_loading_modal(
    client: Any,
    trigger_id: str,
    loading_message: str = "Loading..."
) -> Optional[str]:
    """
    Show a loading modal and return its view_id.
    
    This is useful when you need to show a loading state while performing
    asynchronous operations, then update the modal later with update_modal().
    
    Args:
        client: Slack WebClient instance
        trigger_id: Trigger ID from the action/command
        loading_message: Custom loading message to display
    
    Returns:
        view_id of the opened loading modal, or None if failed
    
    Example:
        view_id = show_loading_modal(client, trigger_id, "Processing...")
        # ... do some work ...
        update_modal(client, view_id, final_modal_view)
    """
    loading_modal = SlackBlockBuilder.loading_modal(
        title="Loading...",
        message=f"{loading_message}\n\nPlease wait..."
    )
    
    try:
        modal_response = client.views_open(trigger_id=trigger_id, view=loading_modal)
        view_id = modal_response.get("view", {}).get("id") if modal_response else None
        logger.info(f"Opened loading modal with view_id: {view_id}")
        return view_id
    except Exception as e:
        logger.error(f"Error opening loading modal: {e}")
        return None


def update_modal(
    client: Any,
    view_id: str,
    modal_view: View,
    loading_message: str = "Loading..."
) -> bool:
    """
    Update an existing modal with a loading state first, then the actual modal.
    
    Args:
        client: Slack WebClient instance
        view_id: ID of the modal view to update
        modal_view: Typed View object from SlackBlockBuilder.modal()
        loading_message: Custom loading message to display
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Always show loading state first
        loading_modal = SlackBlockBuilder.loading_modal(
            title="Loading...",
            message=f"{loading_message}\n\nPlease wait..."
        )
        client.views_update(view_id=view_id, view=loading_modal)
        logger.info(f"Updated modal to loading state (view_id: {view_id})")
        
        # Update to actual modal
        client.views_update(view_id=view_id, view=modal_view)
        logger.info(f"Updated modal (view_id: {view_id})")
        return True
    except Exception as e:
        logger.error(f"Error updating modal: {e}")
        return False

