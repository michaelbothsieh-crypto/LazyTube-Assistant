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

def dl_state():
    """下載合併後的 state.json 並拆分到本地檔案"""
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token: return False
    
    headers = {'Authorization': f'Bearer {token}'}
    try:
        # 使用 list 找到 state.json 的真正 URL (Advanced Operation, 消耗 1 次)
        list_url = 'https://blob.vercel-storage.com?prefix=state/state.json'
        req = r.Request(list_url, headers=headers)
        with r.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            blobs = data.get('blobs', [])
            if blobs:
                # 取得真正具有隨機後綴的下載連結 (Simple Operation)
                with r.urlopen(blobs[0]['url']) as f_resp:
                    content = json.loads(f_resp.read().decode())
                    
                    # 拆分回原本的檔案供主程式使用
                    with open('processed_videos.txt', 'w') as f: 
                        f.write("\n".join(content.get('processed_videos', [])))
                    with open('last_check.txt', 'w') as f: 
                        f.write(content.get('last_check', ''))
                    with open('subscriptions.json', 'w') as f: 
                        json.dump(content.get('subscriptions', {}), f, ensure_ascii=False, indent=2)
                    print(f"✅ 狀態已從雲端 state.json 還原 (包含 {len(content.get('processed_videos', []))} 筆紀錄)")
                    return True
    except Exception as e:
        print(f"⚠️ 雲端 state.json 讀取失敗或尚未建立: {e}")
    
    # 建立空的初始檔案
    with open('processed_videos.txt', 'w') as f: f.write('')
    with open('last_check.txt', 'w') as f: f.write('')
    with open('subscriptions.json', 'w') as f: f.write('{}')
    return False

def up_state():
    """將本地三個檔案合併並上傳為 state.json"""
    token = os.environ.get("BLOB_READ_WRITE_TOKEN")
    if not token: return
    
    try:
        # 讀取並打包
        state = {'processed_videos': [], 'last_check': '', 'subscriptions': {}}
        if os.path.exists('processed_videos.txt'):
            with open('processed_videos.txt', 'r') as f:
                state['processed_videos'] = [line.strip() for line in f if line.strip()]
        if os.path.exists('last_check.txt'):
            with open('last_check.txt', 'r') as f:
                state['last_check'] = f.read().strip()
        if os.path.exists('subscriptions.json'):
            with open('subscriptions.json', 'r') as f:
                try: state['subscriptions'] = json.load(f)
                except: pass

        data = json.dumps(state, ensure_ascii=False).encode('utf-8')
        url = "https://blob.vercel-storage.com/state/state.json"
        req = r.Request(url, data=data, method='PUT', headers={
            'Authorization': f'Bearer {token}',
            'x-api-version': '1',
            'x-add-random-suffix': '0',
            'content-type': 'application/json'
        })
        r.urlopen(req)
        print("✅ 狀態已打包上傳至 state.json")
    except Exception as e:
        print(f"❌ 狀態打包上傳失敗: {e}")

def main():
    if len(sys.argv) < 2: return
    action = sys.argv[1]

    if action == "restore":
        dl_state()
    elif action == "persist":
        # 這裡可以保留原本的個別上傳 (Simple Ops 是免費且無上限的)
        # 但我們主要透過 up_state 確保資料一致性
        up_state()


if __name__ == "__main__":
    main()
