#!/usr/bin/env python3
"""Secret detection script for pre-commit hook.

Scans all files in the repository for potential secrets using multiple workers.
Test files show warnings with user prompts, non-test files fail loudly.
"""

import re
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Tuple

try:
    from rich.console import Console
    from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn
    from rich.prompt import Prompt
except ImportError:
    print("❌ Error: rich library not installed. Install with: pip install rich")
    sys.exit(1)


# Secret patterns to detect
SECRET_PATTERNS = [
    # Shopify tokens
    (r'shpat_[a-zA-Z0-9]{32,}', 'Shopify Access Token'),
    # Slack tokens
    (r'xox[baprs]-[a-zA-Z0-9-]{10,}', 'Slack Token'),
    (r'https://hooks\.slack\.com/services/[a-zA-Z0-9/]+', 'Slack Webhook URL'),
    # API keys (common patterns)
    (r'api[_-]?key["\']?\s*[:=]\s*["\']([^"\']{20,})["\']', 'API Key'),
    # Long tokens (but exclude common false positives like UUIDs, hashes in comments)
    (r'(?<![\w-])(?:token|key|secret)["\']?\s*[:=]\s*["\']([a-zA-Z0-9]{32,})["\']', 'Long Token (32+ chars)'),
    # AWS keys
    (r'AKIA[0-9A-Z]{16}', 'AWS Access Key ID'),
    (r'aws[_-]?secret[_-]?access[_-]?key["\']?\s*[:=]\s*["\']([^"\']{20,})["\']', 'AWS Secret Key'),
    # Generic secrets
    (r'secret["\']?\s*[:=]\s*["\']([^"\']{10,})["\']', 'Secret'),
    (r'password["\']?\s*[:=]\s*["\']([^"\']{8,})["\']', 'Password'),
    (r'token["\']?\s*[:=]\s*["\']([^"\']{10,})["\']', 'Token'),
    (r'bearer["\']?\s*[:=]\s*["\']([^"\']{10,})["\']', 'Bearer Token'),
    # Database connection strings
    (r'(?:postgres|mysql|mongodb)://[^"\'\s]+:[^"\'\s]+@', 'Database Connection String'),
    # Private keys
    (r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', 'Private Key'),
]


class SecretFinding:
    """Represents a secret finding in a file."""
    
    def __init__(self, file_path: Path, line_num: int, pattern_name: str, match: str, line_content: str):
        self.file_path = file_path
        self.line_num = line_num
        self.pattern_name = pattern_name
        self.match = match
        self.line_content = line_content.strip()
    
    def is_test_file(self) -> bool:
        """Check if the file is a test file."""
        path_str = str(self.file_path).lower()
        return (
            'test' in path_str or
            self.file_path.name.startswith('test_') or
            self.file_path.name.endswith('_test.py') or
            self.file_path.name.endswith('_test.js') or
            self.file_path.name.endswith('_test.ts') or
            '/tests/' in path_str or
            '/test/' in path_str
        )


def find_repo_root() -> Path:
    """Find the repository root directory."""
    current = Path.cwd()
    while current != current.parent:
        if (current / '.git').exists():
            return current
        current = current.parent
    return Path.cwd()


def should_skip_file(file_path: Path, repo_root: Path) -> bool:
    """Check if a file should be skipped from secret scanning."""
    rel_path = file_path.relative_to(repo_root)
    path_str = str(rel_path).lower()
    
    # Skip common non-code directories
    skip_patterns = [
        '.git/',
        'node_modules/',
        '__pycache__/',
        '.venv/',
        'venv/',
        '.pytest_cache/',
        'build/',
        'dist/',
        '.egg-info/',
        '.mypy_cache/',
        '.ruff_cache/',
        '.clasp_',
        'pull_validation/',
    ]
    
    for pattern in skip_patterns:
        if pattern in path_str:
            return True
    
    # Skip binary files
    if file_path.suffix in ['.pyc', '.pyo', '.so', '.dylib', '.dll', '.exe', '.zip', '.tar', '.gz']:
        return True
    
    # Only scan text files
    text_extensions = ['.py', '.js', '.ts', '.gs', '.sh', '.bash', '.yaml', '.yml', '.json', '.toml', '.md', '.txt', '.env', '.env.example']
    if file_path.suffix not in text_extensions and not file_path.name.startswith('.'):
        return True
    
    return False


def scan_file(file_path: Path, repo_root: Path) -> List[SecretFinding]:
    """Scan a single file for secrets."""
    findings = []
    
    if should_skip_file(file_path, repo_root):
        return findings
    
    try:
        # Try to read as text
        content = file_path.read_text(encoding='utf-8', errors='ignore')
        lines = content.split('\n')
        
        for line_num, line in enumerate(lines, start=1):
            for pattern, pattern_name in SECRET_PATTERNS:
                matches = re.finditer(pattern, line, re.IGNORECASE)
                for match in matches:
                    # Extract the actual secret value (from capture group if available)
                    secret_value = match.group(1) if match.lastindex else match.group(0)
                    findings.append(SecretFinding(
                        file_path=file_path,
                        line_num=line_num,
                        pattern_name=pattern_name,
                        match=secret_value[:50] + '...' if len(secret_value) > 50 else secret_value,
                        line_content=line
                    ))
    except (UnicodeDecodeError, PermissionError, IsADirectoryError):
        # Skip binary files or files we can't read
        pass
    except Exception as e:
        # Log but don't fail on individual file errors
        print(f"⚠️  Warning: Error scanning {file_path}: {e}", file=sys.stderr)
    
    return findings


def scan_repository(repo_root: Path, max_workers: int = 8) -> List[SecretFinding]:
    """Scan entire repository for secrets using multiple workers."""
    console = Console()
    console.print("[cyan]🔍 Scanning repository for secrets...[/cyan]")
    
    # Find all files
    all_files = []
    for path in repo_root.rglob('*'):
        if path.is_file() and not should_skip_file(path, repo_root):
            all_files.append(path)
    
    total_files = len(all_files)
    console.print(f"[cyan]Found {total_files} files to scan[/cyan]\n")
    
    all_findings = []
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[cyan]Scanning files...", total=total_files)
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_file = {
                executor.submit(scan_file, file_path, repo_root): file_path
                for file_path in all_files
            }
            
            for future in as_completed(future_to_file):
                try:
                    findings = future.result()
                    all_findings.extend(findings)
                except Exception as e:
                    file_path = future_to_file[future]
                    console.print(f"[yellow]⚠️  Error scanning {file_path}: {e}[/yellow]")
                finally:
                    progress.update(task, advance=1)
    
    return all_findings


def display_findings(findings: List[SecretFinding], repo_root: Path) -> Tuple[List[SecretFinding], List[SecretFinding]]:
    """Display findings, separating test files from non-test files."""
    console = Console()
    
    test_findings = [f for f in findings if f.is_test_file()]
    non_test_findings = [f for f in findings if not f.is_test_file()]
    
    # Group findings by file
    test_by_file: Dict[Path, List[SecretFinding]] = {}
    non_test_by_file: Dict[Path, List[SecretFinding]] = {}
    
    for finding in test_findings:
        if finding.file_path not in test_by_file:
            test_by_file[finding.file_path] = []
        test_by_file[finding.file_path].append(finding)
    
    for finding in non_test_findings:
        if finding.file_path not in non_test_by_file:
            non_test_by_file[finding.file_path] = []
        non_test_by_file[finding.file_path].append(finding)
    
    # Display non-test findings first (errors)
    if non_test_by_file:
        console.print("\n[bold red]❌ SECRETS FOUND IN NON-TEST FILES:[/bold red]\n")
        
        for file_path, file_findings in sorted(non_test_by_file.items()):
            rel_path = file_path.relative_to(repo_root)
            console.print(f"[bold red]{rel_path}[/bold red]")
            
            for finding in file_findings:
                console.print(f"  [red]Line {finding.line_num}:[/red] [{finding.pattern_name}] {finding.match}")
                console.print(f"    {finding.line_content[:100]}")
            console.print()
    
    # Display test findings (warnings)
    if test_by_file:
        console.print("\n[yellow]⚠️  SECRETS FOUND IN TEST FILES:[/yellow]\n")
        
        for file_path, file_findings in sorted(test_by_file.items()):
            rel_path = file_path.relative_to(repo_root)
            console.print(f"[yellow]{rel_path}[/yellow]")
            
            for finding in file_findings:
                console.print(f"  [yellow]Line {finding.line_num}:[/yellow] [{finding.pattern_name}] {finding.match}")
                console.print(f"    {finding.line_content[:100]}")
            console.print()
    
    return test_findings, non_test_findings


def prompt_user_for_test_files(test_findings: List[SecretFinding], repo_root: Path) -> bool:
    """Prompt user for test file findings. Returns True if user wants to continue."""
    if not test_findings:
        return True
    
    console = Console()
    
    # Group by file for cleaner display
    by_file: Dict[Path, List[SecretFinding]] = {}
    for finding in test_findings:
        if finding.file_path not in by_file:
            by_file[finding.file_path] = []
        by_file[finding.file_path].append(finding)
    
    # Check if we're in a non-interactive environment (CI)
    if not sys.stdin.isatty():
        console.print("\n[yellow]⚠️  Test files contain potential secrets (non-interactive mode)[/yellow]")
        console.print("[yellow]Commit will proceed, but please review these files:[/yellow]\n")
        
        for file_path, findings in sorted(by_file.items()):
            rel_path = file_path.relative_to(repo_root)
            console.print(f"[yellow]  {rel_path}[/yellow]")
        return True
    
    console.print("\n[yellow]⚠️  Test files contain potential secrets:[/yellow]\n")
    
    for file_path, findings in sorted(by_file.items()):
        rel_path = file_path.relative_to(repo_root)
        console.print(f"[yellow]File: {rel_path}[/yellow]")
        for finding in findings:
            console.print(f"  Line {finding.line_num}: [{finding.pattern_name}]")
            console.print(f"  Value: [yellow]{finding.match}[/yellow]")
        console.print()
    
    while True:
        try:
            choice = Prompt.ask(
                "[yellow]Continue (c), Retry (r), or Exit (e)?[/yellow]",
                choices=["c", "r", "e"],
                default="e"
            )
            
            if choice == "c":
                return True
            elif choice == "r":
                return False
            elif choice == "e":
                console.print("[red]Commit aborted by user[/red]")
                return False
        except (KeyboardInterrupt, EOFError):
            console.print("\n[red]Commit aborted by user[/red]")
            return False


def main() -> int:
    """Main entry point. Returns 0 on success, 1 on failure."""
    repo_root = find_repo_root()
    
    # Scan repository
    findings = scan_repository(repo_root, max_workers=8)
    
    if not findings:
        console = Console()
        console.print("[green]✅ No secrets found[/green]")
        return 0
    
    # Separate test and non-test findings
    test_findings, non_test_findings = display_findings(findings, repo_root)
    
    # Fail loudly for non-test files
    if non_test_findings:
        console = Console()
        console.print("\n[bold red]❌ COMMIT BLOCKED: Secrets found in non-test files![/bold red]")
        console.print("[red]Please remove secrets before committing.[/red]\n")
        return 1
    
    # Prompt for test files
    if test_findings:
        if not prompt_user_for_test_files(test_findings, repo_root):
            return 1
    
    return 0


if __name__ == "__main__":
    # Ensure unbuffered output for git hooks
    if hasattr(sys.stdout, 'reconfigure'):  # type: ignore[attr-defined]
        sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    if hasattr(sys.stderr, 'reconfigure'):  # type: ignore[attr-defined]
        sys.stderr.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
    
    sys.exit(main())
