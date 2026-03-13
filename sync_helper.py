"""
狀態同步小幫手 (GitHub Actions 專用)
用法:
  python sync_helper.py restore <hashed_id>
  python sync_helper.py persist
"""
import os
import json
import time
import sys
import hashlib
import urllib.request as r

def get_h(cid):
    return hashlib.sha256(str(cid).encode()).hexdigest()[:12]

def dl(name, default):
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token:
        print("❌ Missing BLOB_TOKEN")
        return False
    
    headers = {'Authorization': f'Bearer {token}', 'x-api-version': '1'}
    try:
        list_url = f'https://blob.vercel-storage.com/v1?prefix=state/{name}'
        req = r.Request(list_url, headers=headers)
        with r.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            if data.get('blobs'):
                url = data['blobs'][0]['url']
                content = r.urlopen(url).read()
                with open(name, 'wb') as f:
                    f.write(content)
                return True
    except Exception as e:
        print(f"⚠️ Download {name} failed: {e}")
    
    with open(name, 'w') as f:
        f.write(default)
    return False

def main():
    if len(sys.argv) < 2: return
    action = sys.argv[1]

    if action == "restore":
        target_hash = sys.argv[2] if len(sys.argv) > 2 else ""
        # 1. 先下載已處理影片清單
        dl('processed_videos.txt', '')
        # 2. 下載訂閱清單 (帶重試邏輯)
        for i in range(3):
            success = dl('subscriptions.json', '{}')
            if success and target_hash:
                with open('subscriptions.json', 'r') as f:
                    s = json.load(f)
                    if any(get_h(k) == target_hash for k in s.keys()):
                        print(f"✅ Sync successful for {target_hash}")
                        break
            print(f"⏳ Sync delay, retrying {i+1}...")
            time.sleep(10)

    elif action == "persist":
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        for name in ['processed_videos.txt', 'subscriptions.json']:
            if not os.path.exists(name): continue
            try:
                with open(name, 'rb') as f:
                    data = f.read()
                url = f"https://blob.vercel-storage.com/v1/upload/state/{name}"
                req = r.Request(url, data=data, method='PUT', headers={
                    'Authorization': f'Bearer {token}',
                    'x-api-version': '1',
                    'x-add-random-suffix': '0',
                    'content-type': 'application/octet-stream'
                })
                r.urlopen(req)
                print(f"✅ Persisted {name}")
            except Exception as e:
                print(f"❌ Persist {name} failed: {e}")

if __name__ == "__main__":
    main()
