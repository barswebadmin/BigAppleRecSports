"""
Message parsing utilities for Slack messages.
Handles extraction of links, dates, and other information from Slack message content.
"""

import re
import logging
from typing import Dict, Any, Optional
from shared.date_utils import extract_season_dates

logger = logging.getLogger(__name__)


class SlackMessageParsers:
    """Utility class for parsing information from Slack messages"""

    @staticmethod
    def extract_sheet_link(message_text: str) -> str:
        """
        Extract Google Sheets link from message text.
        
        Args:
            message_text: The Slack message text to parse
            
        Returns:
            The extracted sheet link or empty string if not found
        """
        try:
            # Look for Google Sheets links in various formats
            patterns = [
                r'https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9_-]+',
                r'https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9_-]+/edit[^\\s]*',
                r'https://docs\.google\.com/spreadsheets/d/[a-zA-Z0-9_-]+/edit#gid=\d+',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message_text)
                if match:
                    return match.group(0)
            
            return ""
        except Exception as e:
            logger.warning(f"Failed to extract sheet link: {e}")
            return ""

    @staticmethod
    def extract_season_start_info(message_text: str) -> Dict[str, Optional[str]]:
        """
        Extract season start information from message text.
        
        Args:
            message_text: The Slack message text to parse
            
        Returns:
            Dict containing extracted season start information
        """
        try:
            result = {
                "season_start_date": None,
                "season_start_time": None,
                "season_name": None
            }
            
            # Look for season start patterns
            season_patterns = [
                r'season starts? (?:on )?([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)',
                r'starts? (?:on )?([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)',
                r'beginning (?:on )?([A-Za-z]+ \d{1,2}(?:st|nd|rd|th)?)',
            ]
            
            for pattern in season_patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    result["season_start_date"] = match.group(1)
                    break
            
            # Look for time patterns
            time_patterns = [
                r'at (\d{1,2}:\d{2}(?:\s?[AP]M)?)',
                r'(\d{1,2}:\d{2}(?:\s?[AP]M)?)',
            ]
            
            for pattern in time_patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    result["season_start_time"] = match.group(1)
                    break
            
            # Look for season name patterns
            season_name_patterns = [
                r'(summer|fall|winter|spring) (?:season|league)',
                r'(kickball|dodgeball|bowling|pickleball) (?:season|league)',
            ]
            
            for pattern in season_name_patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    result["season_name"] = match.group(1)
                    break
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to extract season start info: {e}")
            return {
                "season_start_date": None,
                "season_start_time": None,
                "season_name": None
            }

    @staticmethod
    def extract_order_number(message_text: str) -> Optional[str]:
        """
        Extract order number from message text.
        
        Args:
            message_text: The Slack message text to parse
            
        Returns:
            The extracted order number or None if not found
        """
        try:
            # Look for order number patterns
            patterns = [
                r'#(\d+)',
                r'order[:\s]+#?(\d+)',
                r'order number[:\s]+#?(\d+)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract order number: {e}")
            return None

    @staticmethod
    def extract_email(message_text: str) -> Optional[str]:
        """
        Extract email address from message text.
        
        Args:
            message_text: The Slack message text to parse
            
        Returns:
            The extracted email or None if not found
        """
        try:
            # Look for email patterns
            email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
            match = re.search(email_pattern, message_text)
            
            if match:
                return match.group(0)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract email: {e}")
            return None

    @staticmethod
    def extract_refund_amount(message_text: str) -> Optional[float]:
        """
        Extract refund amount from message text.
        
        Args:
            message_text: The Slack message text to parse
            
        Returns:
            The extracted refund amount or None if not found
        """
        try:
            # Look for amount patterns
            patterns = [
                r'\$(\d+(?:\.\d{2})?)',
                r'(\d+(?:\.\d{2})?)\s*dollars?',
                r'amount[:\s]+\$?(\d+(?:\.\d{2})?)',
            ]
            
            for pattern in patterns:
                match = re.search(pattern, message_text, re.IGNORECASE)
                if match:
                    try:
                        return float(match.group(1))
                    except ValueError:
                        continue
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract refund amount: {e}")
            return None
