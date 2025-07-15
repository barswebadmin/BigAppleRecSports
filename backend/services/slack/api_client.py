"""
Slack API client utilities.
Handles the low-level Slack API communication.
"""

import requests
import json
import sys
import os
from typing import Dict, Any, Optional, List
import logging

logger = logging.getLogger(__name__)


def _is_test_mode() -> bool:
    """
    Detect if we're running in test mode.
    Returns True if pytest is running or if TESTING environment variable is set.
    """
    # Check if pytest is running
    if 'pytest' in sys.modules:
        return True
    
    # Check if we're running via pytest command
    if any('pytest' in arg for arg in sys.argv):
        return True
    
    # Check for explicit TESTING environment variable
    if os.getenv('TESTING', '').lower() in ('true', '1', 'yes'):
        return True
    
    # Check if we're running test files
    if any('test_' in arg or arg.endswith('_test.py') for arg in sys.argv):
        return True
    
    return False


class MockSlackApiClient:
    """Mock Slack API client for testing purposes."""
    
    def __init__(self, bearer_token: str, channel_id: str):
        self.bearer_token = bearer_token
        self.channel_id = channel_id
        logger.info("🧪 Using MockSlackApiClient - no real Slack requests will be made")
    
    def send_message(self, message_text: str, action_buttons: Optional[List[Dict[str, Any]]] = None, 
                    slack_text: Optional[str] = None) -> Dict[str, Any]:
        """Mock send_message that logs but doesn't make real requests"""
        logger.info(f"🧪 MOCK: Would send Slack message to {self.channel_id}")
        logger.debug(f"🧪 MOCK: Message content: {message_text[:100]}...")
        
        return {
            "success": True,
            "message": "Mock message sent successfully",
            "ts": "1234567890.123456",
            "channel": self.channel_id,
            "slack_response": {"ok": True, "ts": "1234567890.123456"}
        }
    
    def update_message(self, message_ts: str, message_text: str, 
                      action_buttons: Optional[List[Dict[str, Any]]] = None,
                      slack_text: Optional[str] = None) -> Dict[str, Any]:
        """Mock update_message that logs but doesn't make real requests"""
        logger.info(f"🧪 MOCK: Would update Slack message {message_ts} in {self.channel_id}")
        
        return {
            "success": True,
            "message": "Mock message updated successfully",
            "ts": message_ts,
            "channel": self.channel_id
        }
    
    def _create_standard_blocks(self, text: str, action_buttons: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Create standard Slack message blocks (mock version)"""
        blocks = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            }
        ]
        
        # Add action buttons if provided
        if action_buttons:
            # Remove any None buttons and ensure we have a valid list
            filtered_buttons = [btn for btn in action_buttons if btn is not None]
            if filtered_buttons:  # Only add actions if we have valid buttons
                blocks.append({
                    "type": "actions",
                    "elements": filtered_buttons
                })
        
        blocks.append({"type": "divider"})
        return blocks


class SlackApiClient:
    """Helper class for Slack API communication."""
    
    def __init__(self, bearer_token: str, channel_id: str):
        self.bearer_token = bearer_token
        self.channel_id = channel_id
        self.base_url = "https://slack.com/api"
    
    def send_message(self, message_text: str, action_buttons: Optional[List[Dict[str, Any]]] = None, 
                    slack_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Send a message to the configured Slack channel with optional action buttons
        
        Args:
            message_text: The message content to send
            action_buttons: Optional list of action buttons to include
            slack_text: Optional short text for notifications
            
        Returns:
            Dict containing success status and details
        """
        if not self.bearer_token:
            logger.error("No Slack bearer token configured")
            return {
                "success": False, 
                "error": "No Slack bearer token configured"
            }
        
        try:
            # Prepare the request
            url = f"{self.base_url}/chat.postMessage"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
            
            # Create blocks structure for rich formatting
            blocks = self._create_standard_blocks(message_text, action_buttons)
            
            payload = {
                "channel": self.channel_id,
                "text": slack_text or message_text,  # Fallback text for notifications
                "blocks": blocks,
                "unfurl_links": False,
                "unfurl_media": False
            }
            
            logger.info(f"Sending Slack message to channel {self.channel_id}")
            logger.debug(f"Message content: {message_text[:100]}...")
            
            # Send the request
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                logger.info("Slack message sent successfully")
                return {
                    "success": True,
                    "message": "Message sent successfully",
                    "ts": response_data.get("ts"),
                    "channel": response_data.get("channel"),
                    "slack_response": response_data
                }
            else:
                error_msg = response_data.get("error", "Unknown error")
                logger.error(f"Slack API error: {error_msg}")
                return {
                    "success": False,
                    "error": f"Slack API error: {error_msg}",
                    "slack_response": response_data
                }
                
        except requests.RequestException as e:
            logger.error(f"Request error sending Slack message: {str(e)}")
            return {
                "success": False,
                "error": f"Request error: {str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error sending Slack message: {str(e)}")
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }
    
    def update_message(self, message_ts: str, message_text: str, 
                      action_buttons: Optional[List[Dict[str, Any]]] = None,
                      slack_text: Optional[str] = None) -> Dict[str, Any]:
        """
        Update an existing Slack message
        
        Args:
            message_ts: Timestamp of the message to update
            message_text: New message content
            action_buttons: Optional list of action buttons to include
            slack_text: Optional short text for notifications
            
        Returns:
            Dict containing success status and details
        """
        if not self.bearer_token:
            logger.error("No Slack bearer token configured")
            return {
                "success": False, 
                "error": "No Slack bearer token configured"
            }
        
        try:
            url = f"{self.base_url}/chat.update"
            headers = {
                "Authorization": f"Bearer {self.bearer_token}",
                "Content-Type": "application/json"
            }
            
            # Create blocks structure for rich formatting
            blocks = self._create_standard_blocks(message_text, action_buttons)
            
            payload = {
                "channel": self.channel_id,
                "ts": message_ts,
                "text": slack_text or message_text,  # Fallback text for notifications
                "blocks": blocks
            }
            
            response = requests.post(url, headers=headers, data=json.dumps(payload))
            response_data = response.json()
            
            if response.status_code == 200 and response_data.get("ok"):
                logger.info("Slack message updated successfully")
                return {
                    "success": True,
                    "message": "Message updated successfully",
                    "ts": response_data.get("ts"),
                    "slack_response": response_data
                }
            else:
                error_msg = response_data.get("error", "Unknown error")
                logger.error(f"Slack update error: {error_msg}")
                return {
                    "success": False,
                    "error": f"Slack update error: {error_msg}",
                    "slack_response": response_data
                }
                
        except Exception as e:
            logger.error(f"Error updating Slack message: {str(e)}")
            return {
                "success": False,
                "error": f"Update error: {str(e)}"
            }
    
    def _create_standard_blocks(self, text: str, action_buttons: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """Create standard Slack message blocks matching the old implementation"""
        blocks = [
            {"type": "divider"},
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": text}
            }
        ]
        
        # Add action buttons if provided
        if action_buttons:
            # Remove any None buttons and ensure we have a valid list
            filtered_buttons = [btn for btn in action_buttons if btn is not None]
            if filtered_buttons:  # Only add actions if we have valid buttons
                blocks.append({
                    "type": "actions",
                    "elements": filtered_buttons
                })
        
        blocks.append({"type": "divider"})
        return blocks 