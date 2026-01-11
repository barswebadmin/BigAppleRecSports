#!/usr/bin/env python3
"""
Google Apps Script remote code fetcher.
Uses clasp CLI to pull code from Google Apps Script.
Supports custom clasp_helpers.sh pull scripts for projects like waitlist-script-comprehensive.
"""

import json
import subprocess
import shutil
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


class GASFetcher(RemoteFetcher):
    """Fetcher for Google Apps Script projects."""
    
    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize GAS fetcher.
        
        Args:
            project_root: Root directory of GAS projects (default: auto-detect)
        """
        self.project_root = project_root or Path(__file__).parent.parent.parent / "GoogleAppsScripts"
    
    def _has_custom_pull_script(self, project_dir: Path) -> bool:
        """
        Check if project has a custom clasp_helpers.sh with pull function.
        
        Args:
            project_dir: Local GAS project directory
        
        Returns:
            True if custom pull script exists and has pull function
        """
        clasp_helpers = project_dir / 'clasp_helpers.sh'
        if not clasp_helpers.exists():
            return False
        
        try:
            content = clasp_helpers.read_text()
            # Check if it has a pull function (not just delegating to shared script)
            if 'pull()' in content and 'exec bash' not in content.split('pull()')[1].split('}')[0]:
                return True
        except Exception:
            pass
        
        return False
    
    def check_credentials(self) -> bool:
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
            
            # Check if logged in
            result = subprocess.run(
                ["clasp", "login", "--status"],
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False
    
    def fetch(self, project_name: str, temp_dir: Path) -> Path:
        """
        Fetch GAS project code using clasp pull.
        Supports custom clasp_helpers.sh pull scripts for projects like waitlist-script-comprehensive.
        
        Args:
            project_name: Name of the GAS project
            temp_dir: Temporary directory to store fetched code
        
        Returns:
            Path to directory containing fetched code
        
        Raises:
            ValueError: If project directory or .clasp.json not found
            RuntimeError: If fetch fails, with detailed error messages
        """
        project_dir = self.project_root / "projects" / project_name
        
        if not project_dir.exists():
            raise ValueError(f"Project directory not found: {project_dir}")
        
        clasp_json = project_dir / ".clasp.json"
        if not clasp_json.exists():
            raise ValueError(f".clasp.json not found in {project_dir}")
        
        # Check for custom pull script (e.g., waitlist-script-comprehensive)
        if self._has_custom_pull_script(project_dir):
            # Run custom pull script (creates pull_validation/ directory)
            try:
                result = subprocess.run(
                    ['bash', str(project_dir / 'clasp_helpers.sh'), 'pull'],
                    cwd=project_dir,
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=120
                )
                
                # Check if pull_validation directory was created
                pull_validation = project_dir / 'pull_validation'
                if pull_validation.exists() and pull_validation.is_dir():
                    # Copy pull_validation to temp_dir for comparison
                    extract_dir = temp_dir / project_name
                    extract_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Files are directly in pull_validation/ (e.g., pull_validation/config/constants.js)
                    # We want to compare local src/ with remote pull_validation/
                    # So copy pull_validation contents to extract_dir/src/
                    extract_src = extract_dir / 'src'
                    extract_src.mkdir(parents=True, exist_ok=True)
                    
                    # Copy all files from pull_validation to extract_dir/src/
                    for item in pull_validation.iterdir():
                        if item.is_file():
                            shutil.copy2(item, extract_src / item.name)
                        elif item.is_dir():
                            shutil.copytree(item, extract_src / item.name, dirs_exist_ok=True)
                    
                    # Clean up pull_validation directory (created by custom pull script)
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
        # Read rootDir from .clasp.json
        try:
            with open(clasp_json, 'r') as f:
                clasp_config = json.load(f)
            root_dir = clasp_config.get('rootDir', 'src')
        except Exception:
            root_dir = 'src'
        
        # Create temp directory for clasp operations
        clasp_temp = temp_dir / project_name
        clasp_temp.mkdir(parents=True, exist_ok=True)
        
        # Copy .clasp.json with normalized rootDir
        self._normalize_clasp_json(clasp_json, clasp_temp / ".clasp.json")
        
        # Run clasp pull
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
            
            # Verify rootDir was pulled (or Code.js for root-level projects)
            src_dir = clasp_temp / root_dir
            code_js = clasp_temp / "Code.js"
            if not src_dir.exists() and not code_js.exists():
                raise RuntimeError(f"Root directory '{root_dir}' or Code.js not found after pull")
            
            return clasp_temp
        
        except subprocess.TimeoutExpired:
            raise RuntimeError("clasp pull timed out")
    
    def _normalize_clasp_json(self, source: Path, dest: Path) -> None:
        """Normalize .clasp.json rootDir to '.' for temp directories."""
        import json
        
        with open(source, 'r') as f:
            data = json.load(f)
        
        data['rootDir'] = '.'
        
        with open(dest, 'w') as f:
            json.dump(data, f, indent=2)
