from app.threads_analyzer import (
    ThreadsAnalysis,
    _content_lines,
    _extract_metadata,
    _extract_first_image_url,
    _extract_first_media,
    _extract_threadster_media,
    _split_post_and_replies,
    _summarize_replies,
    is_threads_url,
)


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


def test_content_lines_removes_threads_metadata():
    lines = _content_lines(
        """
        Thread
        247K views
        amarillo_rio
        3h
        你各位猜猜這些鄉親在幹嘛？
        """
    )

    assert lines == ["你各位猜猜這些鄉親在幹嘛？"]


def test_content_lines_removes_login_and_view_noise():
    lines = _content_lines(
        """
        登入
        串文
        26 萬次瀏覽
        這幾天股市投資的操作總結：
        翻譯
        9,801
        1.1 萬
        © 2026
        """
    )

    assert lines == ["這幾天股市投資的操作總結："]


def test_content_lines_removes_emoji_from_content():
    lines = _content_lines("這些都是有錢有閒的人，不需要各位操心😂")

    assert lines == ["這些都是有錢有閒的人，不需要各位操心"]


def test_extract_metadata_finds_author_and_like_count():
    metadata = _extract_metadata(
        """
        Log in
        Thread
        247K views
        amarillo_rio
        3h
        你各位猜猜這些鄉親在幹嘛？
        台股再漲半個月就上五萬點了，
        Translate
        3.2K
        268
        51
        ttaat9087
        2h
        回覆內容
        """
    )

    assert metadata.author == "amarillo_rio"
    assert metadata.like_count == "3.2K"


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


def test_format_includes_original_url_and_omits_emoji():
    message = ThreadsAnalysis(
        url="https://www.threads.net/@demo/post/abc",
        post_lines=["你各位猜猜這些鄉親在幹嘛？"],
        reply_lines=_content_lines("在排隊等活動吧😂"),
        source="worker",
        author="demo",
        like_count="123",
        image_url="https://example.com/image.jpg",
        video_url="https://example.com/video.mp4",
    ).format()

    assert "Threads 快速解析" not in message
    assert "來源：worker" not in message
    assert "原始網址：https://www.threads.net/@demo/post/abc" in message
    assert "影片狀態：已截取影片" in message
    assert "⚡" not in message
    assert "🔗" not in message
    assert "🧵" not in message
    assert "💬" not in message
    assert "😂" not in message
    assert "發文者：demo" in message
    assert "按讚數：123" in message
    assert "貼文主旨" in message
    assert "回覆風向" in message


def test_extract_first_image_url_from_meta_tags():
    html = '<meta property="og:image" content="https://cdn.example.com/first.jpg">'

    assert _extract_first_image_url(html) == "https://cdn.example.com/first.jpg"


def test_extract_first_media_supports_video_meta_tags():
    html = """
    <meta property="og:image" content="https://cdn.example.com/first.jpg">
    <meta property="og:video" content="https://cdn.example.com/first.mp4">
    """

    media = _extract_first_media(html)

    assert media.image_url == "https://cdn.example.com/first.jpg"
    assert media.video_url == "https://cdn.example.com/first.mp4"


def test_extract_threadster_media_reads_download_links():
    html = """
    <img src="https://downloads.acxcdn.com/threadster/image?token=image-token&amp;x=1">
    <a href="https://downloads.acxcdn.com/threadster/video?token=video-token&amp;y=2">Download</a>
    """

    media = _extract_threadster_media(html)

    assert media.image_url == "https://downloads.acxcdn.com/threadster/image?token=image-token&x=1"
    assert media.video_url == "https://downloads.acxcdn.com/threadster/video?token=video-token&y=2"
