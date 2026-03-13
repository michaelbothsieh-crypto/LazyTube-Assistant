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
    
    headers = {'Authorization': f'Bearer {token}', 'x-api-version': '1'}
    try:
        # 使用 prefix=state/ 進行精確搜尋
        list_url = f'https://blob.vercel-storage.com/v1?prefix=state/{name}'
        req = r.Request(list_url, headers=headers)
        with r.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            blobs = data.get('blobs', [])
            if blobs:
                # 下載內容
                with r.urlopen(blobs[0]['url']) as f_resp:
                    with open(name, 'wb') as f:
                        f.write(f_resp.read())
                return True
    except Exception as e:
        print(f"⚠️ Download {name} failed: {e}")
    
    # 失敗時建立預設檔案
    with open(name, 'w') as f:
        f.write(default)
    return False

def main():
    if len(sys.argv) < 2: return
    action = sys.argv[1]

    if action == "restore":
        target_hash = sys.argv[2] if len(sys.argv) > 2 else ""
        dl('processed_videos.txt', '')
        
        for i in range(4): # 增加到 4 次重試 (共 30 秒)
            success = dl('subscriptions.json', '{}')
            if success and target_hash:
                with open('subscriptions.json', 'r') as f:
                    try:
                        s = json.load(f)
                        if any(get_h(k) == target_hash for k in s.keys()):
                            print(f"✅ Sync successful for {target_hash}")
                            return
                    except: pass
            print(f"⏳ Sync delay for {target_hash}, retrying {i+1}...")
            time.sleep(10)

    elif action == "persist":
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return
        
        for name in ['processed_videos.txt', 'subscriptions.json']:
            if not os.path.exists(name): continue
            try:
                with open(name, 'rb') as f:
                    data = f.read()
                
                # 防止空檔案導致 400
                if len(data) == 0: data = b"\n"
                
                url = f"https://blob.vercel-storage.com/state/{name}"
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
