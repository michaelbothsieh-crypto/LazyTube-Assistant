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
    
    # 這裡從「List 模式」改為「直接 GET 模式」，以節省 Advanced Operations 額度
    url = f"https://blob.vercel-storage.com/state/{name}"
    headers = {
        'Authorization': f'Bearer {token}',
        'x-api-version': '1'
    }
    
    try:
        req = r.Request(url, headers=headers)
        with r.urlopen(req) as resp:
            content = resp.read()
            # 如果回傳的是 JSON (代表檔案不存在或噴出錯誤)，Vercel 會回傳錯誤訊息
            # 正常檔案下載應該是 binary
            if content.startswith(b'{"error":'):
                print(f"⚠️ 雲端尚未有 {name} 紀錄，將使用預設值")
                with open(name, 'w') as f: f.write(default)
                return True
                
            with open(name, 'wb') as f: f.write(content)
            return True
    except r.HTTPError as e:
        if e.code == 404:
            print(f"ℹ️ 雲端無 {name} (404)，建立初始檔案")
            with open(name, 'w') as f: f.write(default)
            return True
        print(f"⚠️ 下載 {name} 失敗: HTTP {e.code}")
    except Exception as e:
        print(f"⚠️ 下載 {name} 異常: {e}")
    
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
        
        # 改為直接下載，不再使用 Advanced Operations 的 List
        success = dl('subscriptions.json', '{}')
        if success:
            print("✅ 狀態還原完成")
        return

    elif action == "persist":
        up('processed_videos.txt', 'processed_videos.txt')
        up('last_check.txt', 'last_check.txt')

        # 訂閱清單採用「下載-合併-上傳」策略
        local_file = 'subscriptions.json'
        if os.path.exists(local_file):
            print("🔄 Merging subscription updates into cloud data...")
            try:
                with open(local_file, 'r') as f: local_subs = json.load(f)
            except json.JSONDecodeError as e:
                print(f"❌ 本地 {local_file} 解析失敗: {e}")
                return

            if dl('subscriptions.json', '{}'):
                try:
                    with open(local_file, 'r') as f: cloud_subs = json.load(f)
                except json.JSONDecodeError as e:
                    print(f"❌ 雲端資料解析失敗: {e}")
                    # 雲端損壞則直接上傳本地版本
                    up('subscriptions.json', local_file)
                    return

                # --- 改進的合併邏輯 ---
                # 1. 確保本地所有群組都在雲端中存在
                for cid, l_group in local_subs.items():
                    if cid not in cloud_subs:
                        cloud_subs[cid] = l_group
                        continue
                    
                    # 2. 針對群組內的每個頻道進行比對與更新
                    c_group = cloud_subs[cid]
                    for l_sub in l_group:
                        found = False
                        for c_sub in c_group:
                            if l_sub['channel_id'] == c_sub['channel_id']:
                                # 更新狀態資訊
                                c_sub['last_check'] = l_sub['last_check']
                                c_sub['is_first_run'] = l_sub.get('is_first_run', False)
                                if 'signup_msg_id' in l_sub:
                                    c_sub['signup_msg_id'] = l_sub['signup_msg_id']
                                found = True
                                break
                        
                        # 3. 如果是新加入的頻道，則新增至雲端群組
                        if not found:
                            c_group.append(l_sub)

                # 寫回 local 並上傳
                with open(local_file, 'w', encoding='utf-8') as f:
                    json.dump(cloud_subs, f, ensure_ascii=False, indent=2)
                up('subscriptions.json', local_file)


if __name__ == "__main__":
    main()
