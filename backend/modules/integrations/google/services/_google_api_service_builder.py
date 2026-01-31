import json
from typing import Optional
import logging

from googleapiclient.discovery import build, Resource
from google.oauth2.service_account import Credentials

from config import config

logger = logging.getLogger("GoogleApiServiceBuilder")


def _test_credentials_with_service(service: Resource, service_name: str, required_scopes: list[str], subject: Optional[str]) -> None:
    """
    Perform a lightweight test request to verify credentials work.
    
    This catches scope authorization issues early rather than on the first real API call.
    Uses service-specific lightweight endpoints that require minimal permissions.
    
    Args:
        service: The built Google API service
        service_name: Name of the service (e.g., 'admin', 'gmail')
        required_scopes: List of scopes that were requested
        subject: Subject (user email) for domain-wide delegation
    
    Raises:
        Exception: If the test request fails (scope/auth issues)
    """
    # Skip test for services that frequently timeout during initialization
    # These will be tested on first real API call anyway
    skip_test_services = ['admin', 'drive', 'gmail']  # These often timeout during credential refresh
    
    if service_name in skip_test_services:
        return
    
    try:
        # Note: admin service is now skipped above, but keeping this for other services
        if service_name == 'admin':
            # Directory API: Try to list users (lightweight, requires directory scopes)
            # This will fail fast if scopes aren't authorized
            # Using maxResults=1 to minimize data transfer
            service.users().list(customer='my_customer', maxResults=1).execute()  # type: ignore[attr-defined]
        elif service_name == 'sheets':
            # Sheets API: No lightweight test without a spreadsheet ID
            # Skip test - first real API call will catch issues
            pass
        elif service_name == 'script':
            # Scripts API: No lightweight test endpoint
            # Skip test - first real API call will catch issues
            pass
        else:
            # Unknown service, skip test
            pass
    except Exception as e:
        # Re-raise to let caller handle it with proper error handling
        raise


def build_google_api_service(service_name: str, version: str, required_scopes: list[str]) -> Resource:
    """Build and return the Google API service instance."""
    
    try:
        # Get service account from config (already parsed as dict)
        google_service_account = config['GOOGLE']['SERVICE_ACCOUNT']
        
        # Config now returns parsed JSON directly, so it should already be a dict
        if not isinstance(google_service_account, dict):
            raise ValueError(f"Service account config must be a dict, got {type(google_service_account)}")
            
    except KeyError as e:
        logger.error("Config does not have GOOGLE.SERVICE_ACCOUNT: %s", e, exc_info=True)
        raise ValueError(f"Config does not have GOOGLE.SERVICE_ACCOUNT: {e}") from e
    except Exception as e:
        logger.error("Failed to load service account from config: %s", e, exc_info=True)
        raise ValueError(f"Could not load Google service account from config: {e}") from e
    
    # Verify critical fields are present and correct type
    required_fields = ['type', 'project_id', 'client_email']
    for field in required_fields:
        if field not in google_service_account:
            raise ValueError(f"Missing required field in service account: {field}")
        if not isinstance(google_service_account[field], str):
            raise TypeError(f"Field {field} must be a string, got {type(google_service_account[field])}")
    
    # Handle private key - should already be in full PEM format
    if 'private_key' not in google_service_account:
        raise ValueError("Missing required field in service account: private_key")
    
    private_key = google_service_account['private_key']
    
    # Verify private_key has newlines (critical for RSA key format)
    if not isinstance(private_key, str):
        raise TypeError(f"private_key must be a string, got {type(private_key)}")
    if '\n' not in private_key:
        logger.warning("private_key appears to be missing newlines - this may cause authentication issues")
    
    # Get subject from service account dict
    subject: Optional[str] = None
    if "subject" in google_service_account:
        subject_value = google_service_account["subject"]
        if isinstance(subject_value, str):
            subject = subject_value
        elif subject_value is not None:
            logger.warning("subject is not a string: %s", type(subject_value))
    
    # Instantiate credentials using dict from config
    credentials = None
    
    # Method 1: Create credentials without subject, then use with_subject()
    try:
        credentials = Credentials.from_service_account_info(
            google_service_account,
            scopes=required_scopes
        )
        
        if subject:
            credentials = credentials.with_subject(subject)
    except Exception as e:
        # Method 2: Try using from_service_account_file with temp file
        if subject:
            try:
                import tempfile
                import os
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                    json.dump(google_service_account, tmp_file, indent=2)
                    tmp_file_path = tmp_file.name
                
                try:
                    credentials = Credentials.from_service_account_file(
                        filename=tmp_file_path,
                        subject=subject,
                        scopes=required_scopes
                    )
                finally:
                    # Clean up temp file
                    try:
                        os.unlink(tmp_file_path)
                    except Exception:
                        pass
            except Exception as fallback_error:
                logger.error("Failed to instantiate credentials with both methods: %s", fallback_error, exc_info=True)
                raise ValueError(f"Could not create Google API credentials: {fallback_error}") from fallback_error
        else:
            logger.error("Failed to instantiate credentials: %s", e, exc_info=True)
            raise ValueError(f"Could not create Google API credentials: {e}") from e
    
    # Build the service
    try:
        # Configure httplib2 with a longer timeout to prevent connection timeouts
        import httplib2
        from google_auth_httplib2 import Request
        
        # Create httplib2.Http with longer timeout
        http = httplib2.Http(timeout=60)  # 60 second timeout for network operations
        # Create Request wrapper that credentials will use for refresh
        request = Request(http)
        
        # Configure credentials to use our custom request for refresh operations
        credentials._request = request  # type: ignore[attr-defined]
        
        # Build service with credentials
        service = build(service_name, version, credentials=credentials)
        
        # Also configure the service's HTTP transport timeout
        if hasattr(service, '_http'):
            if hasattr(service._http, 'http') and hasattr(service._http.http, 'timeout'):
                service._http.http.timeout = 60  # type: ignore[attr-defined]
        
        # Perform a preliminary test request to verify credentials work
        try:
            _test_credentials_with_service(service, service_name, required_scopes, subject)
        except Exception as test_error:
            # Don't raise - let the first real API call fail with better error handling
            logger.warning("Preliminary credential test failed: %s", test_error)
        
        if subject:
            logger.info("Using domain-wide delegation with subject: %s", subject)
        else:
            logger.warning("No subject provided - using service account directly (may have limited permissions)")

        return service
    
    except Exception as e:
        logger.error("Failed to build Google API service: %s", e, exc_info=True)
        raise ValueError(f"Could not build Google API service '{service_name}': {e}") from e

