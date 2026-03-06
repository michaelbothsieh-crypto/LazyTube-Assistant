from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from datetime import datetime, timezone
from app.config import Config

class YouTubeService:
    """
    /// YouTube API 封裝模組
    /// 負責與 YouTube Data API 互動與影片過濾
    """

    def __init__(self):
        """
        /// 初始化 YouTube 服務連線
        """
        self.service = self._get_service()

    def _get_service(self):
        """
        /// 建立並驗證 Google API 用戶端
        """
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
        /// 抓取訂閱頻道中感興趣的遊戲影片
        """
        new_videos = []
        try:
            subs_request = self.service.subscriptions().list(
                part="snippet,contentDetails", mine=True, maxResults=50, order="relevance"
            )
            subs_response = subs_request.execute()
            
            keywords = Config.get_keywords()
            
            for sub in subs_response.get("items", []):
                channel_id = sub["snippet"]["resourceId"]["channelId"]
                channel_title = sub["snippet"]["title"]
                
                activities = self.service.activities().list(
                    part="snippet,contentDetails", channelId=channel_id, maxResults=5
                ).execute()
                
                for item in activities.get("items", []):
                    if item["snippet"]["type"] == "upload":
                        pub_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                        if pub_time > last_check_time:
                            title = item.get("snippet", {}).get("title", "Unknown")
                            if any(k in title.lower() for k in keywords):
                                video_id = item.get("contentDetails", {}).get("upload", {}).get("videoId")
                                if video_id:
                                    new_videos.append({
                                        "url": f"https://www.youtube.com/watch?v={video_id}",
                                        "title": title,
                                        "time": pub_time,
                                        "channel": channel_title
                                    })
        except Exception as e:
            print(f"❌ YouTube 抓取錯誤: {e}")
        return sorted(new_videos, key=lambda x: x["time"])
