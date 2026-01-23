"""Entry point for scripts.compilation module."""
import sys

from .compile_main import (
    compile_all,
    compile_backend,
    compile_for_path,
    compile_gas,
    compile_lambda,
)


def main():
    """Main entry point for compilation module."""
    if len(sys.argv) < 2:
        print("Usage: python -m scripts.compilation <command> [path]")
        print("Commands:")
        print("  compile-backend  - Compile backend code")
        print("  compile-lambda   - Compile Lambda functions")
        print("  compile-gas      - Compile Google Apps Scripts")
        print("  compile-all      - Compile all repos")
        print("  compile-path <path> - Compile code for specific path")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "compile-backend":
        sys.exit(compile_backend())
    elif command == "compile-lambda":
        sys.exit(compile_lambda())
    elif command == "compile-gas":
        sys.exit(compile_gas())
    elif command == "compile-all":
        sys.exit(compile_all())
    elif command == "compile-path":
        if len(sys.argv) < 3:
            print("❌ Path required for compile-path command")
            sys.exit(1)
        sys.exit(compile_for_path(sys.argv[2]))
    else:
        print(f"❌ Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
