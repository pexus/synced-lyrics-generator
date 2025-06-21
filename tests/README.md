# Tests Directory

This directory contains test scripts for the SyncedLyrics application.

## Available Tests

- `test_templates.py`: Tests the rendering of LRC and SRT debug templates (uses requests to test live server)
- `test_routes.py`: Tests the Flask routes using the Flask test client
- `run_tests.py`: A test runner script that can run all tests or a specific test

## Running Tests

To run all tests, navigate to the project root and execute:

```bash
# Run all tests
python -m tests.run_tests

# Run a specific test
python -m tests.run_tests test_routes

# Or from within the tests directory
cd tests
python run_tests.py
```

## Adding New Tests

When adding new tests, follow these guidelines:

1. Create a descriptive filename with the `test_` prefix
2. Include comments to explain the purpose of the test
3. Add the test to this README file

## Test Dependencies

Some tests may require additional packages. Install them with:

```bash
pip install requests pytest
```
