#!/usr/bin/env python3
"""
Test runner for BARS Lambda Functions

This script provides an easy way to run tests for lambda functions with
proper setup.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path


def setup_test_environment():
    """Setup the test environment with required dependencies"""
    # Get the project root
    project_root = Path(__file__).parent.parent.parent
    lambda_functions_root = project_root / "lambda-functions"

    # Add necessary paths
    sys.path.insert(0, str(lambda_functions_root))
    bars_common_path = (lambda_functions_root / "lambda-layers" /
                        "bars-common-utils" / "python")
    sys.path.insert(0, str(bars_common_path))

    # Set environment variables for testing
    os.environ.update({
        'AWS_DEFAULT_REGION': 'us-east-1',
        'PYTHONPATH': f"{lambda_functions_root}:" +
                      f"{os.environ.get('PYTHONPATH', '')}",
    })

    print("🔧 Test environment configured")
    print(f"   📁 Lambda functions root: {lambda_functions_root}")
    print(f"   🐍 Python path: {sys.path[:3]}...")


def install_test_dependencies():
    """Install required test dependencies"""
    try:
        import pytest  # noqa: F401
        print("✅ pytest already installed")
    except ImportError:
        print("📦 Installing pytest...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            'pytest', 'pytest-asyncio'
        ])
        print("✅ pytest installed successfully")


def run_unit_tests(test_pattern=None, verbose=False):
    """Run unit tests"""
    print("\n🧪 Running Unit Tests")
    print("=" * 50)

    test_dir = Path(__file__).parent / "unit"
    args = ['-v'] if verbose else []

    if test_pattern:
        args.extend(['-k', test_pattern])

    args.append(str(test_dir))

    return subprocess.call([sys.executable, '-m', 'pytest'] + args)


def run_integration_tests(test_pattern=None, verbose=False):
    """Run integration tests"""
    print("\n🔗 Running Integration Tests")
    print("=" * 50)

    test_dir = Path(__file__).parent / "integration"
    args = ['-v'] if verbose else []

    if test_pattern:
        args.extend(['-k', test_pattern])

    args.append(str(test_dir))

    return subprocess.call([sys.executable, '-m', 'pytest'] + args)


def run_specific_function_tests(function_name, verbose=False):
    """Run tests for a specific lambda function"""
    print(f"\n⚡ Running Tests for {function_name}")
    print("=" * 50)

    test_patterns = {
        'MoveInventoryLambda': 'test_move_inventory',
        'shopifyProductUpdateHandler': 'test_shopify_product_update',
        'createScheduledPriceChanges': 'test_scheduler',
        'schedulePriceChanges': 'test_scheduler',
        'CreateScheduleLambda': 'test_scheduler',
        'changePricesOfOpenAndWaitlistVariants': 'test_price_changes',
        'bars_common_utils': 'test_bars_common_utils'
    }

    pattern = test_patterns.get(function_name)
    if not pattern:
        print(f"❌ Unknown function: {function_name}")
        print(f"Available functions: {', '.join(test_patterns.keys())}")
        return 1

    test_dir = Path(__file__).parent
    args = ['-v'] if verbose else []
    args.extend(['-k', pattern])
    args.append(str(test_dir))

    return subprocess.call([sys.executable, '-m', 'pytest'] + args)


def run_coverage_tests():
    """Run tests with coverage reporting"""
    print("\n📊 Running Tests with Coverage")
    print("=" * 50)

    try:
        import coverage  # type: ignore
        print("✅ coverage already installed")
    except ImportError:
        print("📦 Installing coverage...")
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install', 'coverage[toml]'
        ])
        # Re-import after installation
        import coverage  # type: ignore

    test_dir = Path(__file__).parent

    # Run coverage
    cmd = [
        sys.executable, '-m', 'coverage', 'run',
        '--source', str(Path(__file__).parent.parent),
        '-m', 'pytest', str(test_dir), '-v'
    ]

    result = subprocess.call(cmd)

    if result == 0:
        print("\n📈 Coverage Report:")
        subprocess.call([
            sys.executable, '-m', 'coverage', 'report', '--show-missing'
        ])

        # Generate HTML report
        html_dir = Path(__file__).parent / 'coverage_html'
        subprocess.call([
            sys.executable, '-m', 'coverage', 'html', '-d', str(html_dir)
        ])
        print(f"\n🌐 HTML coverage report generated: {html_dir}/index.html")

    return result


def list_available_tests():
    """List all available tests"""
    print("\n📋 Available Tests")
    print("=" * 50)

    test_dir = Path(__file__).parent

    print("Unit Tests:")
    unit_tests = list((test_dir / "unit").glob("test_*.py"))
    for test_file in unit_tests:
        print(f"  📄 {test_file.name}")

    print("\nIntegration Tests:")
    integration_tests = list((test_dir / "integration").glob("test_*.py"))
    for test_file in integration_tests:
        print(f"  📄 {test_file.name}")

    print("\nLambda Functions:")
    functions = [
        'MoveInventoryLambda',
        'shopifyProductUpdateHandler',
        'createScheduledPriceChanges',
        'schedulePriceChanges',
        'CreateScheduleLambda',
        'changePricesOfOpenAndWaitlistVariants',
        'bars_common_utils'
    ]
    for func in functions:
        print(f"  ⚡ {func}")


def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(
        description="BARS Lambda Functions Test Runner"
    )
    parser.add_argument(
        'command', nargs='?', default='all',
        choices=['all', 'unit', 'integration', 'coverage', 'list',
                 'function'],
        help='Test command to run'
    )
    parser.add_argument(
        '--function', '-f',
        help='Specific function to test (when using function command)'
    )
    parser.add_argument('--pattern', '-k', help='Test pattern to match')
    parser.add_argument(
        '--verbose', '-v', action='store_true', help='Verbose output'
    )

    args = parser.parse_args()

    print("🧪 BARS Lambda Functions Test Runner")
    print("=" * 60)

    # Setup environment
    setup_test_environment()
    install_test_dependencies()

    # Run appropriate tests
    if args.command == 'list':
        list_available_tests()
        return 0

    elif args.command == 'unit':
        return run_unit_tests(args.pattern, args.verbose)

    elif args.command == 'integration':
        return run_integration_tests(args.pattern, args.verbose)

    elif args.command == 'coverage':
        return run_coverage_tests()

    elif args.command == 'function':
        if not args.function:
            print("❌ Please specify a function with --function")
            return 1
        return run_specific_function_tests(args.function, args.verbose)

    elif args.command == 'all':
        print("\n🚀 Running All Tests")
        print("=" * 50)

        # Run unit tests first
        unit_result = run_unit_tests(args.pattern, args.verbose)

        # Run integration tests
        integration_result = run_integration_tests(args.pattern, args.verbose)

        # Summary
        print("\n📊 Test Summary")
        print("=" * 50)
        print(f"Unit Tests: {'✅ PASSED' if unit_result == 0 else '❌ FAILED'}")
        integration_status = ('✅ PASSED' if integration_result == 0
                              else '❌ FAILED')
        print(f"Integration Tests: {integration_status}")

        return max(unit_result, integration_result)

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code) 