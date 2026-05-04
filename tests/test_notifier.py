from unittest.mock import MagicMock, patch

from app.notifier import Notifier
from app.notifier.line_client import LINE_PUSH_URL, LineClient
from app.notifier.reporting import generate_html_report
from app.notifier.telegram_client import TelegramClient


def _mock_tg() -> MagicMock:
    return MagicMock(spec=TelegramClient)


def test_send_error_includes_url():
    mock_tg = _mock_tg()
    mock_tg.send_text.return_value = True
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=False):
        assert Notifier.send_error("123", "failed", url="https://example.com")
        mock_tg.send_text.assert_called_once()
        sent_text = mock_tg.send_text.call_args.args[1]
        assert "failed" in sent_text
        assert "https://example.com" in sent_text


def test_send_photo_for_line_falls_back_to_document():
    with patch("app.notifier.service.is_line_chat", return_value=True), patch(
        "app.notifier.service.Notifier.send_document",
        return_value=True,
    ) as mocked_send_document:
        assert Notifier.send_photo("U123", "C:\\tmp\\test.png", caption="preview")
        mocked_send_document.assert_called_once()


def test_send_photo_url_calls_telegram_url_upload():
    mock_tg = _mock_tg()
    mock_tg.send_photo_url.return_value = True
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=False):
        assert Notifier.send_photo_url("123", "https://example.com/first.jpg")
        mock_tg.send_photo_url.assert_called_once_with("123", "https://example.com/first.jpg", caption=None)


def test_send_photo_url_pushes_line_image_message():
    mock_line = MagicMock()
    mock_line.send_image_url.return_value = True
    with patch.object(Notifier, "_line", mock_line), \
         patch("app.notifier.service.is_line_chat", return_value=True):
        assert Notifier.send_photo_url("U123", "https://example.com/first.jpg")
        mock_line.send_image_url.assert_called_once_with("U123", "https://example.com/first.jpg", caption=None)


def test_send_video_url_calls_telegram_url_upload():
    mock_tg = _mock_tg()
    mock_tg.send_video_url.return_value = True
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=False):
        assert Notifier.send_video_url("123", "https://example.com/first.mp4")
        mock_tg.send_video_url.assert_called_once_with("123", "https://example.com/first.mp4", caption=None)


def test_line_client_send_image_url_owns_line_payload():
    response = MagicMock()
    response.status_code = 200
    with patch("app.notifier.line_client.post_json", return_value=response) as mocked_post:
        assert LineClient("token").send_image_url("U123", "https://example.com/first.jpg", caption="preview")

    payload = mocked_post.call_args.kwargs["payload"]
    assert mocked_post.call_args.args[0] == LINE_PUSH_URL
    assert payload["messages"][0]["type"] == "image"
    assert payload["messages"][0]["originalContentUrl"] == "https://example.com/first.jpg"
    assert payload["messages"][1] == {"type": "text", "text": "preview"}


# --- delete_pending_message tests ---

def test_delete_pending_message_calls_delete_on_telegram():
    mock_tg = _mock_tg()
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=False):
        Notifier.delete_pending_message("123456", "789")
        mock_tg.delete_message.assert_called_once_with("123456", "789")


def test_delete_pending_message_skips_line_chat():
    mock_tg = _mock_tg()
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=True):
        Notifier.delete_pending_message("U123456", "789")
        mock_tg.delete_message.assert_not_called()


def test_delete_pending_message_skips_when_no_message_id():
    mock_tg = _mock_tg()
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=False):
        Notifier.delete_pending_message("123456", None)
        Notifier.delete_pending_message("123456", "")
        mock_tg.delete_message.assert_not_called()


def test_delete_pending_message_handles_exception_gracefully():
    mock_tg = _mock_tg()
    mock_tg.delete_message.side_effect = Exception("network error")
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=False), \
         patch("app.notifier.service.logger") as mock_logger:
        Notifier.delete_pending_message("123456", "789")
        mock_logger.warning.assert_called_once()
        assert "789" in str(mock_logger.warning.call_args.args)


def test_send_report_link_strips_numeric_citations_from_mobile_preview():
    mock_tg = _mock_tg()
    mock_tg.send_text.return_value = True
    with patch.object(Notifier, "_tg", mock_tg), \
         patch("app.notifier.service.is_line_chat", return_value=False), \
         patch("app.notifier.service.Notifier.cache_html_to_redis", return_value="https://example.com/report"):
        assert Notifier.send_report_link(
            "123",
            "<html></html>",
            "",
            label="Podcast",
            title="EP1084 [1]",
            ep_date="2026-04-24",
            preview="今天大漲 [1]，但風險仍在 [2, 3]。",
        )
        sent_text = mock_tg.send_text.call_args.args[1]
        assert "EP1084 [1]" not in sent_text
        assert "今天大漲 [1]" not in sent_text
        assert "[2, 3]" not in sent_text
        assert "EP1084" in sent_text
        assert "今天大漲，但風險仍在。" in sent_text


def test_generate_html_report_strips_numeric_citations():
    html = generate_html_report(
        "Bloom Energy",
        "核心結論 [1]\n\nBloom Energy 財報優於預期 [2-4]，AI 資料中心需求增加 [5, 6]。",
    )
    assert "[1]" not in html
    assert "[2-4]" not in html
    assert "[5, 6]" not in html
    assert "Bloom Energy 財報優於預期" in html
