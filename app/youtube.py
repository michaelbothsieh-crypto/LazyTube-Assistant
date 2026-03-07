import re
from datetime import datetime, timedelta, timezone

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build

from app.config import Config


def format_taipei_time(dt):
    return dt.astimezone(timezone(timedelta(hours=8))).strftime("%Y-%m-%d %H:%M:%S")


class YouTubeService:
    """
    /// YouTube API 封裝模組
    /// 負責取得訂閱頻道的新上傳影片，並排除 Shorts
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

    def _parse_duration_seconds(self, duration_text):
        """將 YouTube ISO 8601 影片時長轉成秒數。"""
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
        """批次取得影片時長，避免逐支查詢浪費配額。"""
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
        """
        /// 使用 activities().list(mine=True) 取得訂閱頻道最新活動
        /// 再用 videos().list 補抓時長，排除 Shorts，只保留長影片
        """
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

            print(f"本輪共取得 {len(all_items)} 筆動態，其中 upload 類型 {len(upload_items)} 筆。")

            recent_candidates = []
            time_filtered = 0
            keyword_filtered = 0
            missing_video_id = 0

            for item in upload_items:
                snippet = item.get("snippet", {})
                published_at = snippet.get("publishedAt")
                title = snippet.get("title", "Unknown")
                channel = snippet.get("channelTitle", "Unknown")

                if not published_at:
                    print(f"略過影片：{title}，原因：缺少 publishedAt。")
                    continue

                pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                print(
                    f"檢查 upload：{title} | 頻道：{channel} | 發布時間："
                    f"{format_taipei_time(pub_time)}（台北時間）"
                )

                if pub_time <= last_check_time:
                    time_filtered += 1
                    # 只有在時間非常接近（1小時內）時才輸出略過訊息，減少舊影片產生的雜訊
                    if (last_check_time - pub_time).total_seconds() < 3600:
                        print(
                            f"略過影片：{title}，原因：發布時間早於或等於上次檢查時間 "
                            f"{format_taipei_time(last_check_time)}。"
                        )
                    continue

                if keywords and not any(keyword in title.lower() for keyword in keywords):
                    keyword_filtered += 1
                    print(f"略過影片：{title}，原因：未命中關鍵字 {keywords}。")
                    continue

                video_id = item.get("contentDetails", {}).get("upload", {}).get("videoId")
                if not video_id:
                    missing_video_id += 1
                    print(f"略過影片：{title}，原因：缺少 videoId。")
                    continue

                recent_candidates.append(
                    {
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "title": title,
                        "time": pub_time,
                        "channel": channel,
                    }
                )
                print(f"通過前置篩選：{title}")

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
                print(f"保留長影片：{candidate['title']}（{duration_seconds} 秒）")

            print(
                f"前置篩選結果：時間略過 {time_filtered} 支，"
                f"關鍵字略過 {keyword_filtered} 支，缺少 videoId {missing_video_id} 支，"
                f"進入 Shorts 檢查 {len(recent_candidates)} 支。"
            )
            print(
                f"Shorts 篩選結果：略過 Shorts/短片 {shorts_skipped} 支，"
                f"最終保留長影片 {len(new_videos)} 支。"
            )
        except Exception as error:
            print(f"YouTube 抓取失敗：{error}")

        return sorted(new_videos, key=lambda item: item["time"])
