from api.handlers.tg_webhook.parsing import (
    parse_batch_request,
    parse_research_request,
    parse_slide_request,
    parse_subscription_request,
)
from api.handlers.tg_webhook.validation import normalize_command_text, validate_url
from app.notebook.parsing import parse_query_output


def test_normalize_command_text_removes_bot_suffix():
    assert normalize_command_text("/nlm@LazyTubeBot https://example.com") == "/nlm https://example.com"


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
