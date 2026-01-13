#!/usr/bin/env python3
"""
All fetch logic for remote code retrieval.
Handles both AWS Lambda and Google Apps Script fetching.
"""

import json
import shutil
import subprocess
import tempfile
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional


def fetch_from_remote(
    remote_origin_type: str,
    project_name: str,
    temp_dir: Path,
    **kwargs
) -> Path:
    """
    Main fetcher dispatcher.
    
    Args:
        remote_origin_type: "google" or "aws"
        project_name: Name of the project/function
        temp_dir: Temporary directory to store fetched code
        **kwargs: Additional arguments (region, project_root, etc.)
    
    Returns:
        Path to directory containing fetched code
    
    Raises:
        ValueError: If remote_origin_type is unknown
        RuntimeError: If fetch fails
    """
    if remote_origin_type == "aws":
        region = kwargs.get("region", "us-east-1")
        return fetch_from_aws(project_name, temp_dir, region=region)
    elif remote_origin_type == "google":
        project_root = kwargs.get("project_root")
        return fetch_from_google(project_name, temp_dir, project_root=project_root)
    else:
        raise ValueError(f"Unknown remote origin type: {remote_origin_type}")


def check_credentials(remote_origin_type: str) -> bool:
    """
    Check credentials for AWS or GAS.
    
    Args:
        remote_origin_type: "google" or "aws"
    
    Returns:
        True if credentials are configured, False otherwise
    """
    if remote_origin_type == "aws":
        return check_aws_credentials()
    elif remote_origin_type == "google":
        return check_google_credentials()
    else:
        return False


def check_aws_credentials() -> bool:
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


def check_google_credentials() -> bool:
    """Check if clasp is installed and authenticated."""
    try:
        result = subprocess.run(
            ["clasp", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode != 0:
            return False
        
        result = subprocess.run(
            ["clasp", "login", "--status"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def fetch_from_aws(function_name: str, temp_dir: Path, region: str = "us-east-1") -> Path:
    """
    Fetch Lambda function from AWS.
    
    Args:
        function_name: Name of the Lambda function
        temp_dir: Temporary directory to store fetched code
        region: AWS region (default: us-east-1)
    
    Returns:
        Path to directory containing unzipped function code
    
    Raises:
        RuntimeError: If fetch fails or credentials not configured
    """
    function_temp = temp_dir / function_name
    function_temp.mkdir(parents=True, exist_ok=True)
    
    try:
        result = subprocess.run(
            [
                "aws", "lambda", "get-function",
                "--function-name", function_name,
                "--region", region
            ],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip() if result.stderr else result.stdout.strip() if result.stdout else ""
            if not error_msg:
                error_msg = f"Command failed with exit code {result.returncode}"
            
            error_lower = error_msg.lower()
            if any(phrase in error_lower for phrase in [
                'unable to locate credentials', 'unable to find credentials',
                'not authorized', 'unauthorized', 'authentication',
                'invalid credentials', 'expired token', 'security token'
            ]):
                raise RuntimeError(
                    f"❌ Authentication failure: {error_msg}\n"
                    "   Please run: aws configure (or aws sso login / assume bars)"
                )
            else:
                raise RuntimeError(f"❌ Failed to get Lambda function: {error_msg}")
        
        function_data = json.loads(result.stdout)
        code_location = function_data['Code']['Location']
        
        if not code_location:
            raise RuntimeError("No code location returned from AWS")
        
        zip_path = function_temp / f"{function_name}.zip"
        urllib.request.urlretrieve(code_location, zip_path)
        
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(function_temp)
        
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


def fetch_from_google(project_name: str, temp_dir: Path, project_root: Optional[Path] = None) -> Path:
    """
    Fetch GAS project from Google.
    
    Args:
        project_name: Name of the GAS project
        temp_dir: Temporary directory to store fetched code
        project_root: Root directory of GAS projects (default: auto-detect)
    
    Returns:
        Path to directory containing fetched code
    
    Raises:
        RuntimeError: If fetch fails or clasp not configured
    """
    # Auto-detect project_root if not provided
    if project_root is None:
        script_dir = Path(__file__).parent
        repo_root = script_dir.parent.parent
        project_root = repo_root / "GoogleAppsScripts"
    
    project_dir = project_root / "projects" / project_name
    
    if not project_dir.exists():
        raise ValueError(f"Project directory not found: {project_dir}")
    
    clasp_json = project_dir / ".clasp.json"
    if not clasp_json.exists():
        raise ValueError(f".clasp.json not found in {project_dir}")
    
    # Check for custom pull script
    clasp_helpers = project_dir / 'clasp_helpers.sh'
    has_custom_pull = False
    if clasp_helpers.exists():
        try:
            content = clasp_helpers.read_text()
            if 'pull()' in content and 'exec bash' not in content.split('pull()')[1].split('}')[0]:
                has_custom_pull = True
        except Exception:
            pass
    
    if has_custom_pull:
        try:
            result = subprocess.run(
                ['bash', str(clasp_helpers), 'pull'],
                cwd=project_dir,
                check=True,
                capture_output=True,
                text=True,
                timeout=120
            )
            
            pull_validation = project_dir / 'pull_validation'
            if pull_validation.exists() and pull_validation.is_dir():
                extract_dir = temp_dir / project_name
                extract_dir.mkdir(parents=True, exist_ok=True)
                
                extract_src = extract_dir / 'src'
                extract_src.mkdir(parents=True, exist_ok=True)
                
                for item in pull_validation.iterdir():
                    if item.is_file():
                        shutil.copy2(item, extract_src / item.name)
                    elif item.is_dir():
                        shutil.copytree(item, extract_src / item.name, dirs_exist_ok=True)
                
                shutil.rmtree(pull_validation, ignore_errors=True)
                return extract_dir
            else:
                raise RuntimeError("pull_validation directory not found after custom pull")
        
        except subprocess.CalledProcessError as e:
            error_msg = e.stderr if e.stderr else e.stdout if e.stdout else str(e)
            raise RuntimeError(f"❌ Failed to run custom pull script: {error_msg}")
        except subprocess.TimeoutExpired:
            raise RuntimeError("Custom pull script timed out")
    
    # Standard clasp pull
    try:
        with open(clasp_json, 'r') as f:
            clasp_config = json.load(f)
        root_dir = clasp_config.get('rootDir', 'src')
    except Exception:
        root_dir = 'src'
    
    clasp_temp = temp_dir / project_name
    clasp_temp.mkdir(parents=True, exist_ok=True)
    
    with open(clasp_json, 'r') as f:
        data = json.load(f)
    data['rootDir'] = '.'
    with open(clasp_temp / ".clasp.json", 'w') as f:
        json.dump(data, f, indent=2)
    
    try:
        result = subprocess.run(
            ["clasp", "pull"],
            cwd=str(clasp_temp),
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode != 0:
            error_msg = result.stderr if result.stderr else result.stdout if result.stdout else str(result)
            raise RuntimeError(f"❌ Failed to pull GAS project: {error_msg}")
        
        src_dir = clasp_temp / root_dir
        code_js = clasp_temp / "Code.js"
        if not src_dir.exists() and not code_js.exists():
            raise RuntimeError(f"Root directory '{root_dir}' or Code.js not found after pull")
        
        return clasp_temp
    
    except subprocess.TimeoutExpired:
        raise RuntimeError("clasp pull timed out")
