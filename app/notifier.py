import requests
from app.config import Config

class Notifier:
    """
    /// 通知服務模組
    /// 負責透過 Telegram Bot 發送摘要訊息
    """

    @staticmethod
    def send_summary(title, url, channel, summary):
        """
        /// 格式化並發送摘要訊息
        """
        if not Config.TG_BOT_TOKEN or not Config.TG_CHAT_ID:
            print(f"--- [ 摘要內容: {title} ] ---\n{summary}")
            return False

        msg = (f"<b>🎥 {title}</b>\n"
               f"📺 頻道：{channel}\n"
               f"🔗 <a href='{url}'>觀看</a>\n\n"
               f"📝 <b>AI 摘要</b>\n{summary}")
        
        endpoint = f"https://api.telegram.org/bot{Config.TG_BOT_TOKEN}/sendMessage"
        try:
            requests.post(endpoint, json={
                "chat_id": Config.TG_CHAT_ID, 
                "text": msg, 
                "parse_mode": "HTML"
            }, timeout=15)
            return True
        except Exception as e:
            print(f"❌ Telegram 推播失敗: {e}")
            return False
