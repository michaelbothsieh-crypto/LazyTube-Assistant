import urllib.request as r
import json
import os

token = "mock"
headers = {'Authorization': f'Bearer {token}'}
list_url = f'https://blob.vercel-storage.com?prefix=state/last_check.txt'
print(list_url)
