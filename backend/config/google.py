"""Google API Configuration."""

import os
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GoogleConfig:
    """Configuration for Google API integrations."""
    
    def __init__(self, environment: str = "dev"):
        self.environment = environment
        
        service_account_file = os.getenv(
            "GOOGLE_SERVICE_ACCOUNT_FILE",
            "google-service-account.json"
        )
        
        backend_dir = Path(__file__).parent.parent
        self.service_account_path = backend_dir / service_account_file
        
        if not self.service_account_path.exists():
            logger.warning(
                f"Google service account file not found at: {self.service_account_path}. "
                "Google Sheets integration will not work until credentials are configured."
            )
        
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]
    
    @property
    def credentials_exist(self) -> bool:
        """Check if service account credentials file exists."""
        return self.service_account_path.exists()

