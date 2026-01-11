#!/usr/bin/env python3
"""
AWS Lambda remote code fetcher.
Downloads Lambda function code from AWS.
"""

import subprocess
import zipfile
import urllib.request
from pathlib import Path
from typing import Optional

# Handle both module and standalone execution
try:
    from .remote_fetcher import RemoteFetcher
except ImportError:
    # Standalone execution - add parent directory to path
    import sys
    script_dir = Path(__file__).parent
    repo_root = script_dir.parent.parent
    sys.path.insert(0, str(repo_root))
    
    from scripts.remote_sync.remote_fetcher import RemoteFetcher


class AWSLambdaFetcher(RemoteFetcher):
    """Fetcher for AWS Lambda functions."""
    
    def __init__(self, region: str = "us-east-1"):
        """
        Initialize AWS Lambda fetcher.
        
        Args:
            region: AWS region (default: us-east-1)
        """
        self.region = region
    
    def check_credentials(self) -> bool:
        """Check if AWS credentials are configured."""
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def fetch(self, function_name: str, temp_dir: Path) -> Path:
        """
        Fetch Lambda function code from AWS.
        
        Args:
            function_name: Name of the Lambda function
            temp_dir: Temporary directory to store fetched code
        
        Returns:
            Path to directory containing unzipped function code
        
        Raises:
            RuntimeError: If fetch fails, with detailed error messages
        """
        # Create temp directory for this function
        function_temp = temp_dir / function_name
        function_temp.mkdir(parents=True, exist_ok=True)
        
        # Get function code location
        try:
            result = subprocess.run(
                [
                    "aws", "lambda", "get-function",
                    "--function-name", function_name,
                    "--region", self.region
                ],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.strip() if result.stderr else result.stdout.strip() if result.stdout else ""
                if not error_msg:
                    error_msg = f"Command failed with exit code {result.returncode}"
                
                # Check for authentication failures
                error_lower = error_msg.lower()
                if any(phrase in error_lower for phrase in [
                    'unable to locate credentials',
                    'unable to find credentials',
                    'not authorized',
                    'unauthorized',
                    'authentication',
                    'invalid credentials',
                    'expired token',
                    'security token'
                ]):
                    raise RuntimeError(
                        f"❌ Authentication failure: {error_msg}\n"
                        "   Please run: aws configure (or aws sso login / assume bars)"
                    )
                else:
                    raise RuntimeError(f"❌ Failed to get Lambda function: {error_msg}")
            
            # Parse JSON response
            import json
            function_data = json.loads(result.stdout)
            code_location = function_data['Code']['Location']
            
            if not code_location:
                raise RuntimeError("No code location returned from AWS")
            
            # Download ZIP file
            zip_path = function_temp / f"{function_name}.zip"
            urllib.request.urlretrieve(code_location, zip_path)
            
            # Unzip
            with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                zip_ref.extractall(function_temp)
            
            # Remove ZIP file
            zip_path.unlink()
            
            return function_temp
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("AWS CLI command timed out")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Failed to parse AWS CLI response: {e}")
        except Exception as e:
            if isinstance(e, RuntimeError):
                raise
            raise RuntimeError(f"❌ Error pulling AWS function: {e}")
