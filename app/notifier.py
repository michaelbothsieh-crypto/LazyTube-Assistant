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
        
        # 簡單處理 HTML 逸碼，避免破壞標籤
        safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # 恢復我們想要加粗的部分
        html_text = safe_text.replace("🎥", "<b>🎥").replace("\n📺", "</b>\n📺")

        try:
            resp = requests.post(
                endpoint,
                json={
                    "chat_id": chat_id,
                    "text": html_text,
                    "parse_mode": "HTML",
                    "disable_web_page_preview": True,
                },
                timeout=15,
            )
            if resp.status_code != 200:
                print(f"❌ Telegram 推播失敗: {resp.status_code} {resp.text}")
                # 如果是 HTML 解析錯誤，嘗試以純文字重發
                if "can't parse entities" in resp.text:
                    requests.post(endpoint, json={"chat_id": chat_id, "text": text}, timeout=15)
                return False
            return True
        except Exception as e:
            print(f"❌ Telegram 推播異常: {e}")
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
        """
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token:
            print("❌ 缺少 BLOB_READ_WRITE_TOKEN")
            return None

        filename = os.path.basename(file_path)
        safe_filename = "".join(c for c in filename if c.isalnum() or c in "._-").strip()
        safe_chat_id = "".join(ch if ch.isalnum() else "_" for ch in str(target_chat_id))[:50]
        blob_path = f"artifacts/{safe_chat_id}/{int(time.time())}_{safe_filename}"
        
        api_url = f"https://blob.vercel-storage.com/{blob_path}"
        
        content_type = "application/pdf" if filename.endswith(".pdf") else "text/html"
        
        try:
            with open(file_path, "rb") as f:
                headers = {
                    "Authorization": f"Bearer {token}",
                    "x-api-version": "1",
                    "content-type": content_type
                }
                resp = requests.put(api_url, data=f, headers=headers, timeout=120)
                if resp.status_code == 200:
                    return resp.json().get("url")
                return None
        except Exception:
            return None

    @staticmethod
    def delete_pending_message(chat_id: str, message_id: str) -> None:
        """
        /// 刪除 Telegram「處理中」的等待提示訊息
        """
        if not message_id or str(chat_id).startswith(("U", "C", "R")):
            return
        if not Config.TG_BOT_TOKEN:
            return

        import requests as _requests
        del_url = f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/deleteMessage"
        try:
            _requests.post(del_url, json={
                "chat_id": chat_id,
                "message_id": int(message_id)
            }, timeout=10)
        except Exception:
            pass

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
            return False
        messages = []
        if caption:
            messages.append({"type": "text", "text": caption[:5000]})
        messages.append({"type": "image", "originalContentUrl": image_url, "previewImageUrl": image_url})
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
        public_url = cls._upload_to_vercel_blob(file_path, chat_id)
        if not public_url:
            return False

        filename = os.path.basename(file_path)
        messages = []
        if caption:
            messages.append({"type": "text", "text": caption[:5000]})
        messages.append({
            "type": "text",
            "text": f"📥 檔案已上傳：{filename}\n🔗 下載連結：{public_url}"
        })
        return cls._push_line_messages(chat_id, messages)

    # --- HTML 專業報告相關 ---

    @classmethod
    def generate_html_report(cls, title: str, markdown_content: str) -> str:
        """
        /// 將 Markdown 轉換為專業設計的 HTML 報告
        """
        import markdown
        from datetime import datetime
        
        html_body = markdown.markdown(markdown_content, extensions=['extra', 'toc', 'tables'])
        gen_time = datetime.now().strftime("%Y-%m-%d %H:%M")

        template = f"""
