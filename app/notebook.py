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
        config_dir = os.path.join(home, ".notebooklm-mcp-cli")
        env = os.environ.copy()
        env["NLM_CONFIG_DIR"] = config_dir

        cmd = ["nlm", *args]
        
        last_res = None
        for attempt in range(max_retries):
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            last_res = res
            
            if res.returncode == 0:
                return res
            
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
            error_msg = (last_res.stderr or last_res.stdout or "").strip()
            print(f"❌ 指令執行失敗: {' '.join(cmd)}")
            if "400 Bad Request" in error_msg:
                print("\n⚠️ 【診斷報告：憑證過期或失效】")
                last_res.stderr = f"憑證可能已過期 (400 Bad Request)\n請重新執行 nlm login --force 並更新 Secret。\n\n原始錯誤：{error_msg}"
            if last_res.stderr:
                print(f"--- 🛑 系統錯誤輸出 (STDERR) ---")
                print(last_res.stderr.strip())
        return last_res

    def _clean_content(self, text):
        """
        /// 清理網頁抓取到的雜訊內容
        """
        if not text: return ""
        noise_patterns = [
            r"Cookie Policy", r"Terms of Service", r"Privacy Policy",
            r"Subscribe to", r"Follow us on", r"All rights reserved",
            r"Skip to main content", r"Log in", r"Sign up", r"Copyright ©"
        ]
        for p in noise_patterns:
            text = re.sub(p, "", text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        text = re.sub(r'[ \t]+', ' ', text)
        lines = text.split('\n')
        cleaned_lines = []
        for line in lines:
            line = line.strip()
            if len(line) < 10: continue
            url_count = len(re.findall(r'https?://', line))
            if url_count >= 2 and len(line) < 150: continue
            cleaned_lines.append(line)
        return "\n".join(cleaned_lines)

    def _add_source_with_proxy(self, nb_id, url, wait=False):
        """
        /// 核心代理匯入邏輯
        """
        wait_flag = []
        hard_domains = ["forum.gamer.com.tw", "ptt.cc", "bilibili.com", "x.com", "twitter.com", "patreon.com"]
        js_heavy_domains = ["patreon.com", "x.com", "twitter.com"]

        is_hard_domain = any(domain in url for domain in hard_domains)
        is_js_heavy = any(domain in url for domain in js_heavy_domains)
        success = False

        if not is_hard_domain:
            res_add = self.run_nlm("source", "add", nb_id, "--url", url, *wait_flag)
            if res_add.returncode == 0: success = True

        if not success and not is_js_heavy:
            encoded_url = urllib.parse.quote(url, safe="")
            proxy_url = f"https://r.jina.ai/{encoded_url}"
            res_add = self.run_nlm("source", "add", nb_id, "--url", proxy_url, *wait_flag)
            if res_add.returncode == 0: success = True

        if not success:
            cf_worker_url = "https://lazypipe-worker.hsieh130.workers.dev/"
            try:
                encoded_url = urllib.parse.quote(url, safe="")
                cf_res = requests.get(f"{cf_worker_url}?url={encoded_url}", timeout=30)
                cf_data = cf_res.json()
                content = cf_data.get("content", "")
                if cf_data.get("success") and content:
                    cleaned_content = self._clean_content(content)
                    tmp_txt = f"/tmp/{uuid.uuid4().hex[:8]}.txt"
                    with open(tmp_txt, "w", encoding="utf-8") as f:
                        f.write(f"標題: {cf_data.get('title', '未知')}\n\n{cleaned_content}")
                    res_add = self.run_nlm("source", "add", nb_id, "--file", tmp_txt, *wait_flag)
                    if res_add.returncode == 0: success = True
            except: pass

        if not success:
            encoded_url = urllib.parse.quote(url, safe="")
            gt_url = f"https://translate.google.com/translate?sl=auto&tl=zh-TW&u={encoded_url}"
            res_add = self.run_nlm("source", "add", nb_id, "--url", gt_url, *wait_flag)
            if res_add.returncode == 0: success = True
        return success

    def _prepare_notebook(self, url: str, prefix: str = "YT", wait: bool = False):
        if "youtube.com" in url or "youtu.be" in url:
            try:
                parsed = urllib.parse.urlparse(url)
                params = urllib.parse.parse_qs(parsed.query)
                params.pop('si', None); params.pop('t', None)
                new_query = urllib.parse.urlencode(params, doseq=True)
                url = urllib.parse.urlunparse(parsed._replace(query=new_query))
            except: pass

        nb_name = f"{prefix}_{uuid.uuid4().hex[:4].upper()}"
        res = self.run_nlm("notebook", "create", nb_name)
        if res.returncode != 0:
            return None, f"❌ 建立筆記本失敗: {res.stderr or res.stdout or '未知錯誤'}"
        
        match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
        nb_id = match.group(1) if match else nb_name

        if self._add_source_with_proxy(nb_id, url, wait=False):
            if wait:
                start_time = time.time()
                while time.time() - start_time < 120:
                    status_res = self.run_nlm("source", "list", nb_id, "--json", verbose=False)
                    if status_res.returncode == 0:
                        try:
                            sources = json.loads(status_res.stdout)
                            if all(str(s.get("status", "")).lower() in ["completed", "success", "2"] for s in sources): break
                        except: pass
                    time.sleep(5)
            return nb_id, url
        return nb_id, None

    def process_batch(self, urls: list, custom_prompt: str = None):
        nb_id = None
        try:
            nb_name = f"BATCH_{uuid.uuid4().hex[:4].upper()}"
            res = self.run_nlm("notebook", "create", nb_name)
            if res.returncode != 0: return f"❌ 建立批次失敗: {res.stderr}"
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if match else nb_name
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(lambda u: self._add_source_with_proxy(nb_id, u.strip()), urls)
            
            # Wait for processing
            time.sleep(15)
            user_intent = get_nlm_prompt(custom_prompt)
            final_prompt = f"{user_intent}\n\n【請完全以繁體中文回答。】"
            res = self.run_nlm("query", "notebook", nb_id, final_prompt)
            if res.returncode != 0: return "❌ 批次摘要失敗"
            return res.stdout.strip()
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

    def process_video(self, url, title, custom_prompt=None):
        nb_id = None
        try:
            is_youtube = "youtube.com" in url or "youtu.be" in url
            nb_id, effective_url = self._prepare_notebook(url, prefix="YT", wait=(not is_youtube))
            if not nb_id: return effective_url
            if not effective_url: return "❌ 無法讀取內容"
            prompt = get_nlm_prompt(custom_prompt)
            res = self.run_nlm("query", "notebook", nb_id, prompt)
            if res.returncode == 0:
                summary = res.stdout.strip()
                summary = re.sub(r'\*\*(Thinking|Summarizing|Analysis|Thought|思考過程)\*\*[\s\n]*', '', summary, flags=re.IGNORECASE)
                return summary.strip()
            return f"❌ 摘要產出失敗"
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

    def process_artifact(self, url: str, title: str, artifact_type: str = "slide_deck", custom_prompt: str = None, **kwargs):
        nb_id = None
        try:
            nb_id, eff_url = self._prepare_notebook(url, prefix=artifact_type.upper(), wait=True)
            if not nb_id or not eff_url: return "❌ 匯入失敗"
            cmd_args = ["slides", "create", nb_id, "--language", "zh-TW", "--confirm"] if artifact_type == "slide_deck" else []
            if artifact_type == "infographic": cmd_args = ["infographic", "create", nb_id, "--language", "zh-TW", "--confirm"]
            if artifact_type == "report": cmd_args = ["report", "create", nb_id, "--language", "zh-TW", "--confirm"]
            if custom_prompt: cmd_args.extend(["--focus", get_nlm_prompt(custom_prompt)])
            res = self.run_nlm(*cmd_args)
            return "✅ Artifact 生成中" if res.returncode == 0 else "❌ 生成失敗"
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

    async def research_topic(self, topic: str, mode: str = "fast"):
        """
        /// 執行深度研究 (Deep Research)
        """
        nb_id = None
        try:
            nb_name = f"RESEARCH_{uuid.uuid4().hex[:4].upper()}"
            res = self.run_nlm("notebook", "create", nb_name)
            if res.returncode != 0: return False, "建立筆記本失敗"
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if match else nb_name

            print(f"🔎 啟動研究代理人 ({mode.upper()}): {topic}")
            start_res = self.run_nlm("research", "start", "--notebook-id", nb_id, "--mode", mode, topic)
            if start_res.returncode != 0: return False, "啟動失敗"

            # 動態頻率：deep 1分鐘, fast 30秒
            interval = 60 if mode == "deep" else 30
            timeout = 1200 if mode == "deep" else 600
            
            print(f"⏳ 正在輪詢研究進度 (每 {interval} 秒一次)...")
            start_time = time.time()
            is_done = False
            while time.time() - start_time < timeout:
                status_res = self.run_nlm("research", "status", nb_id, "--max-wait", "0", verbose=False)
                out = status_res.stdout.strip().lower()
                if any(k in out for k in ["completed", "success", "no active research", "ready to import"]):
                    is_done = True
                    break
                print(f"📊 目前狀態: {out.splitlines()[0] if out else '等待中'}")
                time.sleep(interval)

            if not is_done: return False, f"研究超時 ({timeout//60} 分鐘)"
            self.run_nlm("research", "import", nb_id)
            prompt = f"針對「{topic}」，產出結構完整的繁體中文研究報告。"
            res_query = self.run_nlm("query", "notebook", nb_id, prompt)
            if res_query.returncode == 0:
                summary = res_query.stdout.strip()
                # 強化 JSON 提取邏輯
                try:
                    data = json.loads(summary)
                    if isinstance(data, dict):
                        # 處理 {"value": {"answer": "..."}}
                        if "value" in data and isinstance(data["value"], dict):
                            summary = data["value"].get("answer", summary)
                        # 處理 {"answer": "..."}
                        elif "answer" in data:
                            summary = data["answer"]
                except: pass
                
                summary = re.sub(r'\*\*(Thinking|Thought)\*\*[\s\n]*', '', summary, flags=re.IGNORECASE)
                return True, summary.strip()
            return False, "報告產出失敗"
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

NotebookManager = NotebookService
