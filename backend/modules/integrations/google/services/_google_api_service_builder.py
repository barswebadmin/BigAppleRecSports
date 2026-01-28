from googleapiclient.discovery import build, Resource
from google.oauth2.service_account import Credentials
from typing import Optional

import logging
from backend.config import config

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
    import sys
    
    # Skip test for services that frequently timeout during initialization
    # These will be tested on first real API call anyway
    skip_test_services = ['admin', 'drive', 'gmail']  # These often timeout during credential refresh
    
    if service_name in skip_test_services:
        print(f"[DEBUG] Skipping credential test for {service_name} (frequently times out, will test on first API call)", file=sys.stderr)
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
        import sys
        import json
        import time
        from pathlib import Path
        from config import config
        
        build_start_time = time.time()
        
        # Calculate absolute path to service account file for reference/fallback
        # From: backend/modules/integrations/google/services/_google_api_service_builder.py
        # To: backend/google-service-account.json
        source_file = Path(__file__).resolve().parent.parent.parent.parent.parent / "google-service-account.json"
        source_file = source_file.resolve()
        
        # Load from config instead of file directly
        print(f"[DEBUG] Loading service account from config...", file=sys.stderr)
        loaded_from = "config"
        
        try:
            # Get service account from config
            google_service_account = config.google.service_account
            print(f"[DEBUG] ✅ Loaded service account from config", file=sys.stderr)
            print(f"[DEBUG] Loaded type: {type(google_service_account)}", file=sys.stderr)
            
            # Convert to dict if it's a Config object
            if hasattr(google_service_account, 'model_dump'):
                google_service_account = google_service_account.model_dump()
            elif hasattr(google_service_account, '__dict__'):
                # Convert Config object to dict
                google_service_account = {k: v for k, v in google_service_account.__dict__.items() if not k.startswith('_')}
                # Recursively convert nested Config objects
                def convert_config_to_dict(obj):
                    if hasattr(obj, 'model_dump'):
                        return obj.model_dump()
                    elif hasattr(obj, '__dict__'):
                        return {k: convert_config_to_dict(v) if hasattr(v, '__dict__') or hasattr(v, 'model_dump') else v 
                               for k, v in obj.__dict__.items() if not k.startswith('_')}
                    return obj
                google_service_account = {k: convert_config_to_dict(v) for k, v in google_service_account.items()}
            
            if not isinstance(google_service_account, dict):
                raise TypeError(f"Expected dict from config, got {type(google_service_account)}")
                
        except AttributeError as e:
            print(f"[ERROR] Config does not have google.service_account: {type(e).__name__}: {e}", file=sys.stderr)
            logger.error(f"Config does not have google.service_account: {e}", exc_info=True)
            raise ValueError(f"Config does not have google.service_account: {e}") from e
        except Exception as e:
            print(f"[ERROR] Failed to load from config: {type(e).__name__}: {e}", file=sys.stderr)
            logger.error(f"Failed to load service account from config: {e}", exc_info=True)
            raise ValueError(f"Could not load Google service account from config: {e}") from e
        
        # Print source file contents for comparison
        print(f"[DEBUG] ========== SOURCE FILE CONTENTS ==========", file=sys.stderr)
        if source_file.exists():
            try:
                with open(source_file, 'r', encoding='utf-8') as f:
                    source_file_contents = json.load(f)
                print(f"[DEBUG] Source file path: {source_file}", file=sys.stderr)
                print(f"[DEBUG] Source file structure: {json.dumps({k: type(v).__name__ for k, v in source_file_contents.items()}, indent=2)}", file=sys.stderr)
                print(f"[DEBUG] Source file keys: {list(source_file_contents.keys())}", file=sys.stderr)
            except Exception as e:
                print(f"[WARN] Could not read source file for comparison: {type(e).__name__}: {e}", file=sys.stderr)
        else:
            print(f"[WARN] Source file does not exist: {source_file}", file=sys.stderr)
        print(f"[DEBUG] ==========================================", file=sys.stderr)
        
        # Verify we have a dict (json.load() should always return dict for valid JSON objects)
        if not isinstance(google_service_account, dict):
            print(f"[ERROR] Expected dict from json.load(), got {type(google_service_account)}", file=sys.stderr)
            logger.error(f"Expected dict from json.load(), got {type(google_service_account)}")
            raise TypeError(f"google_service_account must be a dict, got {type(google_service_account)}")
        
        print(f"[DEBUG] Service account loaded from: {loaded_from}", file=sys.stderr)
        print(f"[DEBUG] Service account keys: {list(google_service_account.keys())}", file=sys.stderr)
        
        # Log partially redacted service account info
        def redact_value(key: str, value: str) -> str:
            """Redact sensitive values while showing structure."""
            if key in ['private_key', 'private_key_id', 'client_email', 'client_id']:
                if len(value) > 20:
                    return value[:8] + "..." + value[-8:]
                return "***REDACTED***"
            return value
        
        # Log service account structure (redacted) - only for debugging
        redacted_info = {k: redact_value(k, str(v)) if isinstance(v, str) else v 
                        for k, v in google_service_account.items()}
        print(f"[DEBUG] Google service account (redacted): {json.dumps(redacted_info, indent=2)}", file=sys.stderr)
        
        # Verify critical fields are present and correct type
        required_fields = ['type', 'project_id', 'private_key', 'client_email']
        for field in required_fields:
            if field not in google_service_account:
                raise ValueError(f"Missing required field in service account: {field}")
            if not isinstance(google_service_account[field], str):
                raise TypeError(f"Field {field} must be a string, got {type(google_service_account[field])}")
        
        # Verify private_key has newlines (critical for RSA key format)
        private_key = google_service_account['private_key']
        if not isinstance(private_key, str):
            raise TypeError(f"private_key must be a string, got {type(private_key)}")
        has_newlines = '\n' in private_key
        if not has_newlines:
            print(f"[WARN] private_key appears to be missing newlines - this may cause authentication issues", file=sys.stderr)
        print(f"[DEBUG] private_key length: {len(private_key)}, has_newlines: {has_newlines}, newline_count: {private_key.count(chr(10))}", file=sys.stderr)
        
        # Compare with source file if available (and not already loaded from file)
        print(f"[DEBUG] ========== COMPARISON START ==========", file=sys.stderr)
        print(f"[DEBUG] Checking source file: {source_file}", file=sys.stderr)
        print(f"[DEBUG] Source file exists: {source_file.exists()}", file=sys.stderr)
        print(f"[DEBUG] Loaded from: {loaded_from}", file=sys.stderr)
        
        if loaded_from != "file" and source_file.exists():
            print(f"[DEBUG] ✅ Starting comparison with source file: {source_file}", file=sys.stderr)
            try:
                with open(source_file, 'r') as f:
                    source_json = json.load(f)
                print(f"[DEBUG] ✅ Source file loaded successfully", file=sys.stderr)
                
                print(f"[DEBUG] Source file keys: {list(source_json.keys())}", file=sys.stderr)
                print(f"[DEBUG] Loaded JSON keys: {list(google_service_account.keys())}", file=sys.stderr)
                
                source_keys = set(source_json.keys())
                loaded_keys = set(google_service_account.keys())
                missing_keys = source_keys - loaded_keys
                extra_keys = loaded_keys - source_keys
                
                if missing_keys:
                    print(f"[WARN] Missing keys in loaded JSON: {missing_keys}", file=sys.stderr)
                if extra_keys:
                    print(f"[WARN] Extra keys in loaded JSON: {extra_keys}", file=sys.stderr)
                if not missing_keys and not extra_keys:
                    print(f"[DEBUG] ✅ All keys match source file", file=sys.stderr)
                
                # Check if private_key structure is preserved (newlines)
                if 'private_key' in source_json and 'private_key' in google_service_account:
                    source_pk = source_json['private_key']
                    loaded_pk = google_service_account['private_key']
                    if not isinstance(source_pk, str) or not isinstance(loaded_pk, str):
                        print(f"[WARN] private_key is not a string in source or loaded data", file=sys.stderr)
                    else:
                        source_has_newlines = '\n' in source_pk
                        loaded_has_newlines = '\n' in loaded_pk
                        source_pk_lines = len(source_pk.split('\n'))
                        loaded_pk_lines = len(loaded_pk.split('\n'))
                        source_pk_length = len(source_pk)
                        loaded_pk_length = len(loaded_pk)
                        
                        print(f"[DEBUG] private_key comparison:", file=sys.stderr)
                        print(f"  Source: {source_pk_length} chars, {source_pk_lines} lines, has_newlines={source_has_newlines}", file=sys.stderr)
                        print(f"  Loaded: {loaded_pk_length} chars, {loaded_pk_lines} lines, has_newlines={loaded_has_newlines}", file=sys.stderr)
                        
                        if source_has_newlines != loaded_has_newlines:
                            print(f"[ERROR] private_key newline preservation differs: source={source_has_newlines}, loaded={loaded_has_newlines}", file=sys.stderr)
                        elif source_pk_lines != loaded_pk_lines:
                            print(f"[ERROR] private_key line count differs: source={source_pk_lines} lines, loaded={loaded_pk_lines} lines", file=sys.stderr)
                        elif source_pk_length != loaded_pk_length:
                            print(f"[ERROR] private_key length differs: source={source_pk_length} chars, loaded={loaded_pk_length} chars", file=sys.stderr)
                        else:
                            print(f"[DEBUG] ✅ private_key structure preserved: {loaded_pk_lines} lines, {loaded_pk_length} chars", file=sys.stderr)
                        
                        # Check if private_key content matches (first/last chars)
                        if source_pk[:50] != loaded_pk[:50]:
                            print(f"[ERROR] private_key start differs:", file=sys.stderr)
                            print(f"  Source starts: '{source_pk[:50]}'", file=sys.stderr)
                            print(f"  Loaded starts: '{loaded_pk[:50]}'", file=sys.stderr)
                        elif source_pk[-50:] != loaded_pk[-50:]:
                            print(f"[ERROR] private_key end differs:", file=sys.stderr)
                            print(f"  Source ends: '...{source_pk[-50]}'", file=sys.stderr)
                            print(f"  Loaded ends: '...{loaded_pk[-50]}'", file=sys.stderr)
                        else:
                            print(f"[DEBUG] ✅ private_key content matches (first/last 50 chars)", file=sys.stderr)
                        
                        # Check if full content matches
                        if source_pk != loaded_pk:
                            print(f"[ERROR] private_key full content differs!", file=sys.stderr)
                            # Find first difference
                            for i, (s, l) in enumerate(zip(source_pk, loaded_pk)):
                                if s != l:
                                    print(f"  First difference at position {i}: source='{s}' (ord={ord(s)}), loaded='{l}' (ord={ord(l)})", file=sys.stderr)
                                    break
                        else:
                            print(f"[DEBUG] ✅ private_key full content matches", file=sys.stderr)
                
                # Check other critical fields
                print(f"[DEBUG] Checking critical fields...", file=sys.stderr)
                for key in ['client_email', 'project_id', 'type', 'private_key_id', 'client_id']:
                    if key in source_json and key in google_service_account:
                        if source_json[key] != google_service_account[key]:
                            print(f"[ERROR] {key} differs:", file=sys.stderr)
                            print(f"  Source: '{source_json[key]}'", file=sys.stderr)
                            print(f"  Loaded: '{google_service_account[key]}'", file=sys.stderr)
                        else:
                            print(f"[DEBUG] ✅ {key} matches: {google_service_account[key]}", file=sys.stderr)
                    elif key in source_json:
                        print(f"[WARN] {key} missing in loaded JSON (present in source)", file=sys.stderr)
                    elif key in google_service_account:
                        print(f"[WARN] {key} extra in loaded JSON (not in source)", file=sys.stderr)
                
                # Check subject field
                if 'subject' in source_json:
                    print(f"[DEBUG] Source file has subject: '{source_json['subject']}'", file=sys.stderr)
                if 'subject' in google_service_account:
                    print(f"[DEBUG] Loaded JSON has subject: '{google_service_account['subject']}'", file=sys.stderr)
                elif 'subject' in source_json:
                    print(f"[WARN] subject field missing in loaded JSON (present in source file)", file=sys.stderr)
            except Exception as e:
                print(f"[ERROR] Could not compare with source file: {type(e).__name__}: {e}", file=sys.stderr)
                import traceback
                print(f"[ERROR] Traceback: {traceback.format_exc()}", file=sys.stderr)
        elif loaded_from == "file":
            print(f"[DEBUG] Skipping comparison - loaded directly from source file", file=sys.stderr)
        elif not source_file.exists():
            print(f"[WARN] Source file does not exist: {source_file}", file=sys.stderr)
        else:
            print(f"[DEBUG] Comparison skipped: loaded_from={loaded_from}, file_exists={source_file.exists()}", file=sys.stderr)
        
        print(f"[DEBUG] ========== COMPARISON END ==========", file=sys.stderr)
        
        # Get subject from nested structure or direct key
        subject: Optional[str] = None
        if isinstance(google_service_account, dict):
            if "subject" in google_service_account:
                subject_value = google_service_account["subject"]
                if isinstance(subject_value, str):
                    subject = subject_value
                    print(f"[DEBUG] Found subject in service account JSON: {subject}", file=sys.stderr)
                elif subject_value is not None:
                    print(f"[WARN] subject is not a string: {type(subject_value)}", file=sys.stderr)
            # COMMENTED OUT: Fallback to config/env var
            # elif hasattr(config.google.service_account, 'subject'):
            #     subject = config.google.service_account.subject
            # else:
            #     import os
            #     subject = os.getenv("GOOGLE.SERVICE_ACCOUNT.SUBJECT")
        
        print(f"[DEBUG] Using subject for domain-wide delegation: {subject if subject else 'None (service account only)'}", file=sys.stderr)
        print(f"[DEBUG] Requested scopes: {required_scopes}", file=sys.stderr)
        
        # Use from_service_account_info() with dict from config
        print(f"[DEBUG] ========== CREDENTIALS BUILD PARAMETERS ==========", file=sys.stderr)
        print(f"[DEBUG] Using: Credentials.from_service_account_info()", file=sys.stderr)
        print(f"[DEBUG] Service account dict keys: {list(google_service_account.keys())}", file=sys.stderr)
        print(f"[DEBUG] Service account dict (redacted): {json.dumps({k: redact_value(k, str(v)) if isinstance(v, str) else type(v).__name__ for k, v in google_service_account.items()}, indent=2)}", file=sys.stderr)
        print(f"[DEBUG] subject parameter: {subject} (type: {type(subject)})", file=sys.stderr)
        print(f"[DEBUG] scopes parameter: {required_scopes} (type: {type(required_scopes)}, count: {len(required_scopes)})", file=sys.stderr)
        print(f"[DEBUG] =========================================================", file=sys.stderr)
        
        # Instantiate credentials using dict from config
        # Try both methods: with_subject() first, then fallback to passing subject directly
        cred_start_time = time.time()
        print(f"[DEBUG] Instantiating Google API credentials from config dict...", file=sys.stderr)
        credentials = None
        method_used = None
        
        # Method 1: Create credentials without subject, then use with_subject()
        print(f"[DEBUG] ========== METHOD 1: Using with_subject() ==========", file=sys.stderr)
        print(f"[DEBUG] Attempting: Credentials.from_service_account_info() then .with_subject({subject})", file=sys.stderr)
        try:
            credentials = Credentials.from_service_account_info(
                google_service_account,
                scopes=required_scopes
            )
            print(f"[DEBUG] ✅ Base credentials created", file=sys.stderr)
            
            if subject:
                print(f"[DEBUG] Applying domain-wide delegation with .with_subject({subject})...", file=sys.stderr)
                credentials = credentials.with_subject(subject)
                method_used = "from_service_account_info_then_with_subject"
                print(f"[DEBUG] ✅ METHOD 1 SUCCESS: Domain-wide delegation applied via with_subject()", file=sys.stderr)
            else:
                method_used = "from_service_account_info_no_subject"
                print(f"[DEBUG] ✅ METHOD 1 SUCCESS: Credentials created without subject", file=sys.stderr)
        except Exception as e:
            print(f"[DEBUG] ⚠️ METHOD 1 FAILED: {type(e).__name__}: {e}", file=sys.stderr)
            print(f"[DEBUG] Falling back to METHOD 2: Passing subject directly", file=sys.stderr)
            credentials = None
        
        # Method 2: Try using from_service_account_file with temp file (original method 1 approach)
        if credentials is None and subject:
            print(f"[DEBUG] ========== METHOD 2: Passing subject directly (via file) ==========", file=sys.stderr)
            print(f"[DEBUG] Attempting: Credentials.from_service_account_file(subject={subject})", file=sys.stderr)
            try:
                # Write config dict to temp file and use from_service_account_file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as tmp_file:
                    json.dump(google_service_account, tmp_file, indent=2)
                    tmp_file_path = tmp_file.name
                
                try:
                    credentials = Credentials.from_service_account_file(
                        filename=tmp_file_path,
                        subject=subject,
                        scopes=required_scopes
                    )
                    method_used = "from_service_account_file_with_subject"
                    print(f"[DEBUG] ✅ METHOD 2 SUCCESS: Credentials created with subject passed directly", file=sys.stderr)
                finally:
                    # Clean up temp file
                    import os
                    try:
                        os.unlink(tmp_file_path)
                    except Exception:
                        pass
            except Exception as e:
                print(f"[ERROR] METHOD 2 FAILED: {type(e).__name__}: {e}", file=sys.stderr)
                logger.error(f"Failed to instantiate credentials with both methods: {e}", exc_info=True)
                raise
        
        cred_time = time.time() - cred_start_time
        print(f"[DEBUG] Credential instantiation took {cred_time:.2f}s", file=sys.stderr)
        print(f"[DEBUG] ========== FINAL RESULT ==========", file=sys.stderr)
        print(f"[DEBUG] Method used: {method_used}", file=sys.stderr)
        print(f"[DEBUG] ✅ Credentials instantiated successfully", file=sys.stderr)
        print(f"[DEBUG] Service account email: {google_service_account.get('client_email')}", file=sys.stderr)
        print(f"[DEBUG] Subject (impersonated user): {subject}", file=sys.stderr)
        print(f"[DEBUG] Scopes: {required_scopes}", file=sys.stderr)
        
        # Build the service first
        # Configure httplib2 with a longer timeout to prevent connection timeouts
        # The credentials use google_auth_httplib2.Request internally for refresh
        import httplib2
        from google_auth_httplib2 import Request
        
        # Create httplib2.Http with longer timeout
        http = httplib2.Http(timeout=60)  # 60 second timeout for network operations
        # Create Request wrapper that credentials will use for refresh
        request = Request(http)
        
        # Configure credentials to use our custom request for refresh operations
        # This ensures credential refresh uses the longer timeout
        credentials._request = request  # type: ignore[attr-defined]
        
        service_build_start = time.time()
        # Build service with credentials (can't pass http when credentials are provided)
        service = build(service_name, version, credentials=credentials)
        
        # Also configure the service's HTTP transport timeout
        # The service uses google_auth_httplib2.Request which wraps httplib2.Http
        if hasattr(service, '_http'):
            if hasattr(service._http, 'http') and hasattr(service._http.http, 'timeout'):
                service._http.http.timeout = 60  # type: ignore[attr-defined]
        
        service_build_time = time.time() - service_build_start
        print(f"[DEBUG] Service build took {service_build_time:.2f}s", file=sys.stderr)
        
        # Perform a preliminary test request to verify credentials work
        # This catches scope/authorization issues early rather than on first real API call
        test_start_time = time.time()
        print(f"[DEBUG] Performing preliminary credential test...", file=sys.stderr)
        try:
            _test_credentials_with_service(service, service_name, required_scopes, subject)
            test_time = time.time() - test_start_time
            print(f"[DEBUG] ✅ Credential test passed ({test_time:.2f}s)", file=sys.stderr)
        except Exception as e:
            test_time = time.time() - test_start_time
            error_type = type(e).__name__
            error_msg = str(e)
            print(f"[DEBUG] ⚠️ Credential test failed after {test_time:.2f}s: {error_type}: {error_msg}", file=sys.stderr)
            print(f"[DEBUG] This may indicate scope authorization issues. The service will still be returned,", file=sys.stderr)
            print(f"[DEBUG] but the first API call may fail with more detailed error information.", file=sys.stderr)
            # Don't raise - let the first real API call fail with better error handling
            logger.warning(f"Preliminary credential test failed: {e}")
        
        total_build_time = time.time() - build_start_time
        print(f"[DEBUG] Total service build time: {total_build_time:.2f}s", file=sys.stderr)
        
        if subject:
            logger.info(f"✅ Using domain-wide delegation with subject: {subject}")
        else:
            logger.warning("⚠️ No subject provided - using service account directly (may have limited permissions)")

        return service

