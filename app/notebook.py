import subprocess
import uuid
import re
import json
import os
import time
import requests
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from api.utils.prompt_manager import get_nlm_prompt


class NotebookService:
    """
    /// NotebookLM CLI 封裝模組
    /// 負責與 nlm 指令互動，執行摘要產出與清理
    """

    @staticmethod
    def run_nlm(*args, verbose=True, max_retries=3):
        """
        /// 執行 nlm 指令並確保路徑環境正確，具備自動重試機制
        """
        home = os.path.expanduser("~")
        config_dir = os.path.join(home, ".config", "notebooklm-mcp-cli")
        
        env = os.environ.copy()
        # 同時設定新舊版本可能使用的環境變數
        env["NOTEBOOKLM_MCP_CLI_PATH"] = config_dir
        env["NLM_CONFIG_DIR"] = config_dir
        env["XDG_CONFIG_HOME"] = os.path.join(home, ".config") # 模擬 Linux 標準配置
        # 額外顯式指定憑證路徑
        env["NLM_AUTH_JSON"] = os.path.join(config_dir, "profiles", "default", "auth.json")

        cmd = ["nlm", *args]
        
        last_res = None
        for attempt in range(max_retries):
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            last_res = res
            
            if res.returncode == 0:
                return res
            
            # 檢查是否為可重試的錯誤 (例如 429, Timeout 或特定頻繁失敗字串)
            error_msg = (res.stderr or res.stdout or "").lower()
            retryable = any(k in error_msg for k in ["429", "too many requests", "timeout", "busy", "limit"])
            
            if retryable and attempt < max_retries - 1:
                wait_time = (2 ** attempt) + 1
                if verbose:
                    print(f"⚠️ 指令執行繁忙 (Attempt {attempt+1}/{max_retries}), {wait_time}s 後重試...")
                time.sleep(wait_time)
                continue
            break

        if verbose and last_res and last_res.returncode != 0:
            print(f"❌ 指令執行失敗: {' '.join(cmd)}")
            if last_res.stderr:
                print(f"--- 🛑 系統錯誤輸出 (STDERR) ---")
                print(last_res.stderr.strip())
            if last_res.stdout:
                print(f"--- 💡 指令回傳訊息 (STDOUT) ---")
                print(last_res.stdout.strip())
        return last_res

    def _clean_content(self, text):
        """
        /// 清理網頁抓取到的雜訊內容，提升 AI 分析精準度
        """
        if not text: return ""
        
        # 1. 移除常見的網頁導航與政策關鍵字 (Case-insensitive)
        noise_patterns = [
            r"Cookie Policy", r"Terms of Service", r"Privacy Policy",
            r"Subscribe to", r"Follow us on", r"All rights reserved",
            r"Skip to main content", r"Log in", r"Sign up", r"Copyright ©"
        ]
        for p in noise_patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
            
        # 2. 移除連續多個換行與多餘空白，讓文本更緊湊
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        
        # 3. 逐行過濾：移除過短或 URL 佔比過高的無效行 (通常是選單或側邊欄)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) < 10: continue # 略過短句
            
            # 如果一行內包含 2 個以上 URL 且長度不長，高度懷疑是導覽連結
            url_count = len(re.findall(r'https?://', line))
            if url_count >= 2 and len(line) < 150: continue
            
            cleaned_lines.append(line)
            
        return "\n".join(cleaned_lines)

    def _add_source_with_proxy(self, nb_id, url, wait=False):
        """
        /// 核心代理匯入邏輯：套用多重代理策略確保成功率
        /// 回傳 True/False
        """
        # 策略辨識
        wait_flag = [] # 拿掉內建的 --wait，統一由外部手動 Polling 以免 30s timeout
        hard_domains = ["forum.gamer.com.tw", "ptt.cc", "bilibili.com", "x.com", "twitter.com", "patreon.com"]
        js_heavy_domains = ["patreon.com", "x.com", "twitter.com"] # 這些網站 Jina 抓不準，強制用 Puppeteer

        is_hard_domain = any(domain in url for domain in hard_domains)
        is_js_heavy = any(domain in url for domain in js_heavy_domains)
        success = False

        # 策略 1: 直接連線
        if not is_hard_domain:
            res_add = self.run_nlm("source", "add", nb_id, "--url", url, *wait_flag)
            if res_add.returncode == 0: 
                success = True

        # 策略 2: Jina Reader
        if not success and not is_js_heavy:
            encoded_url = urllib.parse.quote(url, safe="")
            proxy_url = f"https://r.jina.ai/{encoded_url}"
            res_add = self.run_nlm("source", "add", nb_id, "--url", proxy_url, *wait_flag)
            if res_add.returncode == 0: 
                success = True

        # 策略 3: Cloudflare Proxy
        if not success:
            cf_worker_url = "https://lazypipe-worker.hsieh130.workers.dev/"
            try:
                encoded_url = urllib.parse.quote(url, safe="")
                cf_res = requests.get(f"{cf_worker_url}?url={encoded_url}", timeout=30)
                cf_data = cf_res.json()
                content = cf_data.get("content", "")
                if cf_data.get("success") and content:
                    # 進行內容清洗 (優化 #4)
                    cleaned_content = self._clean_content(content)
                    print(f"✅ CF Worker 抓取成功 (原始: {len(content)} -> 清洗後: {len(cleaned_content)})")

                    tmp_txt = f"/tmp/{uuid.uuid4().hex[:8]}.txt"
                    with open(tmp_txt, "w", encoding="utf-8") as f:
                        f.write(f"標題: {cf_data.get('title', '未知')}\n\n{cleaned_content}")
                    res_add = self.run_nlm("source", "add", nb_id, "--file", tmp_txt, *wait_flag)
                    if res_add.returncode == 0: 
                        success = True

                        # 額外嘗試：如果內容中有 YouTube 連結，一併加入來源增加上下文
                        yt_match = re.search(r'(https?://(?:www\.)?(?:youtube\.com/watch\?v=|youtu\.be/)[a-zA-Z0-9_-]+)', cleaned_content)
                        if yt_match:
                            yt_url = yt_match.group(1)
                            self.run_nlm("source", "add", nb_id, "--url", yt_url, *wait_flag)
            except: 
                pass

        # 策略 4: Google Translate Proxy
        if not success:
            encoded_url = urllib.parse.quote(url, safe="")
            gt_url = f"https://translate.google.com/translate?sl=auto&tl=zh-TW&u={encoded_url}"
            res_add = self.run_nlm("source", "add", nb_id, "--url", gt_url, *wait_flag)
            if res_add.returncode == 0: 
                success = True

            
        return success

    def _prepare_notebook(self, url: str, prefix: str = "YT", wait: bool = False):
        """
        /// 共用的筆記本準備流程
        """
        # 1. 預處理 URL (移除 YouTube 的 si, t 參數等雜訊，提高匯入成功率)
        if "youtube.com" in url or "youtu.be" in url:
            try:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                # 移除特定雜訊參數
                params.pop('si', None)
                params.pop('t', None)
                # 重新組合
                new_query = urllib.parse.urlencode(params, doseq=True)
                url = urllib.parse.urlunparse(parsed._replace(query=new_query))
                print(f"🧹 URL 已清理: {url}")
            except Exception as e:
                print(f"⚠️ URL 清理失敗: {e}")

        nb_name = f"{prefix}_{uuid.uuid4().hex[:4].upper()}"
        print(f"📁 正在建立筆記本: {nb_name}...")
        res = self.run_nlm("notebook", "create", nb_name)
        if res.returncode != 0:
            error_msg = res.stderr or res.stdout or "未知錯誤"
            return None, f"❌ 建立筆記本失敗: {error_msg}"
        
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
                                all_done = True
                                for s in sources:
                                    s_status = str(s.get("status", "")).lower()
                                    # 檢查常見的成功狀態字串或代碼
                                    if s_status not in ["completed", "success", "2"]:
                                        all_done = False
                                        break
                                if all_done:
                                    is_ready = True
                                    break
                        except:
                            pass
                    time.sleep(5)
                if is_ready:
                    print("✅ 來源內容解析完成。")
                else:
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
            if res.returncode != 0:
                return f"❌ 建立批次筆記本失敗: {res.stderr or res.stdout or '未知錯誤'}"

            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if match else nb_name
            
            # 使用並行匯入 (優化 #1)
            print(f"🔗 正在啟動並行匯入流程 (網址數: {len(urls)})...")
            with ThreadPoolExecutor(max_workers=5) as executor:
                # 建立任務映射
                futures = {executor.submit(self._add_source_with_proxy, nb_id, url.strip()): url for url in urls if url.strip()}
                
                success_count = 0
                for future in as_completed(futures):
                    url = futures[future]
                    try:
                        if future.result():
                            print(f"✅ 匯入成功: {url}")
                            success_count += 1
                        else:
                            print(f"❌ 匯入失敗: {url}")
                    except Exception as e:
                        print(f"❌ 匯入過程發生異常 ({url}): {e}")
            
            if success_count == 0:
                return "❌ 所有網址匯入均失敗。"

            # 補強：批次處理通常內容較多，強制等待解析完成
            print(f"⏳ 正在等待 {success_count} 個來源內容解析完成...")
            start_time = time.time()
            is_ready = False
            while time.time() - start_time < 180: # 批次給予較長等待時間 (3分鐘)
                status_res = self.run_nlm("source", "list", nb_id, "--json", verbose=False)
                if status_res.returncode == 0:
                    try:
                        sources = json.loads(status_res.stdout)
                        if isinstance(sources, list) and len(sources) > 0:
                            all_done = True
                            for s in sources:
                                s_status = str(s.get("status", "")).lower()
                                if s_status not in ["completed", "success", "2"]:
                                    all_done = False
                                    break
                            if all_done:
                                is_ready = True
                                break
                    except: pass
                time.sleep(5)
            
            if not is_ready:
                print("⚠️ 部分來源解析超時，嘗試繼續產出整合摘要...")

            print(f"📝 正在產出整合摘要 (成功數: {success_count})...")
            
            # 使用與 /nlm 相同的預設 Prompt
            user_intent = get_nlm_prompt(custom_prompt)
            
            # 格式強制指令僅作為輔助後綴，不覆蓋使用者意圖
            format_rules = (
                "\n\n【回答規範：請完全以「繁體中文」回答。直接輸出回答內容，嚴禁包含任何思考過程、步驟說明或 meta 評論 (如 **Thinking** 或 **Summarizing**)。嚴禁包含任何前言或結語。】"
            )
            final_prompt = f"{user_intent}{format_rules}"
            
            res = self.run_nlm("query", "notebook", nb_id, final_prompt)
            
            if res.returncode != 0:
                return f"❌ 批次摘要產出失敗: {res.stderr or res.stdout or '未知錯誤'}"

            summary = res.stdout.strip()
            try:
                data = json.loads(res.stdout)
                summary = data.get("value", {}).get("answer", res.stdout)
            except: pass
            
            # 強力過濾：移除所有被 ** 包裹的區塊 (通常是模型自帶的標題或思考過程)
            # 先移除常見的 Meta-talk 區塊
            summary = re.sub(r'\*\*(Thinking|Summarizing|Analysis|Thought|思考過程|摘要中|分析中)\*\*[\s\n]*', '', summary, flags=re.IGNORECASE)
            # 再將剩餘的 **文字** 轉為 文字 (保留內容)
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
            is_youtube = "youtube.com" in url or "youtu.be" in url
            # 修正：除了 YouTube 以外的網頁內容（如 Patreon, 財經新聞），通常需要較長索引時間，強制等待 (wait=True)
            wait_needed = not is_youtube or "batch" in title.lower()
            nb_id, effective_url = self._prepare_notebook(url, prefix="YT", wait=wait_needed)
            
            # 如果 nb_id 是 None，代表筆記本建立就失敗了 (effective_url 在這種情況下會是錯誤訊息)
            if nb_id is None:
                return effective_url
                
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
                    summary = "❌ AI 回傳了無效的思考過程而非內容。請嘗試更換 Prompt 或檢查來源內容。"
            else:
                summary = f"❌ 摘要產出失敗: {res.stderr or res.stdout or '未知錯誤'}"
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
                return effective_url # 這邊 effective_url 已經是包含 ❌ 的錯誤訊息
            if effective_url is None:
                return "❌ 所有代理嘗試均失敗，無法讀取網址內容，無法生成內容。建議嘗試手動將網頁存為 PDF 後上傳。"

            print(f"🎨 正在請求生成 {artifact_type}...")

            cmd_args = []
            if artifact_type == "slide_deck":
                slide_lang = kwargs.get("slide_lang", "zh-TW")
                cmd_args = [
                    "slides", "create", nb_id,
                    "--format", "presenter_slides",
                    "--language", slide_lang,
                    "--length", "medium",
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
                    "--confirm"
                ]
                if custom_prompt:
                    cmd_args.extend(["--focus", get_nlm_prompt(custom_prompt)])
            elif artifact_type == "report":
                lang = kwargs.get("language", "zh-TW")
                cmd_args = [
                    "report", "create", nb_id,
                    "--language", lang,
                    "--format", "Professional Report",
                    "--outline",
                    "--confirm"
                ]
                report_prompt = custom_prompt or "請提供一份結構嚴謹、包含目錄、核心論點分析及腳註引用的繁體中文報告。"
                cmd_args.extend(["--prompt", get_nlm_prompt(report_prompt)])

            create_res = self.run_nlm(*cmd_args)

            if create_res.returncode != 0:
                return f"❌ {artifact_type} 生成請求失敗: {create_res.stderr or create_res.stdout or '未知錯誤'}"

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

            print(f"🆔 取得 Artifact ID: {artifact_id}")

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
                                        print(f"📊 目前生成狀態: {status}")
                                        if status in ["completed", "success", "2"]:
                                            is_ready = True
                                        elif status in ["failed", "4"]:
                                            return f"❌ {artifact_type} 生成失敗 (模型遭拒或建立失敗)"
                                        break
                        except:
                            pass
                    
                    if is_ready:
                        break
                    time.sleep(10)
                
                if not is_ready:
                    return f"❌ {artifact_type} 生成超時 (超過 5 分鐘)"

                print(f"📥 正在下載檔案 ({ext}): {out_path}...")
                down_args = ["download", subcmd, nb_id, "--id", artifact_id, "--output", out_path]
                if artifact_type == "slide_deck":
                    down_args.extend(["--format", ext])

                down_res = self.run_nlm(*down_args)
                if down_res.returncode == 0 and os.path.exists(out_path):
                    target_path = out_path
                    print("✅ 下載成功")
                else:
                    return f"❌ 檔案下載失敗: {down_res.stderr or down_res.stdout or '未知錯誤'}"
            else:
                return "❌ 無法取得 Artifact ID，可能是 API 發生異常"

        finally:
            if nb_id:
                print(f"🧹 正在刪除暫存筆記本: {nb_id}...")
                self.run_nlm("notebook", "delete", nb_id, "--confirm")

        return target_path
