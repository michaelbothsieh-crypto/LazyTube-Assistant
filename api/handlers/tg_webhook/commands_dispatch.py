from __future__ import annotations

import asyncio
import logging

from api.utils.github_dispatch import (
    dispatch_artifact_workflow,
    dispatch_batch_workflow,
    dispatch_nlm_workflow,
    dispatch_research_workflow,
)
from api.utils.telegram import send_telegram_message
from app.notifier import Notifier
from app.threads_analyzer import analyze_threads_url

from .parsing import extract_url_and_prompt, parse_batch_request, parse_research_request, parse_slide_request, parse_threads_urls
from .utils import extract_message_id
from .validation import validate_url

logger = logging.getLogger(__name__)


async def handle_nlm(chat_id: str, text: str) -> None:
    url, prompt = extract_url_and_prompt(text)
    if not url:
        await send_telegram_message(chat_id, "用法：<code>/nlm &lt;url&gt; [prompt]</code>")
        return
    error = validate_url(url)
    if error:
        await send_telegram_message(chat_id, error)
        return

    pending = await send_telegram_message(chat_id, f"<b>摘要任務已建立</b>\n\nURL：<code>{url[:100]}</code>")
    message_id = extract_message_id(pending)
    if not await dispatch_nlm_workflow(url=url, prompt=prompt, chat_id=chat_id, message_id=message_id):
        logger.error("dispatch_nlm_workflow failed")
        await send_telegram_message(chat_id, "任務派送失敗，請稍後再試。")


async def handle_slide(chat_id: str, text: str) -> None:
    request = parse_slide_request(text)
    if not request:
        await send_telegram_message(chat_id, "用法：<code>/slide &lt;url&gt; [prompt] [lang] [pdf|pptx]</code>")
        return
    error = validate_url(request.url)
    if error:
        await send_telegram_message(chat_id, error)
        return

    pending = await send_telegram_message(
        chat_id,
        f"<b>簡報任務已建立</b>\n\nURL：<code>{request.url[:100]}</code>\n語言：<code>{request.language}</code>\n格式：<code>{request.file_format}</code>",
    )
    message_id = extract_message_id(pending)
    if not await dispatch_artifact_workflow(
        url=request.url,
        prompt=request.prompt,
        chat_id=chat_id,
        message_id=message_id,
        slide_format=request.file_format,
        slide_lang=request.language,
        artifact_type="slide_deck",
    ):
        await send_telegram_message(chat_id, "簡報任務派送失敗，請稍後再試。")


async def handle_pic(chat_id: str, text: str) -> None:
    await _handle_artifact(chat_id, text, "pic", "infographic")


async def handle_note(chat_id: str, text: str) -> None:
    await _handle_artifact(chat_id, text, "note", "report")


async def handle_batch(chat_id: str, text: str) -> None:
    urls, prompt = parse_batch_request(text)
    if not urls:
        await send_telegram_message(chat_id, "用法：<code>/batch &lt;url1, url2...&gt; [prompt]</code>")
        return

    pending = await send_telegram_message(chat_id, f"<b>批次摘要任務已建立</b>\n\n共 {len(urls)} 個網址。")
    message_id = extract_message_id(pending)
    if not await dispatch_batch_workflow(
        urls=",".join(urls),
        prompt=prompt,
        chat_id=chat_id,
        message_id=message_id,
    ):
        await send_telegram_message(chat_id, "批次任務派送失敗，請稍後再試。")


async def handle_research(chat_id: str, text: str) -> None:
    topic, mode = parse_research_request(text)
    if not topic:
        await send_telegram_message(chat_id, "用法：<code>/research &lt;topic&gt; [fast|deep]</code>")
        return

    pending = await send_telegram_message(
        chat_id,
        f"<b>研究任務已建立</b>\n\n主題：<code>{topic}</code>\n模式：<code>{mode}</code>",
    )
    message_id = extract_message_id(pending)
    if not await dispatch_research_workflow(topic=topic, mode=mode, chat_id=chat_id, message_id=message_id):
        await send_telegram_message(chat_id, "研究任務派送狀態暫時無法確認；若幾分鐘內沒有收到結果，請稍後再試。")


async def handle_threads(chat_id: str, text: str) -> None:
    urls = parse_threads_urls(text)
    if not urls:
        await send_telegram_message(chat_id, "用法：<code>/threads &lt;Threads貼文URL&gt;</code>")
        return
    if len(urls) > 1:
        await send_telegram_message(chat_id, "一次只支援解析 1 個 Threads URL，請把多個貼文分開送。")
        return

    url = urls[0]
    error = validate_url(url)
    if error:
        await send_telegram_message(chat_id, error)
        return
    if "threads.net/" not in url and "threads.com/" not in url:
        await send_telegram_message(chat_id, "請提供 Threads 貼文 URL。")
        return

    pending = await send_telegram_message(chat_id, "<b>Threads 解析中</b>")
    message_id = extract_message_id(pending)
    try:
        analysis = await asyncio.to_thread(analyze_threads_url, url)
        message = analysis.format()
        if not analysis.post_lines:
            message = "無法解析 Threads 內容，可能是私密貼文、需要登入，或頁面暫時擋爬。"
        media_sent = True
        if analysis.video_url:
            media_sent = await asyncio.to_thread(Notifier.send_video_url, chat_id, analysis.video_url, allow_download_fallback=False)
        elif analysis.image_url:
            media_sent = await asyncio.to_thread(Notifier.send_photo_url, chat_id, analysis.image_url)
        if (analysis.video_url or analysis.image_url) and not media_sent:
            message = f"{message}\n\n媒體傳送：Telegram 直傳逾時或失敗，請開原始網址查看。"
        await send_telegram_message(chat_id, message)
    finally:
        if message_id:
            Notifier.delete_pending_message(chat_id, message_id)


async def _handle_artifact(chat_id: str, text: str, command_name: str, artifact_type: str) -> None:
    url, prompt = extract_url_and_prompt(text)
    if not url:
        await send_telegram_message(chat_id, f"用法：<code>/{command_name} &lt;url&gt; [prompt]</code>")
        return
    error = validate_url(url)
    if error:
        await send_telegram_message(chat_id, error)
        return

    pending = await send_telegram_message(chat_id, f"<b>{command_name} 任務已建立</b>\n\nURL：<code>{url[:100]}</code>")
    message_id = extract_message_id(pending)
    if not await dispatch_artifact_workflow(
        url=url,
        prompt=prompt,
        chat_id=chat_id,
        message_id=message_id,
        artifact_type=artifact_type,
    ):
        await send_telegram_message(chat_id, "任務派送失敗，請稍後再試。")
