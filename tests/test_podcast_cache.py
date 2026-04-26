from app.podcast_cache import build_analysis_cache_key


def test_build_analysis_cache_key_is_stable():
    key1 = build_analysis_cache_key("https://example.com/feed.xml", "guid-123", "podcast")
    key2 = build_analysis_cache_key("https://example.com/feed.xml", "guid-123", "podcast")
    assert key1 == key2
    assert key1.startswith("podcast:analysis:")


def test_build_analysis_cache_key_changes_with_prompt():
    key1 = build_analysis_cache_key("https://example.com/feed.xml", "guid-123", "podcast")
    key2 = build_analysis_cache_key("https://example.com/feed.xml", "guid-123", "finance")
    assert key1 != key2
