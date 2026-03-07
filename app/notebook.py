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

    def process_slide(self, url, title, custom_prompt=None):
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
            
            # 3. 觸發生成簡報
            print("🎨 正在請求生成簡報...")
            cmd_args = ["slides", "create", nb_id, "--confirm"]
            if custom_prompt:
                cmd_args.extend(["--focus", custom_prompt])
            create_res = self.run_nlm(*cmd_args)
            
            if create_res.returncode != 0:
                print("❌ 簡報生成請求失敗")
                return None

            # 4. 輪詢直到完成 (最多等待 10 分鐘 = 30次 * 20秒)
            artifact_id = None
            print("⏳ 正在等待簡報製作完成 (此步驟可能需要 1-5 分鐘)...")
            for i in range(30):
                time.sleep(20)
                status_res = self.run_nlm("studio", "status", nb_id, "--json", verbose=False) # 輪詢就不 verbose 了
                if status_res.returncode == 0:
                    try:
                        # 解析 JSON 輸出
                        status_data = json.loads(status_res.stdout)
                        for art in status_data:
                            # 判斷是否為剛建立的 slide_deck 且狀態為 DONE
                            if art.get("artifact_type") == "slide_deck":
                                if art.get("status") == "DONE":
                                    artifact_id = art.get("artifact_id")
                                    print(f"✨ 簡報製作完成! Artifact ID: {artifact_id}")
                                    break
                                elif art.get("status") == "ERROR":
                                    print(f"❌ 簡報製作失敗，狀態顯示為 ERROR")
                                    return None
                        if artifact_id: break
                        print(f"  ({i+1}/30) 仍然處理中...")
                    except BaseException as e:
                        print(f"  ({i+1}/30) 無法解析狀態: {e}")
                else:
                    print(f"  ({i+1}/30) 查詢狀態失敗")
            
            # 5. 下載檔案
            if artifact_id:
                out_path = f"slide_{nb_name}.pdf"
                print(f"📥 正在下載簡報檔案: {out_path}...")
                down_res = self.run_nlm("download", "slide-deck", nb_id, artifact_id, "--output", out_path)
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
