import re
import time
from functools import wraps
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Config


def retry(max_attempts=3, delay=2):
    """Retry a function on transient errors."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as error:
                    last_exception = error
                    if attempt < max_attempts - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception
        return wrapper
    return decorator


class YouTubeService:
    """YouTube API wrapper."""

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
        if not creds.valid:
            if creds.expired and creds.refresh_token:
                creds.refresh(Request())
        return build("youtube", "v3", credentials=creds)

    @retry(max_attempts=2)
    def _get_playlist_items(self, playlist_id: str, limit: int = 5) -> list:
        """Fetch recent playlist items."""
        try:
            res = self.service.playlistItems().list(
                part="snippet,contentDetails",
                playlistId=playlist_id,
                maxResults=limit,
            ).execute()
            return res.get("items", [])
        except Exception as error:
            print(f"Failed to fetch playlist items: {error}")
            return []

    @retry(max_attempts=2)
    def _get_uploads_playlist_ids(self, channel_ids: list) -> dict:
        """Map channel IDs to uploads playlist IDs."""
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
        """Resolve channel URL to channel ID and title with maximum resilience."""
        import urllib.parse
        if not channel_url: return {}
        
        # 1. 清理與解碼
        clean_url = channel_url.split("?")[0].split("#")[0].rstrip("/")
        decoded_url = urllib.parse.unquote(clean_url)
        
        # 2. 收集所有可能的候選字串 (用來嘗試不同的 API 參數)
        candidates = [] # List of (method, value)
        
        # 提取 UCID (24位元)
        ucid_match = re.search(r"(UC[a-zA-Z0-9_-]{22})", decoded_url)
        if ucid_match:
            candidates.append(("id", ucid_match.group(1)))
        
        # 提取 Handle (@name)
        handle_match = re.search(r"/(@[a-zA-Z0-9._-]+)", decoded_url)
        if handle_match:
            candidates.append(("forHandle", handle_match.group(1)))
        
        # 提取路徑片段
        if "youtube.com/" in decoded_url:
            path_part = decoded_url.split("youtube.com/")[1]
            parts = [p for p in path_part.split("/") if p]
            if parts:
                # 取得關鍵識別字 (例如 /c/name 中的 name)
                val = parts[1] if parts[0] in ["c", "user", "channel"] and len(parts) > 1 else parts[0]
                if val.startswith("@"):
                    candidates.append(("forHandle", val))
                else:
                    candidates.append(("id", val))
                    candidates.append(("forUsername", val))

        # 3. 依序嘗試 API 呼叫，直到成功為止
        processed_values = set()
        for method, value in candidates:
            cache_key = f"{method}:{value}"
            if cache_key in processed_values: continue
            processed_values.add(cache_key)
            
            try:
                kwargs = {method: value, "part": "snippet"}
                res = self.service.channels().list(**kwargs).execute()
                if res.get("items"):
                    item = res["items"][0]
                    return {"id": item["id"], "title": item["snippet"]["title"]}
            except:
                continue

        # 4. 最終手段：使用搜尋 API (全文檢索)
        try:
            search_res = self.service.search().list(
                q=clean_url, type="channel", part="snippet", maxResults=1
            ).execute()
            if search_res.get("items"):
                item = search_res["items"][0]
                return {"id": item["snippet"]["channelId"], "title": item["snippet"]["title"]}
        except Exception as e:
            print(f"Final search fallback failed: {e}")

        return {}

    def _parse_duration_seconds(self, duration_text: str) -> int:
        if not duration_text:
            return 0
        match = re.fullmatch(
            r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?",
            duration_text,
        )
        if not match:
            return 0
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)
        return hours * 3600 + minutes * 60 + seconds

    @retry(max_attempts=3)
    def _fetch_video_details(self, video_ids: list) -> dict:
        if not video_ids:
            return {}
        details = {"durations": {}, "categories": {}, "live_status": {}, "has_live_details": {}, "titles": {}}
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i : i + 50]
            response = self.service.videos().list(
                part="contentDetails,snippet,liveStreamingDetails",
                id=",".join(batch_ids),
                maxResults=len(batch_ids),
            ).execute()
            for item in response.get("items", []):
                vid = item["id"]
                duration_text = item.get("contentDetails", {}).get("duration", "")
                details["durations"][vid] = self._parse_duration_seconds(duration_text)
                details["categories"][vid] = item["snippet"].get("categoryId")
                details["live_status"][vid] = (item["snippet"].get("liveBroadcastContent") or "").lower()
                details["has_live_details"][vid] = bool(item.get("liveStreamingDetails"))
                details["titles"][vid] = item["snippet"].get("title", "")
        return details

    def fetch_new_game_videos(self, last_check_time: datetime) -> list:
        """Scan subscriptions and return new gaming videos after last check time."""
        new_videos = []
        try:
            req = self.service.subscriptions().list(part="snippet", mine=True, maxResults=50)
            resp = req.execute()
            channel_ids = [item["snippet"]["resourceId"]["channelId"] for item in resp.get("items", [])]
            if not channel_ids:
                return []

            uploads_playlists = self._get_uploads_playlist_ids(channel_ids)
            candidate_videos = []
            for _, playlist_id in uploads_playlists.items():
                items = self._get_playlist_items(playlist_id)
                for item in items:
                    pub_time = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
                    if pub_time <= last_check_time:
                        continue
                    candidate_videos.append({
                        "video_id": item["contentDetails"]["videoId"],
                        "title": item["snippet"]["title"],
                        "channel": item["snippet"]["channelTitle"],
                        "time": pub_time,
                        "url": f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}",
                    })

            if not candidate_videos:
                return []

            vids = [v["video_id"] for v in candidate_videos]
            details = self._fetch_video_details(vids)
            keywords = Config.get_keywords()

            for video in candidate_videos:
                vid = video["video_id"]
                category_id = details["categories"].get(vid)
                duration_seconds = details["durations"].get(vid, 0)
                live_status = details["live_status"].get(vid, "")
                has_live_details = details["has_live_details"].get(vid, False)

                if category_id != "20":
                    continue

                if live_status in {"live", "upcoming"} or has_live_details:
                    print(f"Skip live stream: {video['title']} ({live_status})")
                    continue

                # 強化版 Shorts 過濾邏輯
                is_shorts_by_duration = duration_seconds <= Config.SHORTS_MAX_SECONDS
                title_lower = video["title"].lower()
                is_shorts_by_title = any(tag in title_lower for tag in ["#short", "shorts", "#短片", "#短影音"])

                if is_shorts_by_duration or is_shorts_by_title:
                    continue

                if Config.MAX_VIDEO_SECONDS > 0 and duration_seconds > Config.MAX_VIDEO_SECONDS:
                    continue

                if keywords and not any(keyword in video["title"].lower() for keyword in keywords):
                    continue

                video["duration_seconds"] = duration_seconds
                new_videos.append(video)

        except Exception as error:
            print(f"Fetch error: {error}")

        return sorted(new_videos, key=lambda item: item["time"])
