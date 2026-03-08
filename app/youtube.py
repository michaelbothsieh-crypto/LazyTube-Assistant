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

    def _get_subscriptions(self, limit=50):
        """獲取使用者的訂閱頻道清單。"""
        try:
            subscriptions = []
            request = self.service.subscriptions().list(
                part="snippet,contentDetails",
                mine=True,
                maxResults=limit
            )
            response = request.execute()
            for item in response.get("items", []):
                subscriptions.append({
                    "id": item["snippet"]["resourceId"]["channelId"],
                    "title": item["snippet"]["title"]
                })
            return subscriptions
        except Exception as e:
            print(f"獲取訂閱清單失敗: {e}")
            return []

    def _get_channels_uploads_playlists(self, channel_ids):
        """獲取多個頻道的『上傳影片』播放清單 ID。"""
        if not channel_ids:
            return {}
        
        playlist_map = {}
        # 批次查詢，每次上限 50 個
        for i in range(0, len(channel_ids), 50):
            batch_ids = channel_ids[i:i+50]
            response = self.service.channels().list(
                part="contentDetails",
                id=",".join(batch_ids),
                maxResults=len(batch_ids)
            ).execute()
            
            for item in response.get("items", []):
                playlist_map[item["id"]] = item["contentDetails"]["relatedPlaylists"]["uploads"]
        
        return playlist_map

    def _get_video_categories(self, video_ids):
        """批次獲取影片的分類 ID。"""
        if not video_ids:
            return {}
        
        categories = {}
        for i in range(0, len(video_ids), 50):
            batch_ids = video_ids[i:i+50]
            response = self.service.videos().list(
                part="snippet",
                id=",".join(batch_ids),
                maxResults=len(batch_ids)
            ).execute()
            
            for item in response.get("items", []):
                categories[item["id"]] = item["snippet"].get("categoryId")
        return categories

    def fetch_new_game_videos(self, last_check_time):
        """
        /// 重構版：主動遍歷訂閱頻道，並過濾遊戲類別
        /// 1. 獲取訂閱清單
        /// 2. 檢查每個頻道最新上傳
        /// 3. 過濾 Gaming (ID: 20)
        """
        new_videos = []
        try:
            # 1. 獲取訂閱清單 (前 50 個)
            subscriptions = self._get_subscriptions(50)
            if not subscriptions:
                print("未找到訂閱頻道。")
                return []
            
            print(f"開始掃描 {len(subscriptions)} 個訂閱頻道的更新...")

            # 2. 獲取所有頻道的上傳播放清單 ID
            channel_ids = [s["id"] for s in subscriptions]
            uploads_playlists = self._get_channels_uploads_playlists(channel_ids)

            # 3. 遍歷每個播放清單，抓取最近 2 個影片 (減少配額消耗)
            all_candidate_videos = []
            for channel in subscriptions:
                playlist_id = uploads_playlists.get(channel["id"])
                if not playlist_id:
                    continue
                
                try:
                    items_res = self.service.playlistItems().list(
                        part="snippet,contentDetails",
                        playlistId=playlist_id,
                        maxResults=2
                    ).execute()
                    
                    for item in items_res.get("items", []):
                        published_at = item["snippet"]["publishedAt"]
                        pub_time = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
                        
                        # 時間過濾與噪音抑制
                        is_old = pub_time <= last_check_time
                        if is_old:
                            continue
                            
                        all_candidate_videos.append({
                            "video_id": item["contentDetails"]["videoId"],
                            "title": item["snippet"]["title"],
                            "channel": item["snippet"]["videoOwnerChannelTitle"] or item["snippet"]["channelTitle"],
                            "time": pub_time,
                            "url": f"https://www.youtube.com/watch?v={item['contentDetails']['videoId']}"
                        })
                except Exception:
                    continue # 略過私有或有問題的播放清單

            if not all_candidate_videos:
                print("所有訂閱頻道均無新上傳。")
                return []

            # 4. 批次檢查類別與時長
            video_ids = [v["video_id"] for v in all_candidate_videos]
            categories = self._get_video_categories(video_ids)
            durations = self._fetch_video_durations(video_ids)

            keywords = Config.get_keywords()
            
            for video in all_candidate_videos:
                vid_id = video["video_id"]
                category_id = categories.get(vid_id)
                duration_seconds = durations.get(vid_id, 0)
                
                # 類別過濾：只保留 Gaming (20)
                if category_id != "20":
                    continue # 非遊戲類，直接略過
                
                # 時長過濾：排除 Shorts
                if duration_seconds <= Config.SHORTS_MAX_SECONDS:
                    continue
                
                # 關鍵字過濾
                if keywords and not any(keyword in video["title"].lower() for keyword in keywords):
                    continue

                video["duration_seconds"] = duration_seconds
                new_videos.append(video)
                print(f"發現新遊戲影片：{video['title']} | 頻道：{video['channel']}（{duration_seconds} 秒）")

            print(f"掃描完成，本輪共發現 {len(new_videos)} 支符合條件的新遊戲影片。")
            
        except Exception as error:
            print(f"YouTube 抓取失敗：{error}")

        return sorted(new_videos, key=lambda item: item["time"])
