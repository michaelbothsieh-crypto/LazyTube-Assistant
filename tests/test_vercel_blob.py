import os
import json
import urllib.request as r

token = os.environ.get("BLOB_READ_WRITE_TOKEN")
if not token:
    print("NO TOKEN")
else:
    list_url = 'https://blob.vercel-storage.com?prefix=state/last_check.txt'
    headers = {'Authorization': f'Bearer {token}'}
    try:
        req = r.Request(list_url, headers=headers)
        with r.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            print(data)
    except Exception as e:
        print(f"Error: {e}")
