#!/usr/bin/env -S uv run --quiet --with google-api-python-client --with PyYAML --with httpx
"""Export Google API schemas as YAML files for Pydantic model generation.

Usage:
    cd shared_utilities/schemas/google/_tooling
    
    # Export all Gmail schemas
    uv run export.py gmail v1
    
    # Export with method definitions
    uv run export.py gmail v1 --methods
    
    # Export specific resource schemas
    uv run export.py gmail v1 --resources Message Thread
    
    # Export to custom directory
    uv run export.py gmail v1 --output ../gmail
    
    # Show available schemas without exporting
    uv run export.py gmail v1 --list
"""

import json
import sys
from pathlib import Path
from typing import Any

import yaml
from googleapiclient.discovery import build

from .discovery import get_api_metadata as _get_api_metadata


def get_api_discovery_doc(api: str, version: str) -> dict[str, Any]:
    """Fetch the discovery document for an API (I/O operation).
    
    Note: Some APIs (like Forms) don't use the central discovery service
    and require fetching directly from their service endpoint.
    
    This function performs I/O - pure analysis functions are in discovery.py.
    """
    import httpx
    from googleapiclient.errors import HttpError
    
    try:
        discovery = build("discovery", "v1")
        doc = discovery.apis().getRest(api=api, version=version).execute()
        return doc
    except HttpError as e:
        if e.resp.status == 404:
            alternative_url = f"https://{api}.googleapis.com/$discovery/rest?version={version}"
            print(f"⚠️  Not in discovery service, trying: {alternative_url}")
            
            response = httpx.get(alternative_url)
            response.raise_for_status()
            return response.json()
        raise


def list_available_apis() -> list[dict[str, Any]]:
    """List all available Google APIs from Discovery service (I/O operation).
    
    Returns:
        List of API metadata dicts with name, version, title, etc.
    """
    discovery = build("discovery", "v1")
    result = discovery.apis().list().execute()
    return result.get("items", [])


def list_schemas(doc: dict[str, Any]) -> None:
    """List all available schemas in the API."""
    schemas = doc.get("schemas", {})
    
    print(f"\nAvailable schemas for {doc.get('title', 'API')}:\n")
    for schema_name, schema_data in sorted(schemas.items()):
        description = schema_data.get("description", "No description")
        schema_type = schema_data.get("type", "object")
        print(f"  📦 {schema_name:<30} ({schema_type})")
        print(f"     {description[:80]}{'...' if len(description) > 80 else ''}")


def export_schemas(
    doc: dict[str, Any],
    output_dir: Path,
    resource_filter: list[str] | None = None,
) -> None:
    """Export API schemas as YAML files."""
    schemas = doc.get("schemas", {})
    api_name = doc.get("name", "api")
    api_version = doc.get("version", "v1")
    
    if resource_filter:
        schemas = {k: v for k, v in schemas.items() if k in resource_filter}
    
    if not schemas:
        print("No schemas found to export.")
        return
    
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create a metadata file with API info
    metadata = {
        "api": api_name,
        "version": api_version,
        "title": doc.get("title", ""),
        "description": doc.get("description", ""),
        "baseUrl": doc.get("baseUrl", ""),
        "documentationLink": doc.get("documentationLink", ""),
        "generated": "auto-generated from Google Discovery API",
        "schemas": list(schemas.keys()),
    }
    
    metadata_file = output_dir / "_metadata.yaml"
    with open(metadata_file, "w") as f:
        yaml.dump(metadata, f, default_flow_style=False, sort_keys=False)
    
    print(f"📝 Exported metadata to {metadata_file}")
    
    # Export each schema
    for schema_name, schema_data in sorted(schemas.items()):
        # Convert to clean YAML-friendly format
        clean_schema = {
            "$schema": "http://json-schema.org/draft-07/schema#",
            "title": schema_name,
            "description": schema_data.get("description", ""),
            "type": schema_data.get("type", "object"),
        }
        
        # Add properties if present
        if "properties" in schema_data:
            clean_schema["properties"] = schema_data["properties"]
        
        # Add required fields if present
        if "required" in schema_data:
            clean_schema["required"] = schema_data["required"]
        
        # Add additional properties flag
        if "additionalProperties" in schema_data:
            clean_schema["additionalProperties"] = schema_data["additionalProperties"]
        
        # Add enum if present
        if "enum" in schema_data:
            clean_schema["enum"] = schema_data["enum"]
        
        # Add other schema metadata
        for key in ["format", "minimum", "maximum", "pattern", "items"]:
            if key in schema_data:
                clean_schema[key] = schema_data[key]
        
        schema_file = output_dir / f"{schema_name}.yaml"
        with open(schema_file, "w") as f:
            yaml.dump(clean_schema, f, default_flow_style=False, sort_keys=False)
        
        print(f"  ✅ {schema_name:<30} → {schema_file}")
    
    print(f"\n✨ Exported {len(schemas)} schemas to {output_dir}")
    print(f"\nTo generate Pydantic models, run:")
    print(f"  datamodel-codegen --input {output_dir} --output models/")


