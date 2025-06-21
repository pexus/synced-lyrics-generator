#!/usr/bin/env python3
"""
Test runner for the SyncedLyrics application.
Run this from the project root directory with: python -m tests.run_tests
"""

import unittest
import sys
import os

# Add the parent directory to sys.path to allow importing project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

def run_all_tests():
    """Discover and run all tests in the tests directory"""
    print("Running all SyncedLyrics tests...")
    
    # Discover all tests in the tests directory
    test_loader = unittest.TestLoader()
    test_suite = test_loader.discover(os.path.dirname(__file__), pattern='test_*.py')
    
    # Run the tests
    test_runner = unittest.TextTestRunner(verbosity=2)
    result = test_runner.run(test_suite)
    
    # Return 0 if successful, 1 if there were failures
    return 0 if result.wasSuccessful() else 1

def run_specific_test(test_name):
    """Run a specific test module"""
    if not test_name.startswith('test_'):
        test_name = 'test_' + test_name
    
    if not test_name.endswith('.py'):
        test_name = test_name + '.py'
    
    test_path = os.path.join(os.path.dirname(__file__), test_name)
    
    if not os.path.exists(test_path):
        print(f"Error: Test file {test_name} not found.")
        return 1
    
    print(f"Running test: {test_name}")
    
    # Import the test module
    module_name = test_name[:-3]  # Remove .py extension
    __import__(f'tests.{module_name}')
    
    # Run the tests from the imported module
    return 0

if __name__ == '__main__':
    if len(sys.argv) > 1:
        # Run specific test if provided
        exit_code = run_specific_test(sys.argv[1])
    else:
        # Run all tests if no specific test is provided
        exit_code = run_all_tests()
    
    sys.exit(exit_code)
