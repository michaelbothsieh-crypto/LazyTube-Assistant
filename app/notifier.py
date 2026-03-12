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

    @classmethod
    def send_text(cls, target_chat_id, text, html=False):
        """Send a plain text or HTML message to Telegram/LINE."""
        chat_id = target_chat_id or Config.TG_CHAT_ID
        if not chat_id:
            return False

        if str(chat_id).startswith(('U', 'C', 'R')):
            return cls._send_to_line(chat_id, text)

        if not html:
            return cls._send_to_telegram(chat_id, text)

        if not Config.TG_BOT_TOKEN:
            print("❌ 缺少 Telegram Token")
            return False

        endpoint = f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/sendMessage"
        try:
            resp = requests.post(endpoint, json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }, timeout=15)
            return resp.status_code == 200
        except Exception as e:
            print(f"❌ Telegram 發送異常: {e}")
            return False

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
    def _upload_to_vercel_blob(file_path: str, target_chat_id: str) -> Optional[str]:
        """
        將檔案上傳至 Vercel Blob 並取得公開網址。
        取代原本上傳至 GitHub 的舊邏輯。
        """
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token:
            print("❌ 缺少 BLOB_READ_WRITE_TOKEN，無法上傳至 Vercel Blob")
            return None

        filename = os.path.basename(file_path)
        # 移除檔名中的特殊字元避免上傳失敗
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-").strip()
        safe_chat_id = "".join(ch if ch.isalnum() else "_" for ch in str(target_chat_id))[:50]
        # 使用時間戳與 ChatID 建立唯一路徑
        blob_path = f"artifacts/{safe_chat_id}/{int(time.time())}_{safe_filename}"
        
        # Vercel Blob REST API 端點
        api_url = f"https://blob.vercel-storage.com/v1/upload/{blob_path}"
        
        try:
            file_size = os.path.getsize(file_path)
            print(f"☁️ 正在上傳至 Vercel Blob: {safe_filename} ({file_size} bytes)...")
            
            with open(file_path, "rb") as f:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "x-api-version": "1",
                }
                # 使用 PUT 方法直接上傳二進位檔案流
                resp = requests.put(api_url, data=f, headers=headers, timeout=120)
                
                if resp.status_code == 200:
                    url = resp.json().get("url")
                    print(f"✅ 上傳成功: {url}")
                    return url
                
                print(f"❌ Vercel Blob 上傳失敗: {resp.status_code} {resp.text}")
                return None
        except Exception as e:
            print(f"❌ Vercel Blob 上傳異常: {e}")
            return None

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
        image_url = cls._upload_to_vercel_blob(file_path, chat_id)
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

    @staticmethod
    def _upload_to_github(file_path: str, target_chat_id: str) -> Optional[str]:
        """
        當 Vercel Blob 失敗時的備援方案：將檔案 Commit 到 GitHub Repo 並取得 Raw 連結。
        """
        import subprocess
        import shutil
        
        token = os.environ.get("GITHUB_TOKEN")
        if not token:
            print("❌ 缺少 GITHUB_TOKEN，無法執行 GitHub 備援上傳")
            return None

        filename = os.path.basename(file_path)
        ext = filename.split(".")[-1].lower() if "." in filename else "bin"
        # 決定目標檔名：latest-file 或 latest-pic (為了保持連結穩定或方便手機快取)
        target_name = "latest-pic.png" if ext in ["png", "jpg", "jpeg", "gif"] else "latest-file.pdf"
        if ext not in ["png", "jpg", "jpeg", "gif", "pdf"]:
            target_name = f"latest-file.{ext}"

        safe_chat_id = "".join(ch if ch.isalnum() else "_" for ch in str(target_chat_id))[:50]
        rel_dir = os.path.join("generated", "line", safe_chat_id)
        os.makedirs(rel_dir, exist_ok=True)
        
        dest_path = os.path.join(rel_dir, target_name)
        shutil.copy2(file_path, dest_path)
        
        print(f"📦 正在將檔案提交至 GitHub: {dest_path}...")
        
        try:
            # 配置 Git (如果尚未配置)
            subprocess.run(["git", "config", "user.name", "github-actions[bot]"], check=False)
            subprocess.run(["git", "config", "user.email", "github-actions[bot]@users.noreply.github.com"], check=False)
            
            # 提交並推送到 GitHub
            subprocess.run(["git", "add", dest_path], check=True)
            commit_msg = f"chore: publish LINE artifact ({target_name}) [skip ci]"
            subprocess.run(["git", "commit", "-m", commit_msg], check=True)
            
            # 使用 Token 進行推播 (在 GitHub Actions 環境下通常不需要特別處理，但為了保險)
            subprocess.run(["git", "push"], check=True)
            
            # 取得 Repo 資訊
            repo_info = "michaelbothsieh-crypto/LazyTube-Assistant"
            try:
                remote_url = subprocess.check_output(["git", "remote", "get-url", "origin"], text=True).strip()
                if "github.com" in remote_url:
                    repo_info = remote_url.split("github.com")[-1].replace(":", "/").lstrip("/").replace(".git", "")
            except:
                pass
            raw_url = f"https://raw.githubusercontent.com/{repo_info}/main/generated/line/{safe_chat_id}/{target_name}?t={int(time.time())}"
            print(f"✅ GitHub 備援上傳成功: {raw_url}")
            return raw_url
            
        except Exception as e:
            print(f"❌ GitHub 提交失敗: {e}")
            return None

    @classmethod
    def _send_document_to_line(cls, chat_id, file_path, caption=None):
        # 1. 優先嘗試 Vercel Blob (支援大檔案，連結持久)
        public_url = cls._upload_to_vercel_blob(file_path, chat_id)
        
        # 2. 如果 Vercel Blob 失敗 (例如檔案 > 4.5MB)，嘗試 GitHub Fallback
        if not public_url:
            print("⚠️ Vercel Blob 上傳失敗，嘗試 GitHub 備援...")
            public_url = cls._upload_to_github(file_path, chat_id)

        if not public_url:
            fallback = "⚠️ 檔案已生成，但目前無法建立公開下載連結。"
            if caption:
                fallback = f"{caption}\n\n{fallback}"
            return cls._send_to_line(chat_id, fallback)

        filename = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
