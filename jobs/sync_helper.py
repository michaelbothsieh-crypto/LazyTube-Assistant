"""
狀態同步小幫手 (一致性加強版)
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
        print(f"⚠️ 缺少 BLOB_READ_WRITE_TOKEN，無法下載 {name}")
        return False
    headers = {'Authorization': f'Bearer {token}'}
    try:
        list_url = f'https://blob.vercel-storage.com?prefix=state/{name}'
        req = r.Request(list_url, headers=headers)
        with r.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            blobs = data.get('blobs', [])
            if blobs:
                with r.urlopen(blobs[0]['url']) as f_resp:
                    content = f_resp.read()
                    with open(name, 'wb') as f: f.write(content)
                return True
    except Exception as e:
        print(f"⚠️ 下載 {name} 失敗: {e}")
    with open(name, 'w') as f: f.write(default)
    return False

def up(name, local_path):
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not os.path.exists(local_path): return
    try:
        with open(local_path, 'rb') as f: data = f.read()
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

def main():
    if len(sys.argv) < 2: return
    action = sys.argv[1]

    if action == "restore":
        target_chat_id = sys.argv[2] if len(sys.argv) > 2 else ""
        dl('processed_videos.txt', '')
        dl('last_check.txt', '')
        for i in range(5):
            success = dl('subscriptions.json', '{}')
            if not target_chat_id and success:
                print("✅ Downloaded subscriptions.json")
                return
            if success and target_chat_id:
                try:
                    with open('subscriptions.json', 'r') as f:
                        s = json.load(f)
                        if target_chat_id in s.keys():
                            print(f"✅ Found {target_chat_id}"); return
                except json.JSONDecodeError as e:
                    print(f"⚠️ subscriptions.json 解析失敗 (attempt {i+1}): {e}")
            if i < 4:
                print(f"⏳ 等待 Blob 同步... (attempt {i+1}/5)")
                time.sleep(10)

    elif action == "persist":
        up('processed_videos.txt', 'processed_videos.txt')
        up('last_check.txt', 'last_check.txt')

        # 訂閱清單採用「下載-合併-上傳」策略
        # 注意: dl() 會覆蓋 local file，所以先將 local 資料讀進記憶體
        local_file = 'subscriptions.json'
        if os.path.exists(local_file):
            print("🔄 Merging last_check updates into cloud data...")
            try:
                with open(local_file, 'r') as f: local_subs = json.load(f)
            except json.JSONDecodeError as e:
                print(f"❌ 本地 {local_file} 解析失敗: {e}")
                return

            # dl() 下載雲端版本並覆蓋 local_file，但 local_subs 已在記憶體中
            if dl('subscriptions.json', '{}'):
                try:
                    with open(local_file, 'r') as f: cloud_subs = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"❌ 雲端資料解析失敗: {e}")
                    # 雲端損壞則直接上傳本地版本
                    with open(local_file, 'w') as f: json.dump(local_subs, f)
                    up('subscriptions.json', local_file)
                    return

                # 將 local 的 last_check 與 is_first_run 更新到 cloud 中
                for cid, group in local_subs.items():
                    if cid in cloud_subs:
                        for l_sub in group:
                            for c_sub in cloud_subs[cid]:
                                if l_sub['channel_id'] == c_sub['channel_id']:
                                    c_sub['last_check'] = l_sub['last_check']
                                    c_sub['is_first_run'] = l_sub.get('is_first_run', False)
                                    if 'signup_msg_id' in l_sub:
                                        c_sub['signup_msg_id'] = l_sub['signup_msg_id']

                # 寫回 local 並上傳
                with open(local_file, 'w') as f: json.dump(cloud_subs, f)
                up('subscriptions.json', local_file)

if __name__ == "__main__":
    main()
