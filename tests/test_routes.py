import os
import sys
import unittest
from io import StringIO

# Add the parent directory to sys.path to allow importing project modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the Flask app
from app import app

class RouteTests(unittest.TestCase):
    """Test cases for the Flask routes"""
    
    def setUp(self):
        """Set up test client"""
        self.app = app.test_client()
        self.app.testing = True
        
    def test_home_route(self):
        """Test the home page route"""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        
    def test_lrc_debug_route_existing_file(self):
        """Test the LRC debug route with an existing file"""
        # This assumes the file exists in the LRC output folder
        response = self.app.get('/debug/lrc/FirstDayAnyDay-ElectricBlue-Take2-2025-06-11-WAV')
        self.assertEqual(response.status_code, 200)
        
    def test_srt_debug_route_existing_file(self):
        """Test the SRT debug route with an existing file"""
        # This assumes the file exists in the SRT output folder
        response = self.app.get('/debug/srt/FirstDayAnyDay-ElectricBlue-Take2-2025-06-11-WAV')
        self.assertEqual(response.status_code, 200)
        
    def test_lrc_debug_route_nonexistent_file(self):
        """Test the LRC debug route with a non-existent file"""
        response = self.app.get('/debug/lrc/non_existent_file')
        self.assertEqual(response.status_code, 404)
        
    def test_srt_debug_route_nonexistent_file(self):
        """Test the SRT debug route with a non-existent file"""
        response = self.app.get('/debug/srt/non_existent_file')
        self.assertEqual(response.status_code, 404)

if __name__ == '__main__':
    unittest.main()
