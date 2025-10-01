"""
Google Apps Script Client

Handles communication with Google Apps Script web applications.
"""

import logging
import requests
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class GASClient:
    """Client for Google Apps Script integrations"""
    
    def __init__(self, web_app_url: Optional[str]):
        self.web_app_url = web_app_url
    
    def send_to_waitlist_form(self, product_data: Dict[str, Any]) -> Dict[str, Any]:
        """Send product data to Google Apps Script waitlist form"""
        if not self.web_app_url:
            logger.error("GAS_WAITLIST_FORM_WEB_APP_URL not configured")
            return {"success": False, "error": "Waitlist form URL not configured"}
        
        # Convert snake_case keys to camelCase for GAS
        camel_case_data = {
            "productUrl": product_data.get("product_url"),
            "sport": product_data.get("sport"),
            "day": product_data.get("day"),
            "division": product_data.get("division"),
            "otherIdentifier": product_data.get("other_identifier")
        }
        
        try:
            response = requests.post(
                self.web_app_url,
                json=camel_case_data,
                timeout=30
            )
            
            if response.status_code < 400:
                # Check if GAS returned an error in the response body
                try:
                    response_data = response.json()
                    if response_data.get("status") == "error":
                        error_message = response_data.get("message", "Unknown error")
                        if "already exists" in error_message:
                            logger.info(f"Product option already exists in waitlist form: {error_message}")
                            return {"success": False, "error": error_message, "already_exists": True}
                        else:
                            logger.error(f"GAS returned error: {error_message}")
                            return {"success": False, "error": error_message}
                    else:
                        logger.info(f"Successfully sent product data to waitlist form: {product_data}")
                        return {"success": True, "response": response.text}
                except ValueError:
                    # Not JSON response, treat as success
                    logger.info(f"Successfully sent product data to waitlist form: {product_data}")
                    return {"success": True, "response": response.text}
            else:
                logger.error(f"Failed to send to waitlist form. Status: {response.status_code}, Response: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.RequestException as e:
            logger.error(f"Request to waitlist form failed: {e}")
            return {"success": False, "error": str(e)}
