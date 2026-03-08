import base64
import mimetypes
import os
import time
from typing import Optional

import requests
from app.config import Config


class Notifier:
    """
    /// 多平台通知服務模組
    /// 支援 Telegram 與 LINE 的自動化訊息路由
    """

    @classmethod
    def send_summary(cls, title, url, channel, summary, target_chat_id=None):
        """
        /// 格式化摘要並發送至指定平台
        """
        chat_id = target_chat_id or Config.TG_CHAT_ID

        if not chat_id:
            print(f"⚠️ 找不到目標 Chat ID，摘要內容: {title}")
            return False

        msg_text = (
            f"🎥 {title}\n"
            f"📺 頻道：{channel}\n"
            f"🔗 連結：{url}\n\n"
            f"📝 AI 摘要\n{summary}"
        )

        if str(chat_id).startswith(("U", "C", "R")):
            return cls._send_to_line(chat_id, msg_text)
        return cls._send_to_telegram(chat_id, msg_text)

    @staticmethod
    def _send_to_telegram(chat_id, text):
        """
        /// 發送訊息至 Telegram
        """
        if not Config.TG_BOT_TOKEN:
            print("❌ 缺少 Telegram Token")
            return False

        endpoint = f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/sendMessage"
        html_text = text.replace("🎥", "<b>🎥").replace("\n📺", "</b>\n📺")

        try:
            requests.post(
                endpoint,
                json={
                    "chat_id": chat_id,
                    "text": html_text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            return True
        except Exception as e:
            print(f"❌ Telegram 推播失敗: {e}")
            return False

    @staticmethod
    def _send_to_line(chat_id, text):
        """
        /// 發送訊息至 LINE
        """
        if not Config.LINE_CHANNEL_ACCESS_TOKEN:
            print("❌ 缺少 LINE Channel Access Token")
            return False

        endpoint = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}",
        }
        payload = {"to": chat_id, "messages": [{"type": "text", "text": text}]}

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                return True
            print(f"❌ LINE 推播失敗: {resp.status_code} {resp.text}")
            return False
        except Exception as e:
            print(f"❌ LINE API 連線異常: {e}")
            return False

    @staticmethod
    def _push_line_messages(chat_id, messages):
        """Push one or more LINE messages."""
        if not Config.LINE_CHANNEL_ACCESS_TOKEN:
            print("❌ 缺少 LINE Channel Access Token")
            return False

        endpoint = "https://api.line.me/v2/bot/message/push"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}",
        }
        payload = {"to": chat_id, "messages": messages}

        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
            if resp.status_code == 200:
                return True
            print(f"❌ LINE 推播失敗: {resp.status_code} {resp.text}")
            return False
        except Exception as e:
            print(f"❌ LINE API 連線異常: {e}")
            return False

    @staticmethod
    def _publish_file_to_github(file_path: str, target_chat_id: str, artifact_kind: str) -> Optional[str]:
        """
        Publish a generated artifact into the public repository and return a raw URL.
        This bridges LINE delivery, because LINE push messages require public URLs.
        """
        github_token = os.environ.get("GITHUB_TOKEN")
        github_repo = os.environ.get("GITHUB_REPOSITORY")
        github_branch = os.environ.get("GITHUB_REF_NAME", "main")

        if not all([github_token, github_repo, github_branch]):
            print("❌ 缺少 GitHub 發佈所需環境變數")
            return None

        if "/" not in github_repo:
            print("❌ GITHUB_REPOSITORY 格式錯誤")
            return None

        owner, repo = github_repo.split("/", 1)
        safe_chat_id = "".join(ch if ch.isalnum() else "_" for ch in str(target_chat_id))[:80]
        ext = os.path.splitext(file_path)[1].lower()
        remote_path = f"generated/line/{safe_chat_id}/{artifact_kind}{ext}"

        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
        except Exception as e:
            print(f"❌ 讀取檔案失敗: {e}")
            return None

        api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/{remote_path}"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        sha = None
        existing = requests.get(api_url, headers=headers, params={"ref": github_branch}, timeout=30)
        if existing.status_code == 200:
            sha = existing.json().get("sha")

        payload = {
            "message": f"chore: publish LINE artifact ({artifact_kind}) [skip ci]",
            "content": encoded,
            "branch": github_branch,
        }
        if sha:
            payload["sha"] = sha

        try:
            resp = requests.put(api_url, headers=headers, json=payload, timeout=30)
            if resp.status_code not in (200, 201):
                print(f"❌ GitHub 發佈失敗: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            print(f"❌ GitHub 發佈異常: {e}")
            return None

        return (
            f"https://raw.githubusercontent.com/{owner}/{repo}/{github_branch}/{remote_path}"
            f"?t={int(time.time())}"
        )

    @classmethod
    def send_error(cls, target_chat_id, error_msg, url=None):
        """
        /// 發送錯誤通知
        """
        chat_id = target_chat_id or Config.TG_CHAT_ID
        msg = "❌ <b>系統執行失敗</b>\n\n"
        if url:
            msg += f"🔗 連結：<code>{url}</code>\n"
        msg += f"📝 錯誤內容：\n<pre>{error_msg}</pre>"

        if str(chat_id).startswith(("U", "C", "R")):
            return cls._send_to_line(chat_id, f"❌ 系統執行失敗\n\n{error_msg}")
        return cls._send_to_telegram(chat_id, msg)

    @classmethod
    def send_photo(cls, target_chat_id, file_path, caption=None):
        """
        /// 發送圖片至指定平台
        """
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False
        if str(chat_id).startswith(("U", "C", "R")):
            return cls._send_photo_to_line(chat_id, file_path, caption)
        return cls._send_photo_to_telegram(chat_id, file_path, caption)

    @staticmethod
    def _send_photo_to_telegram(chat_id, file_path, caption=None):
        if not Config.TG_BOT_TOKEN:
            return False

        endpoint = f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/sendPhoto"
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption

        try:
            with open(file_path, "rb") as f:
                files = {"photo": (os.path.basename(file_path), f)}
                resp = requests.post(endpoint, data=data, files=files, timeout=60)
                return resp.status_code == 200
        except Exception:
            return False

    @classmethod
    def _send_photo_to_line(cls, chat_id, file_path, caption=None):
        image_url = cls._publish_file_to_github(file_path, chat_id, "latest-pic")
        if not image_url:
            fallback = "⚠️ 圖片已生成，但目前無法建立公開網址。"
            if caption:
                fallback = f"{caption}\n\n{fallback}"
            return cls._send_to_line(chat_id, fallback)

        messages = []
        if caption:
            messages.append({"type": "text", "text": caption[:5000]})
        messages.append(
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        )
        return cls._push_line_messages(chat_id, messages)

    @classmethod
    def send_document(cls, target_chat_id, file_path, caption=None):
        """
        /// 發送文件至指定平台
        """
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False

        if str(chat_id).startswith(("U", "C", "R")):
            return cls._send_document_to_line(chat_id, file_path, caption)
        return cls._send_document_to_telegram(chat_id, file_path, caption)

    @staticmethod
    def _send_document_to_telegram(chat_id, file_path, caption=None):
        if not Config.TG_BOT_TOKEN:
            return False

        endpoint = f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/sendDocument"
        data = {"chat_id": chat_id}
        if caption:
            data["caption"] = caption

        try:
            with open(file_path, "rb") as f:
                files = {"document": (os.path.basename(file_path), f)}
                resp = requests.post(endpoint, data=data, files=files, timeout=60)
                return resp.status_code == 200
        except Exception:
            return False

    @classmethod
    def _send_document_to_line(cls, chat_id, file_path, caption=None):
        kind = "latest-note" if file_path.lower().endswith(".md") else "latest-file"
        public_url = cls._publish_file_to_github(file_path, chat_id, kind)
        if not public_url:
            fallback = "⚠️ 檔案已生成，但目前無法建立公開下載連結。"
            if caption:
                fallback = f"{caption}\n\n{fallback}"
            return cls._send_to_line(chat_id, fallback)

        filename = os.path.basename(file_path)
        mime_type, _ = mimetypes.guess_type(file_path)
        label = "檔案下載"
        if mime_type == "text/markdown" or file_path.lower().endswith(".md"):
            label = "摘要報告"
        elif mime_type == "application/pdf":
            label = "PDF 簡報"
        elif file_path.lower().endswith(".pptx"):
            label = "PPTX 簡報"

        text = f"{caption or '檔案已生成'}\n\n{label}: {filename}\n{public_url}"
        return cls._send_to_line(chat_id, text[:5000])
