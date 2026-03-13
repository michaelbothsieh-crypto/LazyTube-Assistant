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
    if not token: return False
    
    headers = {'Authorization': f'Bearer {token}'}
    try:
        # 修正：Vercel Blob 列表 API 正確端點為根目錄，不要加 /v1
        list_url = f'https://blob.vercel-storage.com?prefix=state/{name}'
        req = r.Request(list_url, headers=headers)
        with r.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            blobs = data.get('blobs', [])
            if blobs:
                # 找到最匹配的檔案
                with r.urlopen(blobs[0]['url']) as f_resp:
                    with open(name, 'wb') as f:
                        f.write(f_resp.read())
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
        dl('processed_videos.txt', '')
        
        print(f"🔍 Searching for subscriptions for {target_hash}...")
        for i in range(5): # 增加重試次數與時間
            success = dl('subscriptions.json', '{}')
            if success and target_hash:
                try:
                    with open('subscriptions.json', 'r') as f:
                        s = json.load(f)
                        if any(get_h(k) == target_hash for k in s.keys()):
                            print(f"✅ Sync successful! Found {target_hash} in cloud data.")
                            return
                except: pass
            print(f"⏳ Cloud data not updated yet, retrying {i+1}/5...")
            time.sleep(10)
        print("⚠️ Failed to find matching group data after retries.")

    elif action == "persist":
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return
        
        for name in ['processed_videos.txt', 'subscriptions.json']:
            if not os.path.exists(name): continue
            try:
                with open(name, 'rb') as f:
                    data = f.read()
                if len(data) == 0: data = b"\n"
                
                url = f"https://blob.vercel-storage.com/state/{name}"
                req = r.Request(url, data=data, method='PUT', headers={
                    'Authorization': f'Bearer {token}',
                    'x-api-version': '1',
                    'x-add-random-suffix': '0',
                    'content-type': 'application/octet-stream'
                })
                r.urlopen(req)
                print(f"✅ Persisted {name} to cloud.")
            except Exception as e:
                print(f"❌ Persist {name} failed: {e}")

if __name__ == "__main__":
    main()
