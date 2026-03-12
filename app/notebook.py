import subprocess
import uuid
import re
import json
import os
import time


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

    def _prepare_notebook(self, url: str, prefix: str = "YT", wait: bool = False):
        """
        /// 共用的筆記本準備流程
        /// 建立筆記本並以多重代理策略新增來源
        /// 回傳 (nb_id, effective_url)，失敗時回傳 (None, None)
        """
        nb_name = f"{prefix}_{uuid.uuid4().hex[:4].upper()}"
        nb_id = None

        print(f"📁 正在建立筆記本: {nb_name}...")
        res = self.run_nlm("notebook", "create", nb_name)
        if res.returncode != 0:
            return None, None
        match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
        nb_id = match.group(1) if match else nb_name
        print(f"✅ 筆記本建立成功 (ID: {nb_id})")

        wait_flag = ["--wait"] if wait else []

        print(f"🔗 正在新增來源: {url}...")
        res_add = self.run_nlm("source", "add", nb_id, "--url", url, *wait_flag)

        if res_add.returncode != 0:
            print("⚠️ 直接新增來源失敗，嘗試透過 Jina Reader 代理繞過...")
            proxy_url = f"https://r.jina.ai/{url}"
            res_add = self.run_nlm("source", "add", nb_id, "--url", proxy_url, *wait_flag)

            if res_add.returncode != 0:
                print("⚠️ Jina 代理亦失敗，嘗試使用 Google Translate Proxy...")
                gt_url = f"https://translate.google.com/translate?sl=auto&tl=zh-TW&u={url}"
                res_add = self.run_nlm("source", "add", nb_id, "--url", gt_url, *wait_flag)

            if res_add.returncode == 0:
                print("✅ 透過代理繞過成功")
            else:
                return nb_id, None

        return nb_id, url

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
            prompt = custom_prompt or "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
            res = self.run_nlm("query", "notebook", nb_id, prompt)

            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    summary = data.get("value", {}).get("answer", res.stdout)
                except Exception:
                    summary = res.stdout.strip()
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
                    "--confirm"
                ]
                if custom_prompt:
                    cmd_args.extend(["--focus", custom_prompt])
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
                    cmd_args.extend(["--focus", custom_prompt])
            elif artifact_type == "report":
                lang = kwargs.get("language", "zh-TW")
                cmd_args = [
                    "report", "create", nb_id,
                    "--language", lang,
                    "--format", "Create Your Own",
                    "--confirm"
                ]
                cmd_args.extend(["--prompt", custom_prompt or "請用繁體中文提供詳細的內容摘要報告"])

            create_res = self.run_nlm(*cmd_args)

            if create_res.returncode != 0:
                print(f"❌ {artifact_type} 生成請求失敗")
                return None

            artifact_id = None
            print(f"⏳ 正在等待 {artifact_type} 製作完成...")
            for i in range(60):
                time.sleep(20)
                status_res = self.run_nlm("studio", "status", nb_id, "--json", verbose=False)
                raw_out = status_res.stdout.strip() if status_res.stdout else ""

                if status_res.returncode == 0 and raw_out:
                    try:
                        status_data = json.loads(raw_out)
                        if not isinstance(status_data, list):
                            continue

                        current_status = "UNKNOWN"
                        for art in status_data:
                            if art.get("type") == artifact_type:
                                current_status = art.get("status")
                                if current_status == "completed":
                                    artifact_id = art.get("id")
                                    print(f"✨ 製作完成! ID: {artifact_id}")
                                    break
                                elif current_status == "failed":
                                    print(f"❌ 製作失敗: {art.get('error_message', '原因不明')}")
                                    return None

                        if artifact_id:
                            break
                        print(f"  ({i+1}/60) 目前狀態: {current_status}...")
                    except BaseException as e:
                        print(f"  ({i+1}/60) 解析失敗: {e}")
                else:
                    print(f"  ({i+1}/60) 正在獲取狀態...")

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
                print("⏰ 製作超時")

        finally:
            if nb_id:
                print(f"🧹 正在刪除暫存筆記本: {nb_id}...")
                self.run_nlm("notebook", "delete", nb_id, "--confirm")

        return target_path
