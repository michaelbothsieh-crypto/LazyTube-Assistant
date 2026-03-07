import os

class Config:
    """
    /// 撠??典??蔭蝞∠?
    /// 鞎痊霈?蒂撽??啣?霈
    """
    
    YT_CLIENT_ID = os.environ.get("YT_CLIENT_ID")
    YT_CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET")
    YT_REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN")
    
    TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")
    
    # LINE ?蔭
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")
    
    NLM_COOKIE_BASE64 = os.environ.get("NLM_COOKIE_BASE64", "")
    
    LAST_CHECK_FILE = "last_check.txt"
    MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS_PER_RUN", 5))
    SHORTS_MAX_SECONDS = int(os.environ.get("SHORTS_MAX_SECONDS", 60))
    
    # ?身?蕪?摮?(?征隞?”銝脰??蕪嚗????蔣??
    DEFAULT_KEYWORDS = ""
    FILTER_KEYWORDS = os.environ.get("FILTER_KEYWORDS", DEFAULT_KEYWORDS)

    # ?賢??桐蝙?刻?ID (????)
    ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "")

    @classmethod
    def get_allowed_users(cls):
        """????雿輻????"""
        if not cls.ALLOWED_USERS: return []
        return [u.strip() for u in cls.ALLOWED_USERS.split(",")]

    @classmethod
    def get_keywords(cls):
        """????敺??摮???"""
        if not cls.FILTER_KEYWORDS: return []
        return [k.strip().lower() for k in cls.FILTER_KEYWORDS.split(",")]
