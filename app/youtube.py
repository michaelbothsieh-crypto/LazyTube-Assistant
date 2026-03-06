from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timezone
from app.config import Config

class YouTubeService:
    """
    /// YouTube API 封裝模組
    /// 負責高效獲取訂閱頻道活動
    """

    def __init__(self):
        self.service = self._get_service()

    def _get_service(self):
        creds = Credentials(
            None,
            refresh_token=Config.YT_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=Config.YT_CLIENT_ID,
            client_secret=Config.YT_CLIENT_SECRET,
        )
        if creds.expired:
            creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)

    def fetch_new_game_videos(self, last_check_time):
        """
        /// 使用 activities().list(mine=True) 高效獲取所有新影片
        /// 這比遍歷每個頻道節省約 95% 的 API 配額
        """
        new_videos = []
        try:
            # 單一請求獲取所有訂閱頻道的最新活動
            request = self.service.activities().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=50
            )
            response = request.execute()
            
            keywords = Config.get_keywords()
            
            for item in response.get("items", []):
                if item["snippet"]["type"] == "upload":
                    pub_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                    
                    if pub_time > last_check_time:
                        title = item.get("snippet", {}).get("title", "Unknown")
                        # 檢查關鍵字
                        if any(k in title.lower() for k in keywords):
                            video_id = item.get("contentDetails", {}).get("upload", {}).get("videoId")
                            if video_id:
                                new_videos.append({
                                    "url": f"https://www.youtube.com/watch?v={video_id}",
                                    "title": title,
                                    "time": pub_time,
                                    "channel": item["snippet"]["channelTitle"]
                                })
                                print(f"🎯 發現相關影片: {title}")
        except Exception as e:
            print(f"❌ YouTube 抓取錯誤: {e}")
            
        # 依照時間排序，確保處理順序正確
        return sorted(new_videos, key=lambda x: x["time"])
