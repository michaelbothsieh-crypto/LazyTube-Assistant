import asyncio

from api.handlers.tg_webhook import commands_dispatch
from api.handlers.tg_webhook.parsing import (
    parse_batch_request,
    parse_research_request,
    parse_slide_request,
    parse_subscription_request,
)
from api.handlers.tg_webhook.validation import normalize_command_text, validate_url
from api.handlers.tg_webhook.router import COMMAND_HANDLERS
from app.notebook.parsing import parse_query_output
from app.threads_analyzer import ThreadsAnalysis


def test_normalize_command_text_removes_bot_suffix():
    assert normalize_command_text("/nlm@LazyTubeBot https://example.com") == "/nlm https://example.com"


def test_threads_command_is_registered():
    assert "/threads" in COMMAND_HANDLERS


def test_validate_url_rejects_non_http():
    assert validate_url("ftp://example.com") is not None


def test_parse_slide_request_reads_language_and_format():
    request = parse_slide_request("/slide https://example.com focus text en pptx")
    assert request is not None
    assert request.url == "https://example.com"
    assert request.language == "en"
    assert request.file_format == "pptx"
    assert request.prompt == "focus text"


def test_parse_batch_request_extracts_urls_and_prompt():
    urls, prompt = parse_batch_request("/batch https://a.com, https://b.com compare them")
    assert urls == ["https://a.com", "https://b.com"]
    assert "compare them" in prompt


def test_parse_research_request_reads_mode():
    topic, mode = parse_research_request("/research ai agents deep")
    assert topic == "ai agents"
    assert mode == "deep"


def test_parse_subscription_request_extracts_time():
    url, prompt, preferred_time = parse_subscription_request("/sub https://youtube.com/@demo custom prompt 11")
    assert url == "https://youtube.com/@demo"
    assert "custom prompt" in prompt
    assert preferred_time == "12:00"


def test_parse_query_output_strips_numeric_citations():
    output = parse_query_output("營收成長 [1]，資料中心需求增加 [2, 3]，燃料電池受惠 [4-6]。")
    assert "[1]" not in output
    assert "[2, 3]" not in output
    assert "[4-6]" not in output
    assert output == "營收成長，資料中心需求增加，燃料電池受惠。"


def test_handle_threads_waits_for_full_analysis(monkeypatch):
    events: list[tuple[str, str]] = []

    async def fake_send_message(chat_id: str, text: str):
        events.append(("text", text))
        return {"ok": True, "result": {"message_id": 99}}

    def fake_analyze(url: str, *, include_media: bool = True) -> ThreadsAnalysis:
        assert include_media is True
        return ThreadsAnalysis(
            url=url,
            post_lines=["貼文內容"],
            reply_lines=["同意"],
            source="worker",
            video_url="https://example.com/video.mp4",
        )

    def fake_send_video(chat_id: str, video_url: str):
        events.append(("video", video_url))
        return True

    monkeypatch.setattr(commands_dispatch, "send_telegram_message", fake_send_message)
    monkeypatch.setattr(commands_dispatch, "analyze_threads_url", fake_analyze)
    monkeypatch.setattr(commands_dispatch.Notifier, "send_video_url", fake_send_video)
    monkeypatch.setattr(commands_dispatch.Notifier, "delete_pending_message", lambda *_args: None)

    asyncio.run(commands_dispatch.handle_threads("123", "/threads https://threads.com/@demo/post/abc"))

    assert events[0] == ("text", "<b>Threads 解析中</b>")
    assert events[1] == ("video", "https://example.com/video.mp4")
    assert events[2][0] == "text"
    assert "貼文內容" in events[2][1]
    assert "影片狀態：已截取影片" in events[2][1]