<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title} - 深度研究報告</title>
    <style>
        :root {{ --primary-color: #1a73e8; --bg-color: #f8f9fa; --text-color: #202124; --card-bg: #ffffff; --border-color: #dadce0; }}
        body {{ font-family: 'Segoe UI', Roboto, Arial, 'PingFang TC', sans-serif; line-height: 1.6; color: var(--text-color); background-color: var(--bg-color); margin: 0; padding: 0; }}
        .container {{ max-width: 900px; margin: 40px auto; padding: 0 20px; }}
        header {{ text-align: center; margin-bottom: 40px; padding-bottom: 20px; border-bottom: 2px solid var(--primary-color); }}
        h1 {{ color: var(--primary-color); margin: 0; }}
        .meta {{ color: #5f6368; font-size: 0.9em; margin-top: 10px; }}
        .report-card {{ background: var(--card-bg); border: 1px solid var(--border-color); border-radius: 8px; padding: 40px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
        h2 {{ border-left: 5px solid var(--primary-color); padding-left: 15px; margin-top: 30px; color: #174ea6; }}
        blockquote {{ background: #e8f0fe; border-left: 5px solid var(--primary-color); margin: 20px 0; padding: 15px 20px; font-style: italic; }}
        table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid var(--border-color); padding: 12px; text-align: left; }}
        th {{ background: #f1f3f4; }}
        footer {{ text-align: center; margin-top: 40px; padding: 20px; color: #70757a; font-size: 0.8em; }}
        @media (max-width: 600px) {{ .container {{ margin: 10px auto; }} .report-card {{ padding: 20px; }} }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>{title}</h1>
            <div class="meta">深度研究報告 • 生成時間：{gen_time}</div>
        </header>
        <div class="report-card">{html_body}</div>
        <footer>&copy; {datetime.now().year} LazyTube-Assistant</footer>
    </div>
</body>
</html>
"""
        return template

    @classmethod
    def generate_pdf_report(cls, html_content: str) -> Optional[str]:
        """
        /// 將 HTML 報告轉換為 PDF 並回傳暫存路徑
        """
        try:
            import pdfkit
            import uuid
            
            pdf_name = f"report_{uuid.uuid4().hex[:8]}.pdf"
            pdf_path = f"/tmp/{pdf_name}"
            
            options = {
                'page-size': 'A4',
                'margin-top': '0.75in',
                'margin-right': '0.75in',
                'margin-bottom': '0.75in',
                'margin-left': '0.75in',
                'encoding': "UTF-8",
                'no-outline': None,
                'quiet': ''
            }
            
            pdfkit.from_string(html_content, pdf_path, options=options)
            return pdf_path
        except Exception as e:
            print(f"❌ PDF 生成失敗: {e}")
            return None

    @classmethod
    def upload_report(cls, title: str, html_content: str, chat_id: str, file_path: Optional[str] = None) -> Optional[str]:
        """
        /// 上傳報告檔案 (HTML 或 PDF)
        """
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return None

        import uuid
        
        # 如果有傳入 file_path (例如 PDF)，直接使用
        if file_path and os.path.exists(file_path):
            tmp_path = file_path
            file_name = os.path.basename(file_path)
            content_type = "application/pdf"
        else:
            file_name = f"report_{uuid.uuid4().hex[:8]}.html"
            tmp_path = f"/tmp/{file_name}"
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            content_type = "text/html"

        safe_chat_id = "".join(ch if ch.isalnum() else "_" for ch in str(chat_id))[:30]
        blob_path = f"reports/{safe_chat_id}/{int(time.time())}_{file_name}"
        api_url = f"https://blob.vercel-storage.com/{blob_path}"
        
        try:
            with open(tmp_path, "rb") as f:
                resp = requests.put(api_url, data=f, headers={
                    "Authorization": f"Bearer {token}",
                    "x-api-version": "1",
                    "content-type": content_type
                }, timeout=60)
                if resp.status_code == 200:
                    return resp.json().get("url")
                else:
                    print(f"❌ Vercel 上傳失敗 (Status {resp.status_code}): {resp.text}")
        except Exception as e:
            print(f"❌ 報告上傳異常: {e}")
        return None

    @classmethod
    def cleanup_old_reports(cls):
        """
        /// 自動清理 30 天前的舊報告
        """
        token = os.environ.get("BLOB_READ_WRITE_TOKEN")
        if not token: return
        list_url = "https://blob.vercel-storage.com?prefix=reports/"
        try:
            resp = requests.get(list_url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
            if resp.status_code == 200:
                data = resp.json()
                now = time.time()
                to_delete = []
                for blob in data.get("blobs", []):
                    try:
                        ts = int(blob["pathname"].split("/")[2].split("_")[0])
                        if now - ts > 30 * 86400: to_delete.append(blob["url"])
                    except: continue
                if to_delete:
                    requests.post("https://blob.vercel-storage.com/v1/delete", 
                                  json={"urls": to_delete}, 
                                  headers={"Authorization": f"Bearer {token}"}, timeout=30)
        except: pass
