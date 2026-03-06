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
    def run_nlm(*args):
        """
        /// 執行 nlm 指令並確保路徑環境正確
        """
        home = os.path.expanduser("~")
        config_dir = os.path.join(home, ".notebooklm-mcp-cli")
        env = os.environ.copy()
        env["NLM_CONFIG_DIR"] = config_dir
        
        cmd = ["nlm", *args]
        return subprocess.run(cmd, capture_output=True, text=True, env=env)

    def process_video(self, url, title):
        """
        /// 完整處理一個影片的摘要流程
        """
        nb_name = f"YT_{uuid.uuid4().hex[:4].upper()}"
        nb_id = None
        summary = None
        
        try:
            # 1. 建立筆記本
            res = self.run_nlm("notebook", "create", nb_name)
            if res.returncode == 0:
                match = re.search(r"ID:\s*([a-zA-Z0-9\-]+)", res.stdout)
                nb_id = match.group(1) if match else nb_name
            else:
                return None
            
            # 2. 新增來源
            self.run_nlm("source", "add", nb_id, "--url", url)
            
            # 3. 產出摘要
            prompt = "請用繁體中文列出這部影片的 3 到 5 個核心重點，並加上影片標題"
            res = self.run_nlm("query", "notebook", nb_id, prompt)
            
            if res.returncode == 0:
                try:
                    data = json.loads(res.stdout)
                    summary = data.get("value", {}).get("answer", res.stdout)
                except:
                    summary = res.stdout.strip()
        finally:
            if nb_id:
                self.run_nlm("notebook", "delete", nb_id, "--confirm")
        
        return summary
