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
    
    NLM_COOKIE_BASE64 = os.environ.get("NLM_COOKIE_BASE64", "")
    
    LAST_CHECK_FILE = "last_check.txt"
    MAX_VIDEOS = int(os.environ.get("MAX_VIDEOS_PER_RUN", 5))
    
    DEFAULT_KEYWORDS = "poe,path of exile,流亡黯道,build,guide,攻略,開荒,賽季,league,atlas,輿圖,天賦,機制,拓荒,暗黑,diablo"
    FILTER_KEYWORDS = os.environ.get("FILTER_KEYWORDS", DEFAULT_KEYWORDS)

    @classmethod
    def get_keywords(cls):
        """
        /// 取得處理後的關鍵字清單
        """
        return [k.strip().lower() for k in cls.FILTER_KEYWORDS.split(",")]
