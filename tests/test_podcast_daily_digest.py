import jobs.podcast_scanner as scanner


def test_build_daily_digest_dedupes_stocks_and_sources():
    items = [
        {
            "label": "節目 A",
            "title": "AI 伺服器需求",
            "published": "2026-05-05",
            "stocks": ["NVDA", "2330"],
            "sentiment": "bullish",
            "summary": "資料中心需求仍強。",
        },
        {
            "label": "節目 B",
            "title": "半導體觀察",
            "published": "2026-05-05",
            "stocks": ["NVDA"],
            "sentiment": "neutral",
            "summary": "估值偏高但趨勢延續。",
        },
    ]
    report = scanner.build_daily_investment_digest(items)
    html = scanner.generate_daily_investment_html_report(items)
    caption = scanner.build_daily_investment_digest_caption(items)

    assert "# 每日 Podcast 投資統整" in report
    assert "本次納入：2 則訊號" in report
    assert "- NVDA：節目 A, 節目 B" in report
    assert "- 2330：節目 A" in report
    assert "偏多 1、中性 1、偏空 0" in report
    assert "<title>每日 Podcast 投資統整</title>" in html
    assert "Daily Investment Brief" in html
    assert "市場情緒分布" in html
    assert "焦點標的排行" in html
    assert "逐集投資訊號" in html
    assert "NVDA" in html
    assert "🔎 研究完成：每日 Podcast 投資統整" in caption
    assert "📝 核心結論" in caption


def test_daily_digest_candidate_uses_conclusion_and_strips_citations(monkeypatch):
    monkeypatch.setattr(scanner, "DAILY_DIGEST_LOOKBACK_DAYS", 0)
    analysis = (
        "【文字紀錄】\n"
        "今天看好台積電與輝達。\n\n"
        "【投資倒數小結】\n"
        "1. 台美股焦點標的：台積電：需求強。NVDA：AI 需求強。\n"
        "2. 本集結論：AI 供應鏈偏多 [1]，但短線仍要留意追價風險 [2, 3]。"
    )

    item = scanner._build_daily_digest_candidate(
        {"label": "測試節目"},
        {"title": "今日盤勢", "published": "2026-05-05", "feed_title": "Feed"},
        analysis,
    )

    assert item is not None
    assert item["label"] == "測試節目"
    assert "2330" in item["stocks"]
    assert "NVDA" in item["stocks"]
    assert "[1]" not in item["summary"]
    assert "[2, 3]" not in item["summary"]
    assert "AI 供應鏈偏多" in item["summary"]


def test_send_daily_digest_uses_research_style_report_link(monkeypatch):
    sent = {}

    def fake_send_report_link(chat_id, html_content, caption):
        sent["chat_id"] = chat_id
        sent["html_content"] = html_content
        sent["caption"] = caption
        return True

    monkeypatch.setattr(scanner.Config, "TG_CHAT_ID", "123")
    monkeypatch.setattr(scanner.Notifier, "send_report_link", fake_send_report_link)

    assert scanner.send_daily_investment_digest([
        {
            "label": "節目 A",
            "title": "AI 伺服器需求",
            "published": "2026-05-05",
            "stocks": ["NVDA"],
            "sentiment": "bullish",
            "summary": "資料中心需求仍強。",
        }
    ])

    assert sent["chat_id"] == "123"
    assert "<html" in sent["html_content"]
    assert "焦點標的排行" in sent["html_content"]
    assert sent["caption"].startswith("🔎 研究完成：每日 Podcast 投資統整")
    assert "完整統整請點開" not in sent["caption"]