<<<<<<< HEAD
        size_str = f"{file_size / 1024 / 1024:.2f} MB" if file_size > 1024 * 1024 else f"{file_size / 1024:.1f} KB"
        
        # 根據副檔名顯示不同圖示
        ext = filename.split(".")[-1].lower() if "." in filename else ""
        icon = "📊" if ext == "pdf" else "📝" if ext == "md" else "📂"
        label = "PDF 簡報" if ext == "pdf" else "摘要報告" if ext == "md" else "檔案下載"

        # 使用 Flex Message 繞過 LINE 帳號對 'file' 類型的權限限制
        flex_contents = {
            "type": "bubble",
            "size": "kilo",
            "header": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": f"{icon} {label}生成完畢",
                        "weight": "bold",
                        "color": "#1DB446",
                        "size": "sm"
                    }
                ]
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": filename,
                        "weight": "bold",
                        "size": "md",
                        "wrap": True,
                        "maxLines": 3
                    },
                    {
                        "type": "text",
                        "text": size_str,
                        "size": "xs",
                        "color": "#aaaaaa",
                        "margin": "sm"
                    }
                ]
            },
            "footer": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "button",
                        "action": {
                            "type": "uri",
                            "label": "📥 點擊下載檔案",
                            "uri": public_url
                        },
                        "style": "primary",
                        "color": "#1DB446"
                    }
                ]
            }
        }

        messages = []
        if caption:
            messages.append({"type": "text", "text": caption[:5000]})
        
        messages.append({
            "type": "flex",
            "altText": f"📊 {filename} 下載連結",
            "contents": flex_contents
        })
        
        return cls._push_line_messages(chat_id, messages)
