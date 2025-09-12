"""
Webhooks Service

Handles incoming webhooks from external services. Currently supports Shopify product 
change webhooks and determines when products have sold out to trigger waitlist form updates.
"""

import json
import os
import re
import hmac
import hashlib
import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class WebhooksService:
    """Service for processing webhooks from external services. Currently handles Shopify product webhooks and sellout detection."""
    
    def __init__(self):
        self.webhook_secret = os.getenv("SHOPIFY_WEBHOOK_SECRET")
        self.gas_waitlist_form_web_app_url = os.getenv("GAS_WAITLIST_FORM_WEB_APP_URL")
        self.shopify_store = os.getenv("SHOPIFY_STORE", "09fe59-3.myshopify.com")
    
    def verify_webhook_signature(self, body: bytes, signature: str) -> bool:
        """Verify Shopify webhook signature for security"""
        if not self.webhook_secret:
            logger.warning("Missing webhook secret - skipping verification")
            return True
            
        if not signature:
            logger.warning("Missing webhook signature - rejecting request") 
            return False
            
        try:
            expected = hmac.new(
                self.webhook_secret.encode('utf-8'),
                body,
                hashlib.sha256
            ).digest()
            
            import base64
            received = base64.b64decode(signature)
            
            return hmac.compare_digest(expected, received)
            
        except Exception as e:
            logger.error(f"Webhook signature verification failed: {e}")
            return False
    
    def handle_shopify_webhook(self, headers: Dict[str, str], body: bytes) -> Dict[str, Any]:
        """Main handler for Shopify webhooks"""
        if not self.is_product_update(headers):
            return {"success": True, "message": "Not a product update webhook"}
        
        return self.handle_shopify_product_update_webhook(body)
    
    def is_product_update(self, headers: Dict[str, str]) -> bool:
        """Check if webhook is a product update from headers"""
        topic = headers.get("x-shopify-topic", "")
        return topic == "products/update"
    
    def handle_shopify_product_update_webhook(self, body: bytes) -> Dict[str, Any]:
        """Handle Shopify product update webhook"""
        try:
            product_data = json.loads(body.decode('utf-8'))
            
            if not self.product_has_zero_inventory(product_data):
                return {"success": True, "message": "Product still has inventory"}
            
            deconstructed_product_json = self.parse_shopify_webhook_for_waitlist_form(product_data)
            result = self.send_to_waitlist_form_gas(deconstructed_product_json)
            
            return {
                "success": True,
                "message": "Product sold out, waitlist form updated",
                "parsed_product": deconstructed_product_json,
                "waitlist_result": result
            }
            
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in webhook body: {e}")
            return {"success": False, "error": "Invalid JSON payload"}
        except Exception as e:
            logger.error(f"Error processing product update webhook: {e}")
            return {"success": False, "error": str(e)}
    
    def product_has_zero_inventory(self, product_data: Dict[str, Any]) -> bool:
        """Check if all variants have zero inventory"""
        variants = product_data.get("variants", [])
        if not variants:
            return False
            
        for variant in variants:
            inventory_quantity = variant.get("inventory_quantity", 0)
            if inventory_quantity > 0:
                return False
        
        return True
    
    def parse_shopify_webhook_for_waitlist_form(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Shopify webhook product data for waitlist form"""
        title = product_data.get("title", "")
        product_id = product_data.get("id", "")
        
        store_name = self.shopify_store.split('.')[0]
        product_url = f"https://admin.shopify.com/store/{store_name}/products/{product_id}"
        
        working_title = title.strip()
        working_title = re.sub(r'\bbig apple\b', '', working_title, flags=re.IGNORECASE).strip()
        
        from datetime import datetime
        current_year = datetime.now().year
        
        working_title = re.sub(r'\b(fall|spring|summer|winter)\b', '', working_title, flags=re.IGNORECASE)
        
        year_patterns = [
            str(current_year), str(current_year + 1), str(current_year - 1),
            str(current_year % 100), str((current_year + 1) % 100), str((current_year - 1) % 100)
        ]
        for year in year_patterns:
            working_title = re.sub(r'\b' + re.escape(year) + r'\b', '', working_title, flags=re.IGNORECASE)
        
        working_title = self._clean_title_formatting(working_title)
        
        result = {
            "product_url": product_url,
            "sport": None,
            "day": None, 
            "division": None,
            "other_identifier": None
        }
        
        # Multi-sport pattern: "Kickball and Dodgeball"
        multi_sport_pattern = r'\b(kickball|dodgeball|pickleball|bowling)\s+and\s+(kickball|dodgeball|pickleball|bowling)\b'
        multi_sport_match = re.search(multi_sport_pattern, working_title, re.IGNORECASE)
        
        if multi_sport_match:
            sport1, sport2 = multi_sport_match.groups()
            result["sport"] = f"{sport1.title()} and {sport2.title()}"
            working_title = working_title[:multi_sport_match.start()] + working_title[multi_sport_match.end():]
            working_title = self._clean_title_formatting(working_title)
        else:
            sports = ["dodgeball", "kickball", "pickleball", "bowling"]
            sport_matches = []
            
            for sport in sports:
                matches = list(re.finditer(r'\b' + re.escape(sport) + r'\b', working_title, re.IGNORECASE))
                sport_matches.extend([(match, sport) for match in matches])
            
            if sport_matches:
                sport_matches.sort(key=lambda x: x[0].start())
                
                if len(sport_matches) == 1:
                    match, sport = sport_matches[0]
                    result["sport"] = sport.title()
                    working_title = working_title[:match.start()] + working_title[match.end():]
                else:
                    first_match = sport_matches[0][0]
                    last_match = sport_matches[-1][0]
                    result["sport"] = sport_matches[0][1].title()
                    working_title = working_title[:first_match.start()] + working_title[last_match.end():]
                
                working_title = self._clean_title_formatting(working_title)
            else:
                result["other_identifier"] = working_title if working_title else None
                return result
        
        days = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
        day_matches = []
        
        for day in days:
            matches = list(re.finditer(r'\b' + re.escape(day) + r'\b', working_title, re.IGNORECASE))
            day_matches.extend([(match, day) for match in matches])
        
        if day_matches:
            day_matches.sort(key=lambda x: x[0].start())
            
            if len(day_matches) == 1:
                match, day = day_matches[0]
                result["day"] = day.title()
                working_title = working_title[:match.start()] + working_title[match.end():]
            else:
                first_match = day_matches[0][0]
                last_match = day_matches[-1][0]
                result["day"] = day_matches[0][1].title()
                working_title = working_title[:first_match.start()] + working_title[last_match.end():]
            
            working_title = self._clean_title_formatting(working_title)
        else:
            result["other_identifier"] = working_title if working_title else None
            return result
        
        # Check wtnb+ before wtnb to avoid partial matches
        divisions = ["wtnb+", "wtnb", "open"]
        
        for division in divisions:
            if division == "wtnb+":
                # Special regex for wtnb+ since + is not a word character
                pattern = r'\bwtnb\+'
            else:
                pattern = r'\b' + re.escape(division) + r'\b'
            match = re.search(pattern, working_title, re.IGNORECASE)
            if match:
                if division == "open":
                    result["division"] = "Open"
                elif division == "wtnb+":
                    result["division"] = "WTNB+"
                else:
                    result["division"] = division.lower()
                
                working_title = working_title[:match.start()] + working_title[match.end():]
                working_title = re.sub(r'\bdivision\b', '', working_title, flags=re.IGNORECASE)
                working_title = self._clean_title_formatting(working_title)
                break
        
        if working_title and re.search(r'[a-zA-Z0-9]', working_title):
            result["other_identifier"] = working_title
        
        return result
    
    def _clean_title_formatting(self, text: str) -> str:
        """Clean up title formatting issues like double hyphens, stray parentheses, etc."""
        if not text:
            return ""
        
        # Remove double hyphens with optional spaces: -- or - - 
        text = re.sub(r'\s*-\s*-\s*', ' - ', text)
        # Remove stray opening/closing parentheses without pairs
        text = re.sub(r'\([^)]*$', '', text)
        text = re.sub(r'^[^(]*\)', '', text)
        # Clean up multiple spaces and hyphen sequences
        text = re.sub(r'\s+', ' ', text)
        text = text.strip(' -')
        text = re.sub(r'(\s*-\s*){2,}', ' - ', text)
        
        return text.strip()
    
    def send_to_waitlist_form_gas(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send product data to Google Apps Script waitlist form"""
        if not self.gas_waitlist_form_web_app_url:
            logger.error("GAS_WAITLIST_FORM_WEB_APP_URL not configured")
            return {"success": False, "error": "Waitlist form URL not configured"}
        
        try:
            response = requests.post(
                self.gas_waitlist_form_web_app_url,
                json=product_data,
                timeout=30
            )
            
            if response.status_code < 400:
                logger.info(f"Successfully sent product data to waitlist form: {product_data}")
                return {"success": True, "response": response.text}
            else:
                logger.error(f"Failed to send to waitlist form. Status: {response.status_code}, Response: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.RequestException as e:
            logger.error(f"Request to waitlist form failed: {e}")
            return {"success": False, "error": str(e)}