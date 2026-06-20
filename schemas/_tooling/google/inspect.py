#!/usr/bin/env -S uv run --quiet --with google-api-python-client
"""Inspect Google API methods and their required OAuth scopes.

Usage:
    cd shared_utilities/schemas/_tooling/google
    
    # List all available Google APIs
    uv run inspect.py --list
    
    # Show all Gmail API methods and scopes
    uv run inspect.py gmail v1
    
    # Show specific method details
    uv run inspect.py gmail v1 users.messages.send
    
    # Or from repo root
    python shared_utilities/schemas/_tooling/google/inspect.py --list
"""

import sys
from pathlib import Path

# Allow running from anywhere
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from shared_utilities.schemas._tooling.google.discovery import (
    extract_method_scopes,
    format_method_summary,
    format_scope_summary,
    get_api_metadata,
    get_api_scopes,
    list_methods,
)
from shared_utilities.schemas._tooling.google.export import (
    get_api_discovery_doc,
    list_available_apis,
)


def show_api_list() -> None:
    """List all available Google APIs."""
    print("Fetching available Google APIs...\n")
    apis = list_available_apis()
    
    # Group by name
    by_name: dict[str, list[dict]] = {}
    for api in apis:
        name = api["name"]
        if name not in by_name:
            by_name[name] = []
        by_name[name].append(api)
    
    print(f"Available Google APIs ({len(by_name)} APIs):\n")
    for name in sorted(by_name.keys()):
        versions = ", ".join(sorted(v["version"] for v in by_name[name]))
        title = by_name[name][0].get("title", name)
        print(f"  {name:<25} {versions:<15} {title}")


def show_api_details(
    api: str,
    version: str,
    method_filter: str | None = None
) -> None:
    """Show methods and scopes for an API."""
    print(f"Fetching discovery document for {api} {version}...\n")
    
    doc = get_api_discovery_doc(api, version)
    metadata = get_api_metadata(doc)
    
    # Show API metadata
    print(f"API: {metadata['title']}")
    print(f"Description: {metadata['description']}")
    print(f"Base URL: {metadata['baseUrl']}")
    
    # Show all defined scopes
    print(f"\nAvailable OAuth Scopes:")
    scopes = get_api_scopes(doc)
    for scope_url, scope_info in scopes.items():
        print(format_scope_summary(scope_url, scope_info))
    
    # Show methods
    print("\n" + "=" * 80)
    print("Methods and Required Scopes:")
    print("=" * 80 + "\n")
    
    methods = list_methods(doc)
    
    # Filter if requested
    if method_filter:
        methods = {
            k: v for k, v in methods.items()
            if method_filter.lower() in k.lower()
        }
    
    if not methods:
        print("No methods found.")
        return
    
    for method_path, method_def in sorted(methods.items()):
        print(format_method_summary(method_path, method_def))
        print()


def main():
    if len(sys.argv) < 2 or sys.argv[1] == "--list":
        show_api_list()
        return
    
    if len(sys.argv) < 3:
        print("Usage: inspect.py <api> <version> [method_filter]")
        print("   or: inspect.py --list")
        sys.exit(1)
    
    api = sys.argv[1]
    version = sys.argv[2]
    method_filter = sys.argv[3] if len(sys.argv) > 3 else None
    
    show_api_details(api, version, method_filter)


if __name__ == "__main__":
    main()
