import subprocess
import uuid
import re
import json
import os

class NotebookService:
    """
    /// NotebookLM CLI 封裝模組
    /// 負責與 nlm 指令互動，執行摘要產出與清理
    """

    @staticmethod
    def run_nlm(*args, verbose=True):
        """
        /// 執行 nlm 指令並確保路徑環境正確
        """
        home = os.path.expanduser("~")
        config_dir = os.path.join(home, ".notebooklm-mcp-cli")
        env = os.environ.copy()
        env["NLM_CONFIG_DIR"] = config_dir
        
        cmd = ["nlm", *args]
        res = subprocess.run(cmd, capture_output=True, text=True, env=env)
        
        if verbose and res.returncode != 0:
            print(f"❌ 指令執行失敗: {' '.join(cmd)}")
            if res.stdout: print(f"STDOUT: {res.stdout.strip()}")
            if res.stderr: print(f"STDERR: {res.stderr.strip()}")
        return res

    def process_video(self, url, title, custom_prompt=None):
        """
        /// 完整處理一個影片的摘要流程
        """
        nb_name = f"YT_{uuid.uuid4().hex[:4].upper()}"
        nb_id = None
        summary = None
        
        try:
            # 1. 建立筆記本
            print(f"📁 正在建立筆記本: {nb_name}...")
            res = self.run_nlm("notebook", "create", nb_name)
            if res.returncode == 0:
                match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
                nb_id = match.group(1) if match else nb_name
                print(f"✅ 筆記本建立成功 (ID: {nb_id})")
            else:
                return None
            
            # 2. 新增來源
            print(f"🔗 正在新增來源: {url}...")
            self.run_nlm("source", "add", nb_id, "--url", url)
            
            # 3. 產出摘要
            print("📝 正在產出摘要...")
            prompt = custom_prompt or "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
            res = self.run_nlm("query", "notebook", nb_id, prompt)
            
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    summary = data.get("value", {}).get("answer", res.stdout)
                except:
                    summary = res.stdout.strip()
        finally:
            if nb_id:
                print(f"🧹 正在刪除暫存筆記本: {nb_id}...")
                self.run_nlm("notebook", "delete", nb_id, "--confirm")
        
        return summary

    def process_slide(self, url, title, custom_prompt=None, slide_format="pdf", slide_lang="zh-TW"):
        """
        /// 完整處理一個影片的簡報生成流程
        """
        import time
        nb_name = f"SLIDE_{uuid.uuid4().hex[:4].upper()}"
        nb_id = None
        pdf_path = None
        
        try:
            # 1. 建立筆記本
            print(f"📁 正在建立筆記本: {nb_name}...")
            res = self.run_nlm("notebook", "create", nb_name)
            if res.returncode == 0:
                match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
                nb_id = match.group(1) if match else nb_name
                print(f"✅ 筆記本建立成功 (ID: {nb_id})")
            else:
                return None
            
            # 2. 新增來源並等待處理完成
            print(f"🔗 正在新增來源並等待處理: {url}...")
            self.run_nlm("source", "add", nb_id, "--url", url, "--wait")
            
            # 3. 觸發生成簡報 (語言: 使用傳入參數)
            print(f"🎨 正在請求生成簡報 (語言: {slide_lang}, 格式: {slide_format})...")
            
            # 使用正確的 --language 參數，並將 custom_prompt 傳入 --focus
            # 優化：使用 presenter_slides 且長度為 short 以加快生成速度
            cmd_args = [
                "slides", "create", nb_id, 
                "--language", slide_lang, 
                "--format", "presenter_slides",
                "--length", "short",
                "--confirm"
            ]
            if custom_prompt:
                cmd_args.extend(["--focus", custom_prompt])
            
            create_res = self.run_nlm(*cmd_args)
            
            if create_res.returncode != 0:
                print("❌ 簡報生成請求失敗")
                return None

            # 4. 輪詢直到完成 (最多等待 20 分鐘 = 60次 * 20秒)
            artifact_id = None
            print("⏳ 正在等待簡報製作完成 (此步驟可能需要 1-10 分鐘)...")
            for i in range(60):
                time.sleep(20)
                status_res = self.run_nlm("studio", "status", nb_id, "--json", verbose=False)
                
                raw_out = status_res.stdout.strip() if status_res.stdout else ""
                
                if status_res.returncode == 0 and raw_out:
                    try:
                        status_data = json.loads(raw_out)
                        if not isinstance(status_data, list):
                            print(f"  ({i+1}/30) 收到非預期格式: {raw_out[:50]}...")
                            continue

                        current_status = "UNKNOWN"
                        # 邏輯優化：只要有 type 為 slide_deck 的項目，就檢查其狀態
                        for art in status_data:
                            # 網頁版有時會回傳多個 artifact，我們要找的是 slide_deck
                            if art.get("type") == "slide_deck":
                                current_status = art.get("status")
                                if current_status == "completed":
                                    artifact_id = art.get("id")
                                    print(f"✨ 簡報製作完成! Artifact ID: {artifact_id}")
                                    break
                                elif current_status == "failed":
                                    print(f"❌ 簡報製作失敗: {art.get('error_message', '原因不明')}")
                                    return None
                        
                        if artifact_id: break
                        print(f"  ({i+1}/30) 目前狀態: {current_status}...")
                    except BaseException as e:
                        print(f"  ({i+1}/30) 解析失敗: {e} | 原始輸出: {raw_out[:50]}...")
                else:
                    # 如果 raw_out 是空的，可能是暫時抓不到資料，繼續輪詢
                    print(f"  ({i+1}/30) 正在獲取狀態... (Code: {status_res.returncode})")
                    if status_res.stderr: print(f"    DEBUG: {status_res.stderr.strip()[:60]}")
            
            # 5. 下載檔案
            if artifact_id:
                ext = "pptx" if slide_format == "pptx" else "pdf"
                out_path = f"slide_{nb_name}.{ext}"
                print(f"📥 正在下載簡報檔案 ({ext}): {out_path}...")
                down_res = self.run_nlm(
                    "download", "slide-deck", nb_id, 
                    "--id", artifact_id,
                    "--output", out_path,
                    "--format", ext
                )
                if down_res.returncode == 0 and os.path.exists(out_path):
                    pdf_path = out_path
                    print("✅ 下載成功")
                else:
                    print("❌ 檔案載入失敗")
            else:
                print("⏰ 簡報生成超時")

        finally:
            if nb_id:
                print(f"🧹 正在刪除暫存筆記本: {nb_id}...")
                self.run_nlm("notebook", "delete", nb_id, "--confirm")
        
        return pdf_path
