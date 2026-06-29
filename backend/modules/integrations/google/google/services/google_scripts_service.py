

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
import requests

from google.oauth2.service_account import Credentials

from config import config
from modules.integrations.google.services._google_api_service_builder import build_google_api_service
from modules.integrations.google.base_methods import handle_http_errors
from modules.integrations.google.models.google_script_resources import ExecutionInfo


logger = logging.getLogger(__name__)


class GoogleScriptsService():
    def __init__(self):
        
        required_scopes = [
            'https://www.googleapis.com/auth/script.scriptapp',
        ]

        self.service = build_google_api_service('script', 'v1', required_scopes)
        self.required_scopes = required_scopes  # Store for error diagnostics
        self.scripts = self.service.scripts()  # type: ignore[attr-defined]

        self.web_app_url = config.google.web_app.waitlist.url

    @handle_http_errors
    def get_script_executions(
        self,
        script_id: str,
        page_size: int = 50
    ) -> List[ExecutionInfo]:
        """
        Get Apps Script execution logs.
        
        Note: The Apps Script API doesn't provide direct access to execution logs.
        Execution logs must be viewed manually in the Apps Script dashboard.
        This method returns an empty list and logs a message.
        
        Args:
            script_id: The Apps Script project ID
            page_size: Number of executions to retrieve (not used, kept for API compatibility)
        
        Returns:
            Empty list (execution logs require manual check)
        
        Note:
            Check executions manually at:
            https://script.google.com/home/projects/{script_id}/executions
        """
        logger.warning(
            f"Apps Script API does not provide execution logs via API. "
            f"Check manually at: https://script.google.com/home/projects/{script_id}/executions"
        )
        return []
    
    
    def filter_executions_by_time(
        self,
        executions: List[ExecutionInfo],
        start_time: datetime,
        end_time: datetime
    ) -> List[ExecutionInfo]:
        """
        Filter executions by time range.
        
        Args:
            executions: List of ExecutionInfo objects
            start_time: Start of time range
            end_time: End of time range
        
        Returns:
            Filtered list of ExecutionInfo objects
        """
        filtered = []
        for exec_info in executions:
            time_str = exec_info.update_time or exec_info.create_time
            if time_str:
                try:
                    exec_time = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
                    if start_time <= exec_time <= end_time:
                        filtered.append(exec_info)
                except Exception:
                    continue
        return filtered
    

    def send_to_waitlist_form(self, product_data: Dict[str, Any], web_app_url: Optional[str] = None) -> Dict[str, Any]:
        """
        Send product data to Google Apps Script waitlist form web app.
        
        Args:
            product_data: Dictionary containing product information. Expected keys:
                - product_url: URL of the product
                - sport: Sport name
                - day: Day of the week
                - division: Division name
                - other_identifier: Other identifying information
                Or can contain nested 'parsed' dict with these keys
            web_app_url: Optional GAS web app URL. If not provided, uses GAS_WAITLIST_FORM_WEB_APP_URL env var.
        
        Returns:
            Dictionary with 'success' key and optional 'error' or 'response' keys
        
        Example:
            >>> client = GoogleApiClient()
            >>> result = client.send_to_waitlist_form({
            ...     "product_url": "https://example.com/product",
            ...     "sport": "dodgeball",
            ...     "day": "tuesday",
            ...     "division": "open"
            ... })
            >>> print(result["success"])
            True
        """
        
        # Extract parsed data if nested, otherwise use product_data directly
        if "parsed" in product_data:
            parsed = product_data["parsed"]
        else:
            parsed = product_data
        
        # Convert snake_case keys to camelCase for GAS
        camel_case_data = {
            "productUrl": parsed.get("product_url"),
            "sport": parsed.get("sport"),
            "day": parsed.get("day"),
            "division": parsed.get("division"),
            "otherIdentifier": parsed.get("other_identifier")
        }
        
        logger.info(f"Sending product data to waitlist form: {camel_case_data}")
        
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
                        logger.info(f"Successfully sent product data to waitlist form")
                        return {"success": True, "response": response.text}
                except ValueError:
                    # Not JSON response, treat as success
                    logger.info(f"Successfully sent product data to waitlist form")
                    return {"success": True, "response": response.text}
            else:
                logger.error(f"Failed to send to waitlist form. Status: {response.status_code}, Response: {response.text}")
                return {"success": False, "error": f"HTTP {response.status_code}: {response.text}"}
                
        except requests.RequestException as e:
            logger.error(f"Request to waitlist form failed: {e}")
            return {"success": False, "error": str(e)}