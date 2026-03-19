import subprocess
import uuid
import re
import json
import os
import time
import requests
import urllib.parse
from api.utils.prompt_manager import get_nlm_prompt


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
            if res.stderr:
                print(f"--- 🛑 系統錯誤輸出 (STDERR) ---")
                print(res.stderr.strip())
            if res.stdout:
                print(f"--- 💡 指令回傳訊息 (STDOUT) ---")
                print(res.stdout.strip())
        return res

    def _add_source_with_proxy(self, nb_id, url, wait=False):
        """
        /// 核心代理匯入邏輯：套用多重代理策略確保成功率
        /// 回傳 True/False
        # 策略辨識
        wait_flag = [] # 拿掉內建的 --wait，統一由外部手動 Polling 以免 30s timeout
        hard_domains = ["forum.gamer.com.tw", "ptt.cc", "bilibili.com", "x.com", "twitter.com", "patreon.com"]
        js_heavy_domains = ["patreon.com", "x.com", "twitter.com"] # 這些網站 Jina 抓不準，強制用 Puppeteer

        is_hard_domain = any(domain in url for domain in hard_domains)
        is_js_heavy = any(domain in url for domain in js_heavy_domains)
        success = False

        # 策略 1: 直接連線
        if not is_hard_domain:
            print(f"嘗試策略 1: 直接連線...")
            res_add = self.run_nlm("source", "add", nb_id, "--url", url, *wait_flag)
            if res_add.returncode == 0: 
                print("✅ 策略 1 成功")
                success = True

        # 策略 2: Jina Reader
        if not success and not is_js_heavy:
            print(f"嘗試策略 2: Jina Reader...")
            encoded_url = urllib.parse.quote(url, safe="")
            proxy_url = f"https://r.jina.ai/{encoded_url}"
            res_add = self.run_nlm("source", "add", nb_id, "--url", proxy_url, *wait_flag)
            if res_add.returncode == 0: 
                print("✅ 策略 2 成功")
                success = True


        # 策略 3: Cloudflare Proxy
        if not success:
            print(f"嘗試策略 3: Cloudflare Proxy (Puppeteer)...")
            cf_worker_url = "https://lazypipe-worker.hsieh130.workers.dev/"
            try:
                encoded_url = urllib.parse.quote(url, safe="")
                cf_res = requests.get(f"{cf_worker_url}?url={encoded_url}", timeout=30)
                cf_data = cf_res.json()
                content = cf_data.get("content", "")
                if cf_data.get("success") and content:
                    print(f"✅ CF Worker 抓取成功，內容長度: {len(content)}")
                    tmp_txt = f"/tmp/{uuid.uuid4().hex[:8]}.txt"
                    with open(tmp_txt, "w", encoding="utf-8") as f:
                        f.write(f"標題: {cf_data.get('title', '未知')}\n\n{content}")
                    res_add = self.run_nlm("source", "add", nb_id, "--file", tmp_txt, *wait_flag)
                    if res_add.returncode == 0: 
                        print("✅ 策略 3 成功")
                        success = True
                else:
                    print(f"⚠️ CF Worker 回傳失敗: {cf_data.get('error', '未知錯誤')}")
            except Exception as e: 
                print(f"❌ 策略 3 發生異常: {e}")

        # 策略 4: Google Translate Proxy
        if not success:
            print(f"嘗試策略 4: Google Translate Proxy...")
            encoded_url = urllib.parse.quote(url, safe="")
            gt_url = f"https://translate.google.com/translate?sl=auto&tl=zh-TW&u={encoded_url}"
            res_add = self.run_nlm("source", "add", nb_id, "--url", gt_url, *wait_flag)
            if res_add.returncode == 0: 
                print("✅ 策略 4 成功")
                success = True
            
        return success

    def _prepare_notebook(self, url: str, prefix: str = "YT", wait: bool = False):
        """
        /// 共用的筆記本準備流程
        """
        nb_name = f"{prefix}_{uuid.uuid4().hex[:4].upper()}"
        print(f"📁 正在建立筆記本: {nb_name}...")
        res = self.run_nlm("notebook", "create", nb_name)
        if res.returncode != 0: return None, None
        
        match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
        nb_id = match.group(1) if match else nb_name
        print(f"✅ 筆記本建立成功 (ID: {nb_id})")

        if self._add_source_with_proxy(nb_id, url, wait=False):
            if wait:
                print("⏳ 正在等待來源內容解析...")
                start_time = time.time()
                is_ready = False
                while time.time() - start_time < 120:
                    status_res = self.run_nlm("source", "list", nb_id, "--json", verbose=False)
                    if status_res.returncode == 0:
                        try:
                            sources = json.loads(status_res.stdout)
                            if isinstance(sources, list) and len(sources) > 0:
                                is_ready = True
                                break
                        except:
                            pass
                    time.sleep(3)
                if not is_ready:
                    print("⚠️ 來源內容解析超時，嘗試繼續產出流程...")
            return nb_id, url
        else:
            print("❌ 所有代理嘗試均失敗。")
            return nb_id, None

    def process_batch(self, urls: list, custom_prompt: str = None):
        """
        /// 完整處理批次網址的摘要流程
        """
        nb_id = None
        try:
            nb_name = f"BATCH_{uuid.uuid4().hex[:4].upper()}"
            res = self.run_nlm("notebook", "create", nb_name)
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if match else nb_name
            
            success_count = 0
            for url in urls:
                url = url.strip()
                if not url: continue
                print(f"🔗 正在批次加入來源: {url}...")
                if self._add_source_with_proxy(nb_id, url, wait=False):
                    success_count += 1
            
            if success_count == 0:
                return "❌ 所有網址匯入均失敗。"

            print(f"📝 正在產出整合摘要 (成功數: {success_count})...")
            
            # 使用與 /nlm 相同的預設 Prompt
            user_intent = get_nlm_prompt(custom_prompt)
            
            # 格式強制指令僅作為輔助後綴，不覆蓋使用者意圖
            format_rules = (
                "\n\n【回答規範：請完全以「繁體中文」回答。直接輸出回答內容，嚴禁包含任何思考過程、步驟說明或 meta 評論 (如 **Thinking** 或 **Summarizing**)。嚴禁包含任何前言或結語。】"
            )
            final_prompt = f"{user_intent}{format_rules}"
            
            res = self.run_nlm("query", "notebook", nb_id, final_prompt)
            
            summary = res.stdout.strip()
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    summary = data.get("value", {}).get("answer", res.stdout)
                except: pass
            
            # 強力過濾：移除所有被 ** 包裹的區塊 (通常是模型自帶的標題或思考過程)
            # 先移除常見的 Meta-talk 區塊
            summary = re.sub(r'\*\*(Thinking|Summarizing|Analysis|Thought|思考過程|摘要中|分析中)\*\*[\s\n]*', '', summary, flags=re.IGNORECASE)
            # 再將剩餘的 **文字** 轉為 文字 (保留內容但移除標記，符合使用者禁用 Markdown 加粗的要求)
            summary = re.sub(r'\*\*(.*?)\*\*', r'\1', summary).strip()
            
            # 如果結果仍包含大量英文 meta 詞彙且沒有中文，則視為失敗
            if len(summary) > 20 and not re.search(r'[\u4e00-\u9fa5]', summary) and ("I am" in summary or "distilling" in summary):
                summary = "❌ AI 回傳了無效的思考過程而非內容。這通常發生在來源過於破碎時，請嘗試減少網址數量或更換 Prompt。"

            return summary
        finally:
            if nb_id:
                print(f"🧹 正在刪除暫存筆記本: {nb_id}...")
                self.run_nlm("notebook", "delete", nb_id, "--confirm")

    def process_video(self, url, title, custom_prompt=None):
        """
        /// 完整處理一個影片的摘要流程
        """
        nb_id = None
        summary = None

        try:
            nb_id, effective_url = self._prepare_notebook(url, prefix="YT", wait=False)
            if nb_id is None:
                return None
            if effective_url is None:
                msg = "❌ 所有代理嘗試均失敗，無法讀取網址內容。這通常是因為來源網站阻擋了自動化抓取，建議嘗試手動將網頁存為 PDF 後上傳。"
                print(msg)
                return msg

            print("📝 正在產出摘要...")
            prompt = get_nlm_prompt(custom_prompt)
            res = self.run_nlm("query", "notebook", nb_id, prompt)

            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    summary = data.get("value", {}).get("answer", res.stdout)
                except Exception:
                    summary = res.stdout.strip()
                
                # 強力過濾：移除所有被 ** 包裹的區塊 (通常是模型自帶的標題或思考過程)
                # 先移除常見的 Meta-talk 區塊
                summary = re.sub(r'\*\*(Thinking|Summarizing|Analysis|Thought|思考過程|摘要中|分析中)\*\*[\s\n]*', '', summary, flags=re.IGNORECASE)
                # 再將剩餘的 **文字** 轉為 文字 (保留內容但移除標記，符合使用者禁用 Markdown 加粗的要求)
                summary = re.sub(r'\*\*(.*?)\*\*', r'\1', summary).strip()
                
                # 如果結果仍包含大量英文 meta 詞彙且沒有中文，則視為失敗
                if summary and len(summary) > 20 and not re.search(r'[\u4e00-\u9fa5]', summary) and ("I am" in summary or "distilling" in summary):
                    summary = "❌ AI 回傳了無效的思考過程而非內容。請嘗試更換 Prompt。"
        finally:
            if nb_id:
                print(f"🧹 正在刪除暫存筆記本: {nb_id}...")
                self.run_nlm("notebook", "delete", nb_id, "--confirm")

        return summary

    def process_artifact(self, url: str, title: str, artifact_type: str = "slide_deck", custom_prompt: str = None, **kwargs):
        """
        /// 完整處理一個影片的 Artifact 生成流程 (Slide, Infographic, Report)
        /// artifact_type: 'slide_deck', 'infographic', 'report'
        """
        prefix = artifact_type.upper()
        nb_id = None
        target_path = None

        try:
            nb_id, effective_url = self._prepare_notebook(url, prefix=prefix, wait=True)
            if nb_id is None:
                return None
            if effective_url is None:
                print("❌ 所有代理嘗試均失敗，無法讀取網址內容，無法生成 Artifact。")
                return None

            print(f"🎨 正在請求生成 {artifact_type}...")

            cmd_args = []
            if artifact_type == "slide_deck":
                slide_lang = kwargs.get("slide_lang", "zh-TW")
                cmd_args = [
                    "slides", "create", nb_id,
                    "--language", slide_lang,
                    "--format", "presenter_slides",
                    "--length", "short",
                    "--json",
                    "--confirm"
                ]
                if custom_prompt:
                    cmd_args.extend(["--focus", get_nlm_prompt(custom_prompt)])
            elif artifact_type == "infographic":
                lang = kwargs.get("language", "zh-TW")
                orientation = kwargs.get("orientation", "portrait")
                detail = kwargs.get("detail", "detailed")
                cmd_args = [
                    "infographic", "create", nb_id,
                    "--language", lang,
                    "--orientation", orientation,
                    "--detail", detail,
                    "--json",
                    "--confirm"
                ]
                if custom_prompt:
                    cmd_args.extend(["--focus", get_nlm_prompt(custom_prompt)])
            elif artifact_type == "report":
                lang = kwargs.get("language", "zh-TW")
                cmd_args = [
                    "report", "create", nb_id,
                    "--language", lang,
                    "--format", "Create Your Own",
                    "--json",
                    "--confirm"
                ]
                cmd_args.extend(["--prompt", get_nlm_prompt(custom_prompt or "請用繁體中文提供詳細的內容摘要報告")])

            create_res = self.run_nlm(*cmd_args)

            if create_res.returncode != 0:
                print(f"❌ {artifact_type} 生成請求失敗")
                return None

            # 解析生成的 Artifact ID
            artifact_id = None
            try:
                out_data = json.loads(create_res.stdout)
                artifact_id = out_data.get("id") or out_data.get("artifact_id")
                if not artifact_id and isinstance(out_data, dict):
                    # 嘗試從文字中解析 (防備 JSON 結構變動)
                    match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", create_res.stdout)
                    artifact_id = match.group(1) if match else None
            except:
                match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", create_res.stdout)
                artifact_id = match.group(1) if match else None

            if artifact_id:
                if artifact_type == "slide_deck":
                    ext = kwargs.get("slide_format", "pdf")
                    subcmd = "slide-deck"
                elif artifact_type == "infographic":
                    ext = "png"
                    subcmd = "infographic"
                elif artifact_type == "report":
                    ext = "md"
                    subcmd = "report"
                else:
                    ext = "txt"
                    subcmd = "artifact"

                out_path = f"{artifact_type}_{uuid.uuid4().hex[:4]}.{ext}"
                
                print(f"⏳ 正在等待產出物生成，此過程可能長達 1 ~ 3 分鐘...")
                start_time = time.time()
                is_ready = False
                
                # 每 10 秒輪詢一次，最多等 5 分鐘
                while time.time() - start_time < 300:
                    status_res = self.run_nlm("studio", "status", nb_id, "--json", verbose=False)
                    if status_res.returncode == 0:
                        try:
                            stats = json.loads(status_res.stdout)
                            if isinstance(stats, list):
                                for artifact in stats:
                                    # 比對 id (可能是 id 或 artifact_id)
                                    curr_id = artifact.get("id") or artifact.get("artifact_id")
                                    if curr_id == artifact_id:
                                        status = str(artifact.get("status", "")).lower()
                                        if status in ["completed", "success", "2"]:
                                            is_ready = True
                                        elif status in ["failed", "4"]:
                                            print(f"❌ {artifact_type} 生成失敗 (模型遭拒或建立失敗)")
                                            return None
                                        break
                        except:
                            pass
                    
                    if is_ready:
                        break
                    time.sleep(10)
                
                if not is_ready:
                    print(f"⏰ {artifact_type} 生成超時 (超過 5 分鐘)")
                    return None

                print(f"📥 正在下載檔案 ({ext}): {out_path}...")
                down_args = ["download", subcmd, nb_id, "--id", artifact_id, "--output", out_path]
                if artifact_type == "slide_deck":
                    down_args.extend(["--format", ext])

                down_res = self.run_nlm(*down_args)
                if down_res.returncode == 0 and os.path.exists(out_path):
                    target_path = out_path
                    print("✅ 下載成功")
                else:
                    print("❌ 檔案下載失敗")
            else:
                print("❌ 無法取得 Artifact ID，可能是 API 發生異常")

        finally:
            if nb_id:
                print(f"🧹 正在刪除暫存筆記本: {nb_id}...")
                self.run_nlm("notebook", "delete", nb_id, "--confirm")

        return target_path
