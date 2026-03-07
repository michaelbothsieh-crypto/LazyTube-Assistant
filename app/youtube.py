import re
from datetime import datetime

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Config


class YouTubeService:
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

    def _parse_duration_seconds(self, duration_text):
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

    def _fetch_video_durations(self, video_ids):
        if not video_ids:
            return {}

        response = self.service.videos().list(
            part="contentDetails",
            id=",".join(video_ids),
            maxResults=len(video_ids),
        ).execute()

        durations = {}
        for item in response.get("items", []):
            durations[item["id"]] = self._parse_duration_seconds(
                item.get("contentDetails", {}).get("duration", "")
            )
        return durations

    def fetch_new_game_videos(self, last_check_time):
        new_videos = []
        try:
            response = self.service.activities().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=50,
            ).execute()

            keywords = Config.get_keywords()
            all_items = response.get("items", [])
            upload_items = [
                item for item in all_items if item.get("snippet", {}).get("type") == "upload"
            ]

            recent_candidates = []
            for item in upload_items:
                published_at = item.get("snippet", {}).get("publishedAt")
                if not published_at:
                    continue

                pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                if pub_time <= last_check_time:
                    continue

                title = item.get("snippet", {}).get("title", "Unknown")
                if keywords and not any(keyword in title.lower() for keyword in keywords):
                    continue

                video_id = item.get("contentDetails", {}).get("upload", {}).get("videoId")
                if not video_id:
                    continue

                recent_candidates.append(
                    {
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "title": title,
                        "time": pub_time,
                        "channel": item.get("snippet", {}).get("channelTitle", "Unknown"),
                    }
                )

            durations = self._fetch_video_durations(
                [candidate["video_id"] for candidate in recent_candidates]
            )

            shorts_skipped = 0
            for candidate in recent_candidates:
                duration_seconds = durations.get(candidate["video_id"], 0)
                if duration_seconds <= Config.SHORTS_MAX_SECONDS:
                    shorts_skipped += 1
                    print(f"略過 Shorts 或短片：{candidate['title']}（{duration_seconds} 秒）")
                    continue

                candidate["duration_seconds"] = duration_seconds
                new_videos.append(candidate)
                print(f"找到符合條件的長影片：{candidate['title']}（{duration_seconds} 秒）")

            print(f"本輪共取得 {len(all_items)} 筆動態，upload 類型 {len(upload_items)} 筆。")
            print(
                "經過時間與關鍵字篩選後，候選影片 "
                f"{len(recent_candidates)} 支；略過 Shorts/短片 {shorts_skipped} 支；"
                f"最終保留長影片 {len(new_videos)} 支。"
            )
        except Exception as error:
            print(f"YouTube 抓取失敗：{error}")

        return sorted(new_videos, key=lambda item: item["time"])