def extract_method_schemas(doc: dict[str, Any]) -> dict[str, dict]:
    """Extract request/response schemas for all methods."""
    method_schemas = {}
    
    def process_resources(resources: dict, prefix: str = ""):
        for resource_name, resource_data in resources.items():
            full_prefix = f"{prefix}{resource_name}." if prefix or resource_name else ""
            
            if "methods" in resource_data:
                for method_name, method_data in resource_data["methods"].items():
                    method_path = f"{full_prefix}{method_name}"
                    
                    schema_info = {
                        "description": method_data.get("description", ""),
                        "httpMethod": method_data.get("httpMethod", ""),
                        "path": method_data.get("path", ""),
                    }
                    
                    # Scopes (critical for OAuth2)
                    if "scopes" in method_data:
                        schema_info["scopes"] = method_data["scopes"]
                    
                    # Request schema
                    if "request" in method_data:
                        schema_info["request"] = method_data["request"]
                    
                    # Parameters schema
                    if "parameters" in method_data:
                        schema_info["parameters"] = method_data["parameters"]
                    
                    # Response schema
                    if "response" in method_data:
                        schema_info["response"] = method_data["response"]
                    
                    method_schemas[method_path] = schema_info
            
            if "resources" in resource_data:
                process_resources(resource_data["resources"], full_prefix)
    
    resources = doc.get("resources", {})
    process_resources(resources)
    
    return method_schemas


def export_method_schemas(doc: dict[str, Any], output_dir: Path) -> None:
    """Export method request/response schemas."""
    method_schemas = extract_method_schemas(doc)
    
    methods_dir = output_dir / "methods"
    methods_dir.mkdir(parents=True, exist_ok=True)
    
    for method_path, schema_info in sorted(method_schemas.items()):
        # Convert dots to underscores for filename
        safe_name = method_path.replace(".", "_")
        method_file = methods_dir / f"{safe_name}.yaml"
        
        with open(method_file, "w") as f:
            yaml.dump(schema_info, f, default_flow_style=False, sort_keys=False)
        
        print(f"  ✅ {method_path:<40} → {method_file.name}")
    
    print(f"\n✨ Exported {len(method_schemas)} method schemas to {methods_dir}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(
        description="Export Google API schemas as YAML files"
    )
    parser.add_argument("api", help="API name (e.g., gmail, drive)")
    parser.add_argument("version", help="API version (e.g., v1, v3)")
    parser.add_argument(
        "--list", 
        action="store_true",
        help="List available schemas without exporting"
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Output directory (default: shared_utilities/schemas/google/<api>)"
    )
    parser.add_argument(
        "--resources", "-r",
        nargs="+",
        help="Only export specific resource schemas"
    )
    parser.add_argument(
        "--methods",
        action="store_true",
        help="Also export method request/response schemas"
    )
    
    args = parser.parse_args()
    
    print(f"Fetching discovery document for {args.api} {args.version}...")
    doc = get_api_discovery_doc(args.api, args.version)
    
    if args.list:
        list_schemas(doc)
        return
    
    # Determine output directory
    if args.output:
        output_dir = Path(args.output)
    else:
        # Script is in shared_utilities/schemas/google/_tooling/
        tooling_dir = Path(__file__).parent
        google_schemas_dir = tooling_dir.parent
        output_dir = google_schemas_dir / args.api
    
    print(f"\nExporting to: {output_dir}\n")
    
    export_schemas(doc, output_dir, args.resources)
    
    if args.methods:
        print("\nExporting method schemas...")
        export_method_schemas(doc, output_dir)


if __name__ == "__main__":
    main()
