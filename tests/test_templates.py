import requests
import time
import sys
import os
import sys

# Add the parent directory to sys.path to allow importing project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

base_url = "http://localhost:5000"
test_basename = "FirstDayAnyDay-ElectricBlue-Take2-2025-06-11-WAV"

print("Testing LRC and SRT debug routes...")

endpoints = [
    f"/debug/lrc/{test_basename}",
    f"/debug/srt/{test_basename}",
    f"/debug/lrc/non_existent_file",  # Should return 404 with error template
    f"/debug/srt/non_existent_file",  # Should return 404 with error template
]

for endpoint in endpoints:
    url = base_url + endpoint
    print(f"\nTesting endpoint: {url}")
    try:
        response = requests.get(url)
        print(f"Status code: {response.status_code}")
        if response.status_code == 200:
            print("Template rendered successfully!")
        else:
            print("Error response received (expected for non_existent_file tests)")
    except Exception as e:
        print(f"Error: {e}")

print("\nTests completed!")
