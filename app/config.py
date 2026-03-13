import os


class Config:
    """
    /// 專案全域配置管理
    /// 負責讀取並驗證環境變數
    """

    YT_CLIENT_ID = os.environ.get("YT_CLIENT_ID")
    YT_CLIENT_SECRET = os.environ.get("YT_CLIENT_SECRET")
    YT_REFRESH_TOKEN = os.environ.get("YT_REFRESH_TOKEN")

    TG_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
    TG_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

    # LINE 配置
    LINE_CHANNEL_ACCESS_TOKEN = os.environ.get("LINE_CHANNEL_ACCESS_TOKEN")

    NLM_COOKIE_BASE64 = os.environ.get("NLM_COOKIE_BASE64", "")

    LAST_CHECK_FILE = "last_check.txt"
    PROCESSED_VIDEOS_FILE = "processed_videos.txt"
    SUBSCRIPTIONS_FILE = "subscriptions.json"
    MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS_PER_RUN", 5))

    # 超過這個秒數才視為長影片，60 秒以下視為 Shorts/短片
    SHORTS_MAX_SECONDS = int(os.environ.get("SHORTS_MAX_SECONDS", 60))

    # 預設過濾關鍵字（留空代表不進行過濾，抓取所有影片）
    DEFAULT_KEYWORDS = ""
    MAX_VIDEO_SECONDS = int(os.environ.get("MAX_VIDEO_SECONDS", 3600))
    FILTER_KEYWORDS = os.environ.get("FILTER_KEYWORDS", DEFAULT_KEYWORDS)

    # 白名單使用者 ID（逗號分隔）
    ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "")

    @classmethod
    def validate(cls) -> bool:
        """
        /// 驗證必填設定是否完整
        /// 在啟動時呼叫，提早偵測缺少的憑證
        """
        missing = []
        for field in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
            if not getattr(cls, field):
                missing.append(field)
        has_notifier = cls.TG_BOT_TOKEN or cls.LINE_CHANNEL_ACCESS_TOKEN
        if not has_notifier:
            missing.append("TELEGRAM_BOT_TOKEN 或 LINE_CHANNEL_ACCESS_TOKEN")
        if missing:
            print(f"❌ 缺少必填設定：{', '.join(missing)}")
            return False
        return True

    @classmethod
    def get_allowed_users(cls):
        """取得授權使用者清單"""
        if not cls.ALLOWED_USERS:
            return []
        return [user.strip() for user in cls.ALLOWED_USERS.split(",")]

    @classmethod
    def get_keywords(cls):
        """取得處理後的關鍵字清單"""
        if not cls.FILTER_KEYWORDS:
            return []
        return [keyword.strip().lower() for keyword in cls.FILTER_KEYWORDS.split(",")]
