from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from api.utils.github_dispatch import get_hashed_id
from app.notebook import NotebookService
from app.notifier import Notifier
from app.state_manager import StateManager
from app.subscription_vm import SubscriptionViewModel
from app.youtube import YouTubeService

TW_TIMEZONE = timezone(timedelta(hours=8))
ERROR_PREFIXES = ("error:", "failed:", "unable to", "could not")


@dataclass(slots=True)
class GroupExecutionContext:
    target_chat_id: str
    yt: YouTubeService
    notebook: NotebookService
    subscriptions: SubscriptionViewModel



def execute_group(chat_id: str) -> None:
    context = GroupExecutionContext(
        target_chat_id=chat_id,
        yt=YouTubeService.from_config(),
        notebook=NotebookService(),
        subscriptions=SubscriptionViewModel(),
    )

    all_subscriptions = context.subscriptions.get_all_active_subscriptions()
    if chat_id not in all_subscriptions:
        print(f"No active subscriptions for {chat_id}")
        return

    now_tw = datetime.now(TW_TIMEZONE)
    print(f"Running group executor at {now_tw.isoformat()} for {chat_id[:8]}...")

    for subscription in all_subscriptions.get(chat_id, []):
        process_subscription(context, subscription, now_tw)


def process_subscription(context: GroupExecutionContext, subscription: dict, now_tw: datetime) -> None:
    channel_id = subscription["channel_id"]
    channel_title = subscription["channel_title"]

    print(f"Checking channel: {channel_title}")
    if not should_run_subscription(subscription, now_tw):
        return

    try:
        playlist_id = context.yt._get_uploads_playlist_ids([channel_id]).get(channel_id)
        if not playlist_id:
            return

        is_first_run = subscription.get("is_first_run", False)
        items = context.yt._get_playlist_items(playlist_id, limit=1 if is_first_run else 10)
        if not items:
            return

        video_ids = [item["contentDetails"]["videoId"] for item in items]
        details = context.yt._fetch_video_details(video_ids)
        process_videos(context, subscription, channel_title, items, details, is_first_run)
        context.subscriptions.update_last_check(context.target_chat_id, channel_id, datetime.now(timezone.utc))

        signup_msg_id = subscription.get("signup_msg_id")
        if signup_msg_id:
            Notifier.delete_pending_message(context.target_chat_id, signup_msg_id)
    except Exception as exc:
        print(f"Failed to process {channel_title}: {exc}")


def should_run_subscription(subscription: dict, now_tw: datetime) -> bool:
    if subscription.get("is_first_run", False):
        return True

    preferred_time = subscription.get("preferred_time")
    last_check_str = subscription.get("last_check")
    today = now_tw.strftime("%Y-%m-%d")
    current_time = now_tw.strftime("%H:%M")

    if preferred_time:
        if not last_check_str:
            return current_time >= preferred_time
        last_check_day = datetime.fromisoformat(last_check_str).astimezone(TW_TIMEZONE).strftime("%Y-%m-%d")
        return last_check_day != today and current_time >= preferred_time

    if not last_check_str:
        return True
    return (datetime.now(timezone.utc) - datetime.fromisoformat(last_check_str)).total_seconds() > 12 * 3600


def process_videos(
    context: GroupExecutionContext,
    subscription: dict,
    channel_title: str,
    items: list[dict],
    details: dict,
    is_first_run: bool,
) -> None:
    last_check_str = subscription.get("last_check")
    window_days = 7 if is_first_run else 1
    video_window = datetime.now(timezone.utc) - timedelta(days=window_days)

    for item in items:
        published_at = datetime.fromisoformat(item["snippet"]["publishedAt"].replace("Z", "+00:00"))
        video_id = item["contentDetails"]["videoId"]
        title = item["snippet"]["title"]

        if published_at < video_window:
            continue
        if last_check_str and not is_first_run and published_at <= datetime.fromisoformat(last_check_str):
            continue

        duration = details["durations"].get(video_id, 0)
        if duration <= context.yt.shorts_max_seconds or "#shorts" in title.lower():
            continue

        url = f"https://www.youtube.com/watch?v={video_id}"
        summary = context.notebook.process_video(url, title, custom_prompt=subscription.get("custom_prompt"))
        if _should_send_summary(summary):
            Notifier.send_summary(title, url, channel_title, summary, target_chat_id=context.target_chat_id)
            StateManager.add_processed_id(video_id)

        if is_first_run:
            break


def _should_send_summary(summary: str | None) -> bool:
    if not summary:
        return False

    normalized = summary.strip()
    if not normalized:
        return False

    lowered = normalized.lower()
    return not lowered.startswith(ERROR_PREFIXES)
