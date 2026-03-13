import re
import time
from functools import wraps
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Config


def retry(max_attempts=3, delay=2):
    """簡單的重試裝飾器"""
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
    """YouTube 數據服務類別"""

    def __init__(self):
        self.service = self._get_service()

    def _get_service(self):
        """初始化並刷新 YouTube API 憑證"""
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

    @retry(max_attempts=2)
    def _get_playlist_items(self, playlist_id: str, limit: int = 5) -> list:
        """獲取播放清單項目的最新影片"""
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
        """獲取頻道的上傳播放清單 ID"""
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
    def get_channel_info(self, channel_url: str) -> dict:
        """根據頻道 URL 獲取頻道 ID 與標題"""
        import urllib.parse
        channel_url = urllib.parse.unquote(channel_url)
        handle = None
        if "/@" in channel_url:
            handle = "@" + channel_url.split("/@")[1].split("/")[0]
        elif "youtube.com/" in channel_url:
            parts = channel_url.split("youtube.com/")[1].split("/")
            if len(parts) > 0:
                if parts[0] in ["c", "user", "channel"] and len(parts) > 1:
                    handle = parts[1]
                else:
                    handle = parts[0]
        
        if not handle:
            # 嘗試直接提取 ID (UC...)
            match = re.search(r"(UC[a-zA-Z0-9_-]{22})", channel_url)
            if match: handle = match.group(1)

        if not handle: return {}

        try:
            if handle.startswith("UC") and len(handle) >= 20:
                res = self.service.channels().list(part="snippet", id=handle).execute()
            else:
                if handle.startswith("@"):
                    res = self.service.channels().list(part="snippet", forHandle=handle).execute()
                else:
                    search_res = self.service.search().list(
                        q=handle, type="channel", part="snippet", maxResults=1
                    ).execute()
                    if search_res.get("items"):
                        item = search_res["items"][0]
                        return {"id": item["snippet"]["channelId"], "title": item["snippet"]["title"]}
                    return {}

            if res.get("items"):
                item = res["items"][0]
                return {"id": item["id"], "title": item["snippet"]["title"]}
        except Exception as e:
            print(f"獲取頻道資訊失敗: {e}")
        
        return {}

    @retry(max_attempts=3)
    def _fetch_video_details(self, video_ids: list) -> dict:
        if not video_ids: return {}
        details = {"durations": {}, "categories": {}, "live_status": {}}
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i : i + 50]
            response = self.service.videos().list(
                part="contentDetails,snippet",
                id=",".join(batch_ids),
                maxResults=len(batch_ids),
            ).execute()
            for item in response.get("items", []):
                vid = item["id"]
                duration_text = item.get("contentDetails", {}).get("duration", "")
                details["durations"][vid] = self._parse_duration_seconds(duration_text)
                details["categories"][vid] = item["snippet"].get("categoryId")
                details["live_status"][vid] = item["snippet"].get("liveBroadcastContent")
        return details

    def _parse_duration_seconds(self, duration_text: str) -> int:
        if not duration_text: return 0
        match = re.fullmatch(r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?", duration_text)
        if not match: return 0
        h, m, s = int(match.group("hours") or 0), int(match.group("minutes") or 0), int(match.group("seconds") or 0)
        return h * 3600 + m * 60 + s

    def fetch_new_game_videos(self, last_check_time: datetime) -> list:
        """獲取帳號訂閱的新遊戲影片 (全域掃描用)"""
        new_videos = []
        try:
            # 獲取本人訂閱
            req = self.service.subscriptions().list(part="snippet", mine=True, maxResults=50)
            resp = req.execute()
            channel_ids = [item["snippet"]["resourceId"]["channelId"] for item in resp.get("items", [])]
            if not channel_ids: return []

            uploads_playlists = self._get_uploads_playlist_ids(channel_ids)
            candidate_videos = []
            for cid, pid in uploads_playlists.items():
                items = self._get_playlist_items(pid)
                for item in items:
                    pub_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                    if pub_time <= last_check_time: continue
                    candidate_videos.append({
                        "video_id": item["contentDetails"]["videoId"],
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "time": pub_time,
                        "url": f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}",
                    })

            if not candidate_videos: return []
            vids = [v["video_id"] for v in candidate_videos]
            details = self._fetch_video_details(vids)
            for v in candidate_videos:
                vid = v["video_id"]
                # 僅處理類別為遊戲且非直播/預定直播的影片
                is_game = details["categories"].get(vid) == "20"
                is_standard_video = details["live_status"].get(vid) == "none"
                
                if is_game and is_standard_video:
                    new_videos.append(v)
                elif not is_standard_video:
                    print(f"⏩ 略過直播/預約影片：{v['title']} (狀態: {details['live_status'].get(vid)})")
        except Exception as e:
            print(f"全域掃描異常: {e}")
        return sorted(new_videos, key=lambda x: x["time"])
