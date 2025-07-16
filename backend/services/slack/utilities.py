"""
Slack utility functions.
Contains helper functions for parsing, validation, and data extraction.
"""

from typing import Dict, Any, Optional
import logging
import hmac
import hashlib
import json
import re
from config import settings

logger = logging.getLogger(__name__)


class SlackUtilities:
    """Utility functions for Slack operations"""
    
    def __init__(self):
        pass
    
    def verify_slack_signature(self, body: bytes, timestamp: str, signature: str) -> bool:
        """Verify that the request came from Slack"""
        if not settings.slack_signing_secret:
            logger.warning("No Slack signing secret configured - skipping signature verification")
            return True  # Skip verification in development
        
        # Create the signature base string
        sig_basestring = f"v0:{timestamp}:{body.decode('utf-8')}"
        
        # Create the expected signature
        expected_signature = 'v0=' + hmac.new(
            settings.slack_signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(expected_signature, signature)

    def parse_button_value(self, value: str) -> Dict[str, str]:
        """Parse button value like 'rawOrderNumber=#12345|orderId=gid://shopify/Order/12345|refundAmount=36.00'"""
        request_data = {}
        button_values = value.split('|')
        
        for button_value in button_values:
            if '=' in button_value:
                key, val = button_value.split('=', 1)  # Split only on first =
                request_data[key] = val
        
        return request_data

    def extract_text_from_blocks(self, blocks: list) -> str:
        """Extract text content from Slack blocks structure"""
        try:
            text_parts = []
            
            for block in blocks:
                if not isinstance(block, dict):
                    continue
                    
                block_type = block.get("type", "")
                
                # Extract text from section blocks
                if block_type == "section":
                    text_obj = block.get("text", {})
                    if isinstance(text_obj, dict) and "text" in text_obj:
                        text_parts.append(text_obj["text"])
                
                # Extract text from context blocks
                elif block_type == "context":
                    elements = block.get("elements", [])
                    for element in elements:
                        if isinstance(element, dict) and "text" in element:
                            text_parts.append(element["text"])
                
                # Extract text from rich_text blocks
                elif block_type == "rich_text":
                    elements = block.get("elements", [])
                    for element in elements:
                        if isinstance(element, dict):
                            if element.get("type") == "rich_text_section":
                                sub_elements = element.get("elements", [])
                                for sub_element in sub_elements:
                                    if isinstance(sub_element, dict) and "text" in sub_element:
                                        text_parts.append(sub_element["text"])
            
            return "\n".join(text_parts)
            
        except Exception as e:
            logger.error(f"Error extracting text from blocks: {e}")
            return ""
    
    def extract_data_from_slack_thread(self, thread_ts: str) -> str:
        """Extract data from the Slack thread message (placeholder implementation)"""
        # TODO: Implement actual Slack thread message retrieval
        # For now, return empty string to use fallback values
        return ""

    def extract_sheet_link(self, message_text: str) -> str:
        """Extract Google Sheets link from message"""
        import html
        
        print(f"\n🔍 === EXTRACT SHEET LINK DEBUG ===")
        print(f"📝 Input message text length: {len(message_text)}")
        print(f"📝 Input message text preview: {message_text[:300]}...")
        
        # Decode HTML entities like &amp; that might be in Slack message blocks
        decoded_text = html.unescape(message_text)
        print(f"📝 Decoded text preview: {decoded_text[:300]}...")
        
        # Look for different Google Sheets link patterns
        patterns = [
            # Pattern 1: Slack link format <URL|text> (with :link: emoji)
            r':link:\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*',
            # Pattern 2: Slack link format <URL|text> (with 🔗 emoji)
            r'🔗\s*\*<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>\*',
            # Pattern 3: Slack link format <URL|text> (without emoji)
            r'<(https://docs\.google\.com/spreadsheets/[^>|]+)\|[^>]*>',
            # Pattern 4: Direct URL after emoji
            r'🔗[^h]*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)',
            # Pattern 5: URL on same line as emoji
            r'🔗.*?(https://docs\.google\.com/spreadsheets/[^\s\n]+)',
            # Pattern 6: URL anywhere in the message
            r'(https://docs\.google\.com/spreadsheets/[^\s\n]+)'
        ]
        
        for i, pattern in enumerate(patterns):
            print(f"🔍 Testing pattern {i+1}: {pattern}")
            match = re.search(pattern, decoded_text)
            if match:
                url = match.group(1)
                # Clean up the URL (remove any remaining HTML entities)
                url = html.unescape(url)
                print(f"✅ Pattern {i+1} matched! URL: {url}")
                print(f"✅ Returning URL: {url}")
                print("=== END EXTRACT SHEET LINK DEBUG ===\n")
                return url
            else:
                print(f"❌ Pattern {i+1} no match")
        
        # Fallback if no URL found - use the user-provided fallback URL
        fallback_url = "https://docs.google.com/spreadsheets/d/11oXF8a7lZV0349QFVYyxPw8tEokoLJqZDrGDpzPjGtw/edit"
        print("❌ No patterns matched, using fallback")
        print(f"✅ Fallback URL: {fallback_url}")
        print("=== END EXTRACT SHEET LINK DEBUG ===\n")
        return fallback_url

    def extract_season_start_info(self, message_text: str) -> Dict[str, Optional[str]]:
        """Extract season start information from message"""
        print(f"\n🔍 === EXTRACT SEASON START INFO DEBUG ===")
        print(f"📝 Input message text length: {len(message_text)}")
        print(f"📝 Input message text preview: {message_text[:200]}...")
        
        # Look for different product/season patterns
        patterns = [
            # Pattern 1: Season Start Date line with product (with link)
            r"Season Start Date for <[^|]+\|([^>]+)> is (.+?)\.",
            # Pattern 2: Season Start Date line with product (plain text)
            r"Season Start Date for (.+?) is (.+?)\.",
            # Pattern 3: Product Title field with Slack link - extract title from <URL|title>
            r"\*Product Title\*:\s*<[^|]+\|([^>]+)>",
            # Pattern 4: Product Title field with full Slack link
            r"\*Product Title\*:\s*(<[^>]+>)",
            # Pattern 5: Sport/Season/Day field with Slack link - extract title from <URL|title>
            r"\*Sport/Season/Day\*:\s*<[^|]+\|([^>]+)>",
            # Pattern 6: Sport/Season/Day field with full Slack link  
            r"\*Sport/Season/Day\*:\s*(<[^>]+>)",
            # Pattern 7: Product title with link <URL|title> (extract title only)
            r"Product Title:\s*<[^|]+\|([^>]+)>",
            r"Sport/Season/Day:\s*<[^|]+\|([^>]+)>",
            # Pattern 8: Product Title field (plain text)
            r"Product Title:\s*([^<\n]+)",
            # Pattern 9: Sport/Season/Day field (plain text)
            r"Sport/Season/Day:\s*([^<\n]+)"
        ]
        
        product_title = "Unknown Product"
        product_link = None
        season_start_date = "Unknown"
        
        # Try to find season start date with product (Pattern 1: with link)
        season_match = re.search(patterns[0], message_text)
        if season_match:
            product_title = season_match.group(1).strip()
            season_start_date = season_match.group(2).strip()
            print(f"✅ Pattern 1 matched! Product: {product_title}, Season Start: {season_start_date}")
            print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
            return {"product_title": product_title, "season_start_date": season_start_date, "product_link": None}
        
        # Try to find season start date with product (Pattern 2: plain text)
        season_match = re.search(patterns[1], message_text)
        if season_match:
            product_title = season_match.group(1).strip()
            season_start_date = season_match.group(2).strip()
            print(f"✅ Pattern 2 matched! Product: {product_title}, Season Start: {season_start_date}")
            print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
            return {"product_title": product_title, "season_start_date": season_start_date, "product_link": None}
        
        # Try to find product title/link from various fields
        for i, pattern in enumerate(patterns[2:], start=3):
            product_match = re.search(pattern, message_text)
            if product_match:
                matched_text = product_match.group(1).strip()
                
                # Check if it's a full Slack link (patterns 4 and 6) 
                if i in [4, 6] and matched_text.startswith('<') and matched_text.endswith('>'):
                    product_link = matched_text
                    # Extract title from link for display
                    if '|' in matched_text:
                        product_title = matched_text.split('|')[1].replace('>', '')
                    else:
                        product_title = "Unknown Product"
                    print(f"✅ Pattern {i} matched! Product Link: {product_link}, Title: {product_title}")
                else:
                    # Plain text or title from link (patterns 3, 5, 7, 8 get title directly)
                    product_title = matched_text
                    print(f"✅ Pattern {i} matched! Product: {product_title}")
                break
        
        # Try to find separate season start date
        season_date_patterns = [
            r"Season Start Date:\s*([^\n]+)",
            r"Season Start:\s*([^\n]+)",
            r"Start Date:\s*([^\n]+)"
        ]
        
        for pattern in season_date_patterns:
            season_match = re.search(pattern, message_text)
            if season_match:
                season_start_date = season_match.group(1).strip()
                print(f"✅ Pattern matched! Season Start: {season_start_date}")
                break
        
        print("❌ No season start info found, using fallback")
        print("=== END EXTRACT SEASON START INFO DEBUG ===\n")
        return {"product_title": product_title, "season_start_date": season_start_date, "product_link": product_link} 