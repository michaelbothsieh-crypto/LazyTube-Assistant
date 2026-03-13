import os
import sys
import re
import urllib.parse
from dotenv import load_dotenv

# Try to load keys from an .env file if it exists, otherwise use environment variables
load_dotenv()

# We need valid API keys to test
API_KEY = os.environ.get("YT_API_KEY") # Sometimes people use standard API keys
CLIENT_ID = os.environ.get("YT_CLIENT_ID")

if not CLIENT_ID:
    print("No YT_CLIENT_ID found. Checking app.config and app.auth...")
    from app.config import Config
    from app.auth import AuthManager
    from app.youtube import YouTubeService
    try:
        AuthManager.deploy_credentials()
        yt = YouTubeService()
        print("YT Service initialized. Testing fetch:")
        res = yt.get_channel_info("https://www.youtube.com/@%E4%BD%8E%E6%AC%B8%E6%AD%BB")
        print(f"RESULT: {res}")
    except Exception as e:
        print(f"Error testing yt service: {e}")
else:
    print("Cannot perform local test without correct credentials in environment.")
