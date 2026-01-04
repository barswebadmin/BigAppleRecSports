"""
Modal handling logic for Slack interactions.
Separated from slack_service.py to keep that file focused on service coordination.
"""

import logging
from typing import Any, Optional

from slack_sdk.models.views import View

from .block_builders import SlackBlockBuilder

logger = logging.getLogger(__name__)


class SlackModalHandlers:
    """Handles Slack modal creation, display, and submission processing"""

    def __init__(self, api_client: Any, gas_webhook_url: str):
        self.api_client = api_client
        self.gas_webhook_url = gas_webhook_url


    def show_modal(
        self,
        client: Any,
        trigger_id: str,
        modal_view: View,
        show_loading: bool = False,
        loading_message: str = "Loading..."
    ) -> Optional[str]:
        """
        Show a modal, optionally with a loading state first.
        
        This is the unified method for displaying Slack modals across the application.
        It supports showing a loading state while processing, with automatic fallback
        if loading fails.
        
        Args:
            client: Slack WebClient instance
            trigger_id: Trigger ID from the action/command
            modal_view: Typed View object from SlackBlockBuilder.modal()
            show_loading: Whether to show a loading modal first while processing
            loading_message: Custom loading message if show_loading is True
        
        Returns:
            view_id of the displayed modal, or None if failed
        
        Example:
            modal_view = SlackBlockBuilder.modal(
                title="My Modal",
                blocks=[...],
                submit_text="Submit",
                callback_id="my_modal",
                private_metadata="..."
            )
            view_id = handler.show_modal(client, trigger_id, modal_view)
        """
        try:
            if show_loading:
                # Show loading modal first, then update to actual modal
                view_id = self._show_loading_modal(client, trigger_id, loading_message)
                if view_id:
                    # Update loading modal to actual modal
                    try:
                        client.views_update(view_id=view_id, view=modal_view)
                        logger.info(f"Updated loading modal to actual modal (view_id: {view_id})")
                        return view_id
                    except Exception as update_error:
                        logger.error(f"Error updating loading modal: {update_error}")
                        # Fallback: try opening directly
                        return self._open_modal_directly(client, trigger_id, modal_view)
                else:
                    # Fallback: open modal directly if loading failed
                    logger.warning("Loading modal failed to open, opening actual modal directly")
                    return self._open_modal_directly(client, trigger_id, modal_view)
            else:
                # Open modal directly without loading state
                return self._open_modal_directly(client, trigger_id, modal_view)
        except Exception as e:
            logger.error(f"Error showing modal: {e}")
            return None

    def show_loading_modal(
        self,
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
            view_id = handler.show_loading_modal(client, trigger_id, "Processing...")
            # ... do some work ...
            handler.update_modal(client, view_id, final_modal_view)
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

    def _show_loading_modal(
        self,
        client: Any,
        trigger_id: str,
        loading_message: str = "Loading..."
    ) -> Optional[str]:
        """Internal helper that calls show_loading_modal(). Kept for backwards compatibility."""
        return self.show_loading_modal(client, trigger_id, loading_message)

    def _open_modal_directly(
        self,
        client: Any,
        trigger_id: str,
        modal_view: View
    ) -> Optional[str]:
        """
        Open a modal directly without loading state.
        Internal helper for show_modal().
        """
        try:
            modal_response = client.views_open(trigger_id=trigger_id, view=modal_view)
            view_id = modal_response.get("view", {}).get("id") if modal_response else None
            logger.info(f"Opened modal directly with view_id: {view_id}")
            return view_id
        except Exception as e:
            logger.error(f"Error opening modal directly: {e}")
            return None

    def update_modal(
        self,
        client: Any,
        view_id: str,
        modal_view: View,
        show_loading: bool = False,
        loading_message: str = "Loading..."
    ) -> bool:
        """
        Update an existing modal, optionally with a loading state first.
        
        Args:
            client: Slack WebClient instance
            view_id: ID of the modal view to update
            modal_view: Typed View object from SlackBlockBuilder.modal()
            show_loading: Whether to show a loading state first
            loading_message: Custom loading message if show_loading is True
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if show_loading:
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



