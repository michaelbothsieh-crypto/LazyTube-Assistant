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

    # Redis 配置 (用於暫存 LINE PDF 報告)
    REDIS_URL = os.environ.get("UPSTASH_REDIS_REST_URL")
    REDIS_TOKEN = os.environ.get("UPSTASH_REDIS_REST_TOKEN")

    NLM_COOKIE_BASE64 = os.environ.get("NLM_COOKIE_BASE64", "")
    CUSTOM_PROMPT = os.environ.get("CUSTOM_PROMPT")

    # Vercel 環境下只有 /tmp 是可寫的
    _STATE_DIR = "/tmp" if os.environ.get("VERCEL") or os.environ.get("NOW_REGION") else "."
    
    LAST_CHECK_FILE = os.path.join(_STATE_DIR, "last_check.txt")
    PROCESSED_VIDEOS_FILE = os.path.join(_STATE_DIR, "processed_videos.txt")
    SUBSCRIPTIONS_FILE = os.path.join(_STATE_DIR, "subscriptions.json")
    MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS_PER_RUN", 10))

    # 超過這個秒數才視為長影片，60 秒以下視為 Shorts/短片
    SHORTS_MAX_SECONDS = int(os.environ.get("SHORTS_MAX_SECONDS", 60))

    # 預設過濾關鍵字（留空代表不進行過濾，抓取所有影片）
    DEFAULT_KEYWORDS = ""
    MAX_VIDEO_SECONDS = int(os.environ.get("MAX_VIDEO_SECONDS", 3600))
    FILTER_KEYWORDS = os.environ.get("FILTER_KEYWORDS", DEFAULT_KEYWORDS)

    # 白名單使用者 ID（逗號分隔）
    ALLOWED_USERS = os.environ.get("ALLOWED_USERS", "")

    # 排程系統：有效的 preferred_time 時段（台北時間，偶數小時）
    # master-scheduler 在這些時段的 :30 分執行，與 yt-summary 的 :00 分完全錯開
    VALID_PREFERRED_HOURS = [6, 8, 10, 12, 14, 16, 18, 20, 22]

    # 已處理影片 ID 上限（超過則保留最新的）
    PROCESSED_IDS_LIMIT = 150

    # URL 長度上限
    MAX_URL_LENGTH = 2048

    # 自訂 Prompt 長度上限
    MAX_PROMPT_LENGTH = 500

    # 批次處理 URL 上限
    MAX_BATCH_URLS = 20

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
