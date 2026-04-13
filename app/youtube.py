import re
import time
from functools import wraps
from datetime import datetime
import os
import httpx

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
    """YouTube API wrapper with high-resilience resolution."""

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
    def get_channel_info(self, channel_url: str) -> dict:
        """Resolve channel URL to channel ID and title with maximum success rate."""
        import urllib.parse
        if not channel_url: return {}
        
        # 1. 基礎清理
        clean_url = channel_url.split("?")[0].split("#")[0].strip().rstrip("/")
        decoded_url = urllib.parse.unquote(clean_url)
        
        # 2. 策略 A：直接提取 UCID (最精準)
        ucid_match = re.search(r"(UC[a-zA-Z0-9_-]{22})", decoded_url)
        if ucid_match:
            cid = ucid_match.group(1)
            try:
                res = self.service.channels().list(part="snippet", id=cid).execute()
                if res.get("items"):
                    item = res["items"][0]
                    return {"id": item["id"], "title": item["snippet"]["title"]}
            except: pass

        # 3. 策略 B：Handle (@name) 查詢
        handle_match = re.search(r"@([a-zA-Z0-9._-]+)", decoded_url)
        if handle_match:
            handle = handle_match.group(1)
            for h in ["@" + handle, handle]:
                try:
                    res = self.service.channels().list(part="snippet", forHandle=h).execute()
                    if res.get("items"):
                        item = res["items"][0]
                        return {"id": item["id"], "title": item["snippet"]["title"]}
                except: continue

        # 4. 策略 C：網頁物理爬取 (針對 Handle 網址)
        if "@" in decoded_url:
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
                with httpx.Client(timeout=8.0, follow_redirects=True, headers=headers) as client:
                    resp = client.get(clean_url)
                    if resp.status_code == 200:
                        # 從網頁中抓取關鍵 ID
                        m = re.search(r"\"browse_id\":\"(UC[a-zA-Z0-9_-]{22})\"", resp.text)
                        if m:
                            cid = m.group(1)
                            res = self.service.channels().list(part="snippet", id=cid).execute()
                            if res.get("items"):
                                return {"id": res["items"][0]["id"], "title": res["items"][0]["snippet"]["title"]}
            except: pass

        # 5. 策略 D：搜尋 API (保底)
        try:
            q = handle_match.group(1) if handle_match else decoded_url.split("/")[-1]
            search_res = self.service.search().list(q=q, type="channel", part="snippet", maxResults=1).execute()
            if search_res.get("items"):
                item = search_res["items"][0]
                return {"id": item["snippet"]["channelId"], "title": item["snippet"]["title"]}
        except: pass

        return {}

    @retry(max_attempts=2)
    def _get_playlist_items(self, playlist_id: str, limit: int = 5) -> list:
        try:
            res = self.service.playlistItems().list(part="snippet,contentDetails", playlistId=playlist_id, maxResults=limit).execute()
            return res.get("items", [])
        except: return []

    @retry(max_attempts=2)
    def _get_uploads_playlist_ids(self, channel_ids: list) -> dict:
        mapping = {}
        for i in range(0, len(channel_ids), 50):
            batch = channel_ids[i : i + 50]
            res = self.service.channels().list(part="contentDetails", id=",".join(batch), maxResults=len(batch)).execute()
            for item in res.get("items", []):
                mapping[item["id"]] = item["contentDetails"]["relatedPlaylists"]["uploads"]
        return mapping

    def _parse_duration_seconds(self, duration_text: str) -> int:
        if not duration_text: return 0
        match = re.fullmatch(r"PT(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?", duration_text)
        if not match: return 0
        h, m, s = int(match.group("hours") or 0), int(match.group("minutes") or 0), int(match.group("seconds") or 0)
        return h * 3600 + m * 60 + s

    @retry(max_attempts=3)
    def _fetch_video_details(self, video_ids: list) -> dict:
        if not video_ids: return {}
        details = {"durations": {}, "categories": {}, "live_status": {}, "has_live_details": {}, "titles": {}}
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i : i + 50]
            res = self.service.videos().list(part="contentDetails,snippet,liveStreamingDetails", id=",".join(batch_ids), maxResults=len(batch_ids)).execute()
            for item in res.get("items", []):
                vid = item["id"]
                details["durations"][vid] = self._parse_duration_seconds(item.get("contentDetails", {}).get("duration", ""))
                details["categories"][vid] = item["snippet"].get("categoryId")
                details["live_status"][vid] = (item["snippet"].get("liveBroadcastContent") or "").lower()
                details["has_live_details"][vid] = bool(item.get("liveStreamingDetails"))
                details["titles"][vid] = item["snippet"].get("title", "")
        return details

    def fetch_new_game_videos(self, last_check_time: datetime) -> list:
        new_videos = []
        try:
            req = self.service.subscriptions().list(part="snippet", mine=True, maxResults=50)
            resp = req.execute()
            channel_ids = [item["snippet"]["resourceId"]["channelId"] for item in resp.get("items", [])]
            if not channel_ids: return []
            uploads_playlists = self._get_uploads_playlist_ids(channel_ids)
            candidate_videos = []
            for _, playlist_id in uploads_playlists.items():
                items = self._get_playlist_items(playlist_id)
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
            for video in candidate_videos:
                vid = video["video_id"]
                if details["categories"].get(vid) != "20": continue
                if details["live_status"].get(vid) in {"live", "upcoming"} or details["has_live_details"].get(vid): continue
                duration = details["durations"].get(vid, 0)
                if duration <= Config.SHORTS_MAX_SECONDS or any(t in video["title"].lower() for t in ["#short", "shorts"]): continue
                if Config.MAX_VIDEO_SECONDS > 0 and duration > Config.MAX_VIDEO_SECONDS: continue
                new_videos.append(video)
        except: pass
        return sorted(new_videos, key=lambda x: x["time"])
