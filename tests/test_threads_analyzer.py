from app.threads_analyzer import _content_lines, _split_post_and_replies, _summarize_replies, is_threads_url


def test_is_threads_url_accepts_threads_hosts():
    assert is_threads_url("https://www.threads.net/@demo/post/abc")
    assert is_threads_url("https://threads.com/@demo/post/abc")
    assert not is_threads_url("https://example.com/@demo/post/abc")


def test_content_lines_removes_boilerplate_and_duplicates():
    lines = _content_lines(
        """
        Threads
        Log in
        台股今天很強，AI 族群帶頭。
        台股今天很強，AI 族群帶頭。
        12 likes
        """
    )

    assert lines == ["台股今天很強，AI 族群帶頭。"]


def test_split_post_and_replies_uses_reply_marker():
    post, replies = _split_post_and_replies(
        [
            "@demo",
            "這篇在講 AI 伺服器需求升溫。",
            "Replies",
            "同意，散熱也會跟著受惠。",
            "但估值已經偏高？",
        ]
    )

    assert "這篇在講 AI 伺服器需求升溫。" in post
    assert replies == ["同意，散熱也會跟著受惠。", "但估值已經偏高？"]


def test_summarize_replies_reports_tone_and_samples():
    summary = _summarize_replies(["同意這個看法", "但價格可能太高？"])

    assert "整體風向" in summary
    assert "代表回覆" in summary
    assert "同意這個看法" in summary
