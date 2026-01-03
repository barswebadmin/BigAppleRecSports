"""Slack ephemeral message updating utilities."""
import logging
from typing import List, Dict, Any, Optional, Union
import requests

try:
    from slack_sdk.models.blocks import Block
except ImportError:
    Block = None

logger = logging.getLogger(__name__)


def update_ephemeral_message(
    response_url: str,
    text: str,
    blocks: Union[List[Dict[str, Any]], List[Block]],
    show_loading: bool = False,
    loading_message: str = "Loading..."
) -> None:
    """
    Update an ephemeral message via response_url.
    
    Args:
        response_url: The response_url from Slack interaction
        text: Fallback text for the message
        blocks: List of Slack Block Kit blocks (dicts or Block objects)
        show_loading: Whether to show loading indicator
        loading_message: Custom loading message text
    """
    try:
        blocks_list = _convert_blocks_to_dicts(blocks)
        
        if show_loading:
            blocks_list = _add_loading_indicator(blocks_list, loading_message)
        
        payload = {
            "replace_original": True,
            "text": text,
            "blocks": blocks_list
        }
        
        response = requests.post(response_url, json=payload, timeout=5)
        response.raise_for_status()
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error updating ephemeral message: {e}")
    except Exception as e:
        logger.error(f"Unexpected error updating ephemeral message: {e}")


def _convert_blocks_to_dicts(blocks: Union[List[Dict[str, Any]], List[Block]]) -> List[Dict[str, Any]]:
    """Convert Block objects to dictionaries if needed."""
    if not blocks:
        return []
    
    if Block and isinstance(blocks[0], Block):
        return [block.to_dict() for block in blocks]
    
    return blocks


def _add_loading_indicator(blocks: List[Dict[str, Any]], loading_message: str) -> List[Dict[str, Any]]:
    """Add a loading indicator to the beginning of blocks."""
    loading_block = {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": f"⏳ {loading_message}"
        }
    }
    return [loading_block] + blocks

