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
        # 決定目標 Chat ID (若未指定，則使用 Config 中的預設值)
        chat_id = target_chat_id or Config.TG_CHAT_ID
        
        if not chat_id:
            print(f"⚠️ 找不到目標 Chat ID，摘要內容: {title}")
            return False

        # 格式化訊息內容
        msg_text = (f"🎥 {title}\n"
                    f"📺 頻道：{channel}\n"
                    f"🔗 連結：{url}\n\n"
                    f"📝 AI 摘要\n{summary}")

        # 根據 Chat ID 特徵自動路由平台
        # LINE ID 通常以 U (User), C (Group), R (Room) 開頭
        if str(chat_id).startswith(('U', 'C', 'R')):
            return cls._send_to_line(chat_id, msg_text)
        else:
            # 預設為 Telegram
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
        # 轉換 HTML 標籤 (針對 Telegram)
        html_text = text.replace("🎥", "<b>🎥").replace("\n📺", "</b>\n📺")
        
        try:
            requests.post(endpoint, json={
                "chat_id": chat_id, 
                "text": html_text, 
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }, timeout=15)
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
            "Authorization": f"Bearer {Config.LINE_CHANNEL_ACCESS_TOKEN}"
        }
        payload = {
            "to": chat_id,
            "messages": [{"type": "text", "text": text}]
        }
        
        try:
            resp = requests.post(endpoint, json=payload, headers=headers, timeout=15)
            if resp.status_code == 200:
                return True
            else:
                print(f"❌ LINE 推播失敗: {resp.status_code} {resp.text}")
                return False
        except Exception as e:
            print(f"❌ LINE API 連線異常: {e}")
            return False
