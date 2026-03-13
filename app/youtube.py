import re
import time
from functools import wraps
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Config


def retry(max_attempts=3, delay=2):
    """
    /// 簡單的重試裝飾器
    /// 用於包裹容易因網路或 API 限制而失敗的方法
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator


class YouTubeService:
    """
    /// YouTube 數據服務類別 (Model/Service Layer)
    /// 負責與 YouTube Data API v3 進行通訊
    """

    def __init__(self):
        self.service = self._get_service()

    def _get_service(self):
        """初始化並刷新 YouTube API 憑證。"""
        creds = Credentials(
            None,
            refresh_token=Config.YT_REFRESH_TOKEN,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=Config.YT_CLIENT_ID,
            client_secret=Config.YT_CLIENT_SECRET,
        )
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)

    @retry(max_attempts=3)
    def _fetch_video_details(self, video_ids: list) -> dict:
        """批次獲取影片詳細資訊（時長、分類）。"""
        if not video_ids:
            return {}
        
        details = {"durations": {}, "categories": {}}
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i : i + 50]
            response = self.service.videos().list(
                part="contentDetails,snippet",
                id=",".join(batch_ids),
                maxResults=len(batch_ids),
            ).execute()

            for item in response.get("items", []):
                vid = item["id"]
                # 處理時長
                duration_text = item.get("contentDetails", {}).get("duration", "")
                details["durations"][vid] = self._parse_duration_seconds(duration_text)
                # 處理分類
                details["categories"][vid] = item["snippet"].get("categoryId")
        
        return details

    def _parse_duration_seconds(self, duration_text: str) -> int:
        """將 YouTube ISO 8601 時長格式轉換為秒數。"""
        if not duration_text:
            return 0
        match = re.fullmatch(
            r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
            duration_text,
        )
        if not match:
            return 0
        h = int(match.group("hours") or 0)
        m = int(match.group("minutes") or 0)
        s = int(match.group("seconds") or 0)
        return h * 3600 + m * 60 + s

    @retry(max_attempts=2)
    def _get_subscriptions(self, limit=50) -> list:
        """獲取使用者訂閱的頻道列表。"""
        try:
            subscriptions = []
            request = self.service.subscriptions().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=limit,
            )
            response = request.execute()
            for item in response.get("items", []):
                subscriptions.append({
                    "id": item["snippet"]["resourceId"]["channelId"],
                    "title": item["snippet"]["title"],
                })
            return subscriptions
        except Exception as e:
            print(f"取得訂閱頻道失敗：{e}")
            return []

    def fetch_new_game_videos(self, last_check_time: datetime) -> list:
        """
        /// 獲取自上次檢查以來的新遊戲影片
        /// 1. 獲取訂閱頻道
        /// 2. 遍歷每個頻道的最新影片
        /// 3. 過濾非遊戲分類、過短影片 (Shorts) 或過長直播紀錄
        """
        new_videos = []
        try:
            subscriptions = self._get_subscriptions(50)
            if not subscriptions:
                return []

            print(f"📡 開始掃描 {len(subscriptions)} 個訂閱頻道的更新...")

            # 批次獲取 uploads 播放清單 ID
            channel_ids = [s["id"] for s in subscriptions]
            uploads_playlists = self._get_uploads_playlist_ids(channel_ids)

            candidate_videos = []
            for channel in subscriptions:
                pid = uploads_playlists.get(channel["id"])
                if not pid:
                    continue
                
                # 獲取每個頻道的最近 5 支影片
                items = self._get_playlist_items(pid)
                for item in items:
                    published_at = item["snippet"]["publishedAt"]
                    pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))

                    if pub_time <= last_check_time:
                        continue

                    candidate_videos.append({
                        "video_id": item["contentDetails"]["videoId"],
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"].get("videoOwnerChannelTitle") or item["snippet"]["channelTitle"],
                        "time": pub_time,
                        "url": f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}",
                    })

            if not candidate_videos:
                return []

            # 批次獲取詳細資訊以過濾
            vids = [v["video_id"] for v in candidate_videos]
            details = self._fetch_video_details(vids)
            keywords = Config.get_keywords()

            for v in candidate_videos:
                vid = v["video_id"]
                cat_id = details["categories"].get(vid)
                dur = details["durations"].get(vid, 0)

                # 過濾：必須是遊戲分類 (20)，且不能是 Shorts，也不能超過設定上限
                if cat_id != "20":
                    continue
                if dur <= Config.SHORTS_MAX_SECONDS:
                    continue
                if Config.MAX_VIDEO_SECONDS > 0 and dur > Config.MAX_VIDEO_SECONDS:
                    continue
                
                # 關鍵字過濾 (如果有設定)
                if keywords and not any(kw in v["title"].lower() for kw in keywords):
                    continue

                v["duration_seconds"] = dur
                new_videos.append(v)
                print(f"🎬 發現候選：{v['title']} ({dur}s)")

        except Exception as error:
            print(f"YouTube 處理流程異常：{error}")

        return sorted(new_videos, key=lambda x: x["time"])

    @retry(max_attempts=2)
    def _get_playlist_items(self, playlist_id: str, limit: int = 5) -> list:
        """獲取播放清單項目的最新影片。"""
        try:
            res = self.service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=limit
            ).execute()
            return res.get("items", [])
        except Exception as e:
            print(f"取得播放清單項目失敗: {e}")
            return []

    @retry(max_attempts=2)
    def _get_playlist_items(self, playlist_id: str, limit: int = 5) -> list:
        """獲取播放清單項目的最新影片。"""
        try:
            res = self.service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=limit
            ).execute()
            return res.get("items", [])
        except Exception as e:
            print(f"取得播放清單項目失敗: {e}")
            return []

    @retry(max_attempts=2)
    def _get_uploads_playlist_ids(self, channel_ids: list) -> dict:
        """獲取頻道的上傳播放清單 ID。"""
        mapping = {}
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i : i + 50]
            res = self.service.channels().list(
                part="contentDetails",
                id=",".join(batch),
                maxResults=len(batch),
            ).execute()
            for item in res.get("items", []):
                mapping[item["id"]] = item["contentDetails"]["relatedPlaylists"]["uploads"]
        return mapping

    @retry(max_attempts=2)
    def _get_playlist_items(self, playlist_id: str, limit=5) -> list:
        """獲取播放清單中的最近影片。"""
        try:
            res = self.service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=limit,
            ).execute()
            return res.get("items", [])
        except Exception:
            return []

