from unittest.mock import patch

from app.notifier import Notifier


def test_send_error_includes_url():
    with patch("app.notifier.service.send_telegram_text", return_value=True) as mocked_send:
        assert Notifier.send_error("123", "failed", url="https://example.com")
        mocked_send.assert_called_once()
        sent_text = mocked_send.call_args.args[1]
        assert "failed" in sent_text
        assert "https://example.com" in sent_text


def test_send_photo_for_line_falls_back_to_document():
    with patch("app.notifier.service.is_line_chat", return_value=True), patch(
        "app.notifier.service.Notifier.send_document",
        return_value=True,
    ) as mocked_send_document:
        assert Notifier.send_photo("U123", "C:\\tmp\\test.png", caption="preview")
        mocked_send_document.assert_called_once()


# --- delete_pending_message tests ---

def test_delete_pending_message_calls_delete_on_telegram():
    with patch("app.notifier.service.is_line_chat", return_value=False), \
         patch("app.notifier.service.delete_message") as mock_delete:
        Notifier.delete_pending_message("123456", "789")
        mock_delete.assert_called_once_with("123456", "789")


def test_delete_pending_message_skips_line_chat():
    with patch("app.notifier.service.is_line_chat", return_value=True), \
         patch("app.notifier.service.delete_message") as mock_delete:
        Notifier.delete_pending_message("U123456", "789")
        mock_delete.assert_not_called()


def test_delete_pending_message_skips_when_no_message_id():
    with patch("app.notifier.service.is_line_chat", return_value=False), \
         patch("app.notifier.service.delete_message") as mock_delete:
        Notifier.delete_pending_message("123456", None)
        Notifier.delete_pending_message("123456", "")
        mock_delete.assert_not_called()


def test_delete_pending_message_handles_exception_gracefully():
    with patch("app.notifier.service.is_line_chat", return_value=False), \
         patch("app.notifier.service.delete_message", side_effect=Exception("network error")), \
         patch("app.notifier.service.logger") as mock_logger:
        # Should not raise
        Notifier.delete_pending_message("123456", "789")
        mock_logger.warning.assert_called_once()
        warning_args = mock_logger.warning.call_args.args
        assert "789" in str(warning_args)
