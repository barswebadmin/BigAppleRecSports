#!/usr/bin/env python3
"""
Generate Python Pydantic models and TypeScript types from YAML schemas.

This script reads YAML JSON Schema files from shared_utilities/schemas/
and generates:
- Python Pydantic models in backend/models/generated/
- TypeScript types in GoogleAppsScripts/types/generated/

Usage:
    python scripts/generate_types.py [--python-only] [--typescript-only]
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n{'='*60}")
    print(f"🔧 {description}")
    print(f"{'='*60}")
    print(f"Command: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        if result.stdout:
            print(result.stdout)
        print(f"✅ {description} - SUCCESS")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"Error: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"❌ {description} - FAILED")
        print(f"Error: Command not found. Make sure required tools are installed.")
        return False


def generate_python_models(schema_dir: Path, output_dir: Path) -> bool:
    """Generate Python Pydantic models from YAML schemas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all YAML schema files
    schema_files = list(schema_dir.rglob("*.yaml")) + list(schema_dir.rglob("*.yml"))
    
    if not schema_files:
        print(f"⚠️  No YAML schema files found in {schema_dir}")
        return True
    
    print(f"\n📋 Found {len(schema_files)} schema file(s):")
    for schema_file in schema_files:
        print(f"   - {schema_file.relative_to(schema_dir.parent)}")
    
    success = True
    for schema_file in schema_files:
        # Determine output path based on schema location
        relative_path = schema_file.relative_to(schema_dir)
        output_subdir = output_dir / relative_path.parent
        output_subdir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_subdir / f"{schema_file.stem}.py"
        
        cmd = [
            "datamodel-codegen",
            "--input", str(schema_file),
            "--output", str(output_file),
            "--input-file-type", "jsonschema",
            "--output-model-type", "pydantic_v2.BaseModel",
            "--use-standard-collections",
            "--use-schema-description",
            "--use-field-description",
            "--field-constraints",
            "--snake-case-field",
            "--allow-extra-fields",
        ]
        
        if not run_command(cmd, f"Generate Python model: {relative_path}"):
            success = False
    
    return success


def generate_typescript_types(schema_dir: Path, output_dir: Path) -> bool:
    """Generate TypeScript types from YAML schemas."""
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all YAML schema files
    schema_files = list(schema_dir.rglob("*.yaml")) + list(schema_dir.rglob("*.yml"))
    
    if not schema_files:
        print(f"⚠️  No YAML schema files found in {schema_dir}")
        return True
    
    print(f"\n📋 Found {len(schema_files)} schema file(s):")
    for schema_file in schema_files:
        print(f"   - {schema_file.relative_to(schema_dir.parent)}")
    
    success = True
    for schema_file in schema_files:
        # Determine output path based on schema location
        relative_path = schema_file.relative_to(schema_dir)
        output_subdir = output_dir / relative_path.parent
        output_subdir.mkdir(parents=True, exist_ok=True)
        
        output_file = output_subdir / f"{schema_file.stem}.ts"
        
        cmd = [
            "json2ts",
            "-i", str(schema_file),
            "-o", str(output_file),
            "--bannerComment", f"// Generated from {relative_path}\n// DO NOT EDIT - Changes will be overwritten",
        ]
        
        if not run_command(cmd, f"Generate TypeScript types: {relative_path}"):
            success = False
    
    return success


def main():
    parser = argparse.ArgumentParser(
        description="Generate types from YAML schemas",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  Generate both Python and TypeScript:
    python scripts/generate_types.py
  
  Generate only Python models:
    python scripts/generate_types.py --python-only
  
  Generate only TypeScript types:
    python scripts/generate_types.py --typescript-only
        """
    )
    parser.add_argument(
        "--python-only",
        action="store_true",
        help="Generate only Python Pydantic models"
    )
    parser.add_argument(
        "--typescript-only",
        action="store_true",
        help="Generate only TypeScript types"
    )
    
    args = parser.parse_args()
    
    # Determine project root (script is in scripts/ directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Define paths
    schema_dir = project_root / "shared_utilities" / "schemas"
    python_output_dir = project_root / "backend" / "models" / "generated"
    typescript_output_dir = project_root / "GoogleAppsScripts" / "types" / "generated"
    
    print("="*60)
    print("🚀 Type Generation from YAML Schemas")
    print("="*60)
    print(f"Schema directory: {schema_dir}")
    print(f"Python output:    {python_output_dir}")
    print(f"TypeScript output: {typescript_output_dir}")
    
    # Check if schema directory exists
    if not schema_dir.exists():
        print(f"\n❌ Schema directory not found: {schema_dir}")
        print("Please create schemas in shared_utilities/schemas/")
        sys.exit(1)
    
    success = True
    
    # Generate Python models
    if not args.typescript_only:
        if not generate_python_models(schema_dir, python_output_dir):
            success = False
    
    # Generate TypeScript types
    if not args.python_only:
        if not generate_typescript_types(schema_dir, typescript_output_dir):
            success = False
    
    print("\n" + "="*60)
    if success:
        print("✅ Type generation completed successfully!")
    else:
        print("⚠️  Type generation completed with errors")
    print("="*60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
