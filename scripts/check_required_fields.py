#!/usr/bin/env python3
"""
Check that Pydantic models don't have defaults on required fields.

Catches:
  ❌ deleted: bool = False
  ❌ count: int = 0  
  ❌ items: List[str] = Field(default_factory=list)
  ❌ name: str = Field(default="unknown")

Allows:
  ✅ email: Optional[str] = None
  ✅ name: str = Field(description="User name")  # Just metadata, no default
  ✅ name: str  # No default at all
"""
import re
import sys
from pathlib import Path
from prompt_utils import is_interactive, prompt_choice


def check_file(filepath: Path) -> list[str]:
    """Check a file for required fields with defaults."""
    errors = []
    content = filepath.read_text()
    lines = content.split('\n')
    
    in_class = False
    class_is_model = False
    
    for i, line in enumerate(lines, 1):
        # Track if we're in a Pydantic model class
        if line.strip().startswith('class '):
            in_class = True
            class_is_model = 'BaseModel' in line or 'ApiModel' in line
            continue
        
        if not in_class or not class_is_model:
            continue
        
        # End of class definition
        if line and not line[0].isspace() and line.strip():
            in_class = False
            class_is_model = False
            continue
        
        # Skip comments, empty lines, methods
        stripped = line.strip()
        if not stripped or stripped.startswith('#') or stripped.startswith('def ') or stripped.startswith('@'):
            continue
        
        # Match field definitions: field_name: Type = default
        match = re.match(r'\s+(\w+):\s*([^=]+?)\s*=\s*(.+)', line)
        if not match:
            continue
        
        field_name, field_type, default_value = match.groups()
        field_type = field_type.strip()
        default_value = default_value.strip()
        
        # Allow Optional fields (they can have defaults including None)
        if 'Optional[' in field_type:
            continue
        
        # Allow Union types that include None (equivalent to Optional)
        if 'Union[' in field_type and 'None' in field_type:
            continue
        
        # Check if it's a real default (not just metadata)
        has_real_default = False
        
        # Direct value assignment: name: str = "default"
        if not default_value.startswith('Field('):
            has_real_default = True
        # Field() with default or default_factory
        elif 'default=' in default_value or 'default_factory=' in default_value:
            has_real_default = True
        
        if has_real_default:
            errors.append(
                f"{filepath}:{i}: Required field '{field_name}: {field_type}' "
                f"should not have a default. Make it Optional[{field_type}] or remove the default."
            )
    
    return errors


def prompt_user_action() -> str:
    """
    Prompt user for action when violations are found.
    Returns: 'c' (continue), 'r' (retry), or 'e' (exit)
    """
    return prompt_choice(
        "What would you like to do?",
        {
            'c': 'Continue anyway and commit with violations',
            'r': 'Retry after fixing violations',
            'e': 'Exit without committing'
        },
        default='e'
    )


def main():
    """Check model files for violations."""
    # Check specific model directories
    check_dirs = [
        'backend/modules/integrations/slack/models',
        'backend/modules/integrations/shopify/models',
        'backend/modules/refunds/models',
    ]
    
    interactive = is_interactive()
    
    while True:
        errors = []
        for dir_path in check_dirs:
            path = Path(dir_path)
            if path.exists():
                for py_file in path.rglob('*.py'):
                    errors.extend(check_file(py_file))
        
        if not errors:
            print('✅ No required fields with defaults found in integration models')
            return 0
        
        # Display warnings
        print('⚠️  Found required fields with defaults:\n')
        for error in errors:
            print(f'  {error}')
        print('\n💡 Required fields should NOT have defaults.')
        print('   Either remove the default or make the field Optional[T]')
        
        # Non-interactive mode: just exit with error
        if not interactive:
            print('\n❌ Running in non-interactive mode. Exiting.')
            return 1
        
        # Interactive mode: prompt user
        action = prompt_user_action()
        
        if action == 'c':
            print("\n⚠️  Continuing with violations...")
            return 0
        elif action == 'e':
            print("\n❌ Exiting without committing.")
            return 1
        elif action == 'r':
            print("\n🔄 Retrying...\n")
            # Loop will re-check files
            continue


if __name__ == '__main__':
    sys.exit(main())

