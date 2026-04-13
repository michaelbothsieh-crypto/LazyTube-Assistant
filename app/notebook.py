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
    /// NotebookLM CLI 封裝模組 (效能優化版)
    """

    @staticmethod
    def run_nlm(*args, verbose=True, max_retries=3):
        home = os.path.expanduser("~")
        config_dir = os.path.join(home, ".notebooklm-mcp-cli")
        env = os.environ.copy()
        env["NLM_CONFIG_DIR"] = config_dir

        cmd = ["nlm", *args]
        last_res = None
        for attempt in range(max_retries):
            res = subprocess.run(cmd, capture_output=True, text=True, env=env)
            last_res = res
            if res.returncode == 0: return res
            
            error_msg = (res.stderr or res.stdout or "").lower()
            if not any(k in error_msg for k in ["429", "too many requests", "timeout", "busy", "limit"]): break
            
            wait_time = (2 ** attempt) + 1
            if verbose: print(f"⚠️ 繁忙 (Attempt {attempt+1}/{max_retries}), {wait_time}s 後重試...")
            time.sleep(wait_time)

        if verbose and last_res and last_res.returncode != 0:
            err = (last_res.stderr or last_res.stdout or "").strip()
            print(f"❌ 指令失敗: {' '.join(cmd)}\n{err[:200]}")
        return last_res

    def _clean_content(self, text):
        if not text: return ""
        text = re.sub(r"Cookie Policy|Terms of Service|Privacy Policy|Copyright ©", "", text, flags=re.IGNORECASE)
        text = re.sub(r'\n\s*\n', '\n\n', text)
        return text.strip()

    def _add_source_with_proxy(self, nb_id, url, wait=True):
        """
        /// 核心代理匯入邏輯 (強化版)
        """
        wait_flag = ["--wait"] if wait else []
        
        # 1. 快速路徑：YouTube 直接新增
        if "youtube.com" in url or "youtu.be" in url:
            res = self.run_nlm("source", "add", nb_id, "--url", url, *wait_flag)
            if res.returncode == 0: return True

        # 網址標準化：先解碼再編碼，防止雙重編碼問題
        decoded_url = urllib.parse.unquote(url)
        encoded_url = urllib.parse.quote(decoded_url, safe="")

        # 2. 策略路徑：Jina Reader (加上快取穿透)
        proxy_url = f"https://r.jina.ai/{encoded_url}"
        # 透過 run_nlm 呼叫時，NotebookLM 會去抓取 Jina 的結果
        res = self.run_nlm("source", "add", nb_id, "--url", proxy_url, *wait_flag)
        if res.returncode == 0: return True

        # 3. 備援路徑：Cloudflare Worker (Puppeteer 渲染)
        try:
            print(f"📡 Jina 失敗，啟動備援爬蟲：{decoded_url[:50]}...")
            # 增加超時時間至 40 秒，因為 Puppeteer 啟動較慢
            cf_res = requests.get(f"https://lazypipe-worker.hsieh130.workers.dev/?url={encoded_url}", timeout=40)
            if cf_res.status_code == 200:
                resp_json = cf_res.json()
                if resp_json.get("success"):
                    content = self._clean_content(resp_json.get("content", ""))
                    if len(content) > 50: # 確保抓到的不是空內容
                        tmp_txt = f"/tmp/{uuid.uuid4().hex[:8]}.txt"
                        with open(tmp_txt, "w", encoding="utf-8") as f: f.write(content)
                        res = self.run_nlm("source", "add", nb_id, "--file", tmp_txt, *wait_flag)
                        return res.returncode == 0
        except Exception as e:
            print(f"⚠️ 備援爬蟲發生異常: {e}")
        return False

    def process_video(self, url, title, custom_prompt=None):
        """
        /// 處理單一影片摘要 (優化 /nlm 回應速度)
        """
        nb_id = None
        try:
            nb_name = f"YT_{uuid.uuid4().hex[:4].upper()}"
            res = self.run_nlm("notebook", "create", nb_name)
            if res.returncode != 0: return "❌ 建立筆記本失敗"
            
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if match else nb_name

            # 使用 --wait 加速索引
            if not self._add_source_with_proxy(nb_id, url, wait=True):
                return "❌ 無法讀取內容"

            prompt = get_nlm_prompt(custom_prompt)
            res_query = self.run_nlm("query", "notebook", nb_id, prompt)
            if res_query.returncode == 0:
                summary = res_query.stdout.strip()
                try:
                    data = json.loads(summary)
                    summary = data.get("value", {}).get("answer", data.get("answer", summary))
                except: pass
                return re.sub(r'\*\*(Thinking|Thought|Summarizing|Analysis).*?\*\*[\s\n]*', '', summary, flags=re.IGNORECASE).strip()
            return "❌ 摘要產出失敗"
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

    def process_batch(self, urls: list, custom_prompt: str = None):
        nb_id = None
        try:
            nb_name = f"BATCH_{uuid.uuid4().hex[:4].upper()}"
            res = self.run_nlm("notebook", "create", nb_name)
            if res.returncode != 0: return "❌ 建立失敗"
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if match else nb_name
            
            # 並行匯入
            with ThreadPoolExecutor(max_workers=5) as executor:
                executor.map(lambda u: self._add_source_with_proxy(nb_id, u.strip(), wait=False), urls)
            
            time.sleep(5) # 批次等待時間
            prompt = f"{get_nlm_prompt(custom_prompt)}\n\n【請完全以繁體中文回答。】"
            res = self.run_nlm("query", "notebook", nb_id, prompt)
            if res.returncode != 0: return "❌ 摘要失敗"
            
            out = res.stdout.strip()
            try:
                data = json.loads(out)
                out = data.get("value", {}).get("answer", data.get("answer", out))
            except: pass
            return re.sub(r'\*\*(Thinking|Thought).*?\*\*[\s\n]*', '', out, flags=re.IGNORECASE).strip()
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

    def process_artifact(self, url: str, title: str, artifact_type: str = "slide_deck", custom_prompt: str = None, **kwargs):
        nb_id = None
        try:
            res = self.run_nlm("notebook", "create", f"ART_{uuid.uuid4().hex[:4]}")
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if res.returncode == 0 else None
            if not nb_id or not self._add_source_with_proxy(nb_id, url, wait=True): return "❌ 失敗"
            
            cmd = ["slides", "create", nb_id, "--language", "zh-TW", "--confirm"]
            if artifact_type == "infographic": cmd = ["infographic", "create", nb_id, "--language", "zh-TW", "--confirm"]
            if artifact_type == "report": cmd = ["report", "create", nb_id, "--language", "zh-TW", "--confirm"]
            if custom_prompt: cmd.extend(["--focus", get_nlm_prompt(custom_prompt)])
            return "✅ 生成中" if self.run_nlm(*cmd).returncode == 0 else "❌ 失敗"
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

    async def research_topic(self, topic: str, mode: str = "fast"):
        """
        /// 執行深度研究 (Deep Research)
        """
        nb_id = None
        try:
            res = self.run_nlm("notebook", "create", f"RES_{uuid.uuid4().hex[:4]}")
            match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
            nb_id = match.group(1) if res.returncode == 0 else None
            if not nb_id: return False, "建立筆記本失敗"

            print(f"🔎 啟動研究 ({mode.upper()}): {topic}")
            if self.run_nlm("research", "start", "--notebook-id", nb_id, "--mode", mode, topic).returncode != 0:
                return False, "啟動失敗"

            interval = 30 if mode == "deep" else 15
            timeout = 1200 if mode == "deep" else 600
            start_time = time.time()
            while time.time() - start_time < timeout:
                status_res = self.run_nlm("research", "status", nb_id, "--max-wait", "0", verbose=False)
                out = status_res.stdout.strip().lower()
                if any(k in out for k in ["completed", "success", "no active research", "ready to import"]): break
                print(f"📊 目前狀態: {out.splitlines()[0] if out else '等待中'}")
                time.sleep(interval)

            self.run_nlm("research", "import", nb_id)
            prompt = (
                f"你是一位資深財經分析師。針對主題「{topic}」，"
                "產出一份結構嚴謹、符合台灣用語的繁體中文報告。嚴禁英文思考過程與Meta說明。"
            )
            res_query = self.run_nlm("query", "notebook", nb_id, prompt)
            if res_query.returncode == 0:
                summary = res_query.stdout.strip()
                try:
                    data = json.loads(summary)
                    if isinstance(data, dict):
                        summary = data.get("value", {}).get("answer", data.get("answer", summary))
                except: pass
                summary = re.sub(r'\*\*(Thinking|Thought|Defining|Finalizing).*?\*\*[\s\n]*', '', summary, flags=re.IGNORECASE)
                summary = re.sub(r'I\'ve (finalized|decided|started).*?\.', '', summary, flags=re.IGNORECASE)
                return True, summary.strip()
            return False, "報告失敗"
        finally:
            if nb_id: self.run_nlm("notebook", "delete", nb_id, "--confirm")

NotebookManager = NotebookService
