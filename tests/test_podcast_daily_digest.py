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
    assert "今天看好台積電與輝達" in item["analysis_text"]


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


def test_send_daily_digest_uses_nlm_multi_source_report_when_available(monkeypatch):
    sent = {}

    def fake_send_report_link(chat_id, html_content, caption):
        sent["html_content"] = html_content
        sent["caption"] = caption
        return True

    monkeypatch.setattr(scanner.Config, "TG_CHAT_ID", "123")
    monkeypatch.setattr(scanner.Notifier, "send_report_link", fake_send_report_link)
    monkeypatch.setattr(scanner, "_should_use_nlm_daily_digest", lambda: True)
    monkeypatch.setattr(
        scanner,
        "synthesize_daily_digest_with_nlm",
        lambda runner, items: "# 每日 Podcast 投資統整\n\n## 執行摘要\n跨來源統整。",
    )

    assert scanner.send_daily_investment_digest([
        {
            "label": "節目 A",
            "title": "AI 伺服器需求",
            "published": "2026-05-05",
            "stocks": ["NVDA"],
            "sentiment": "bullish",
            "summary": "資料中心需求仍強。",
            "analysis_text": "【文字紀錄】完整逐字稿",
        }
    ], runner=object())

    assert "跨來源統整" in sent["html_content"]
    assert "NotebookLM" not in sent["html_content"]
    assert "今日判讀" in sent["html_content"]
    assert "主軸雷達" in sent["html_content"]
    assert "股票特別提及" in sent["html_content"]
    assert "ticker-highlight" in sent["html_content"]
    assert sent["caption"].startswith("🔎 研究完成：每日 Podcast 投資統整")


def test_send_daily_digest_rejects_nlm_process_draft(monkeypatch):
    sent = {}

    def fake_send_report_link(chat_id, html_content, caption):
        sent["html_content"] = html_content
        sent["caption"] = caption
        return True

    monkeypatch.setattr(scanner.Config, "TG_CHAT_ID", "123")
    monkeypatch.setattr(scanner.Notifier, "send_report_link", fake_send_report_link)
    monkeypatch.setattr(scanner, "_should_use_nlm_daily_digest", lambda: True)
    monkeypatch.setattr(
        scanner,
        "synthesize_daily_digest_with_nlm",
        lambda runner, items: None,
    )

    assert scanner.send_daily_investment_digest([
        {
            "label": "節目 A",
            "title": "AI 伺服器需求",
            "published": "2026-05-05",
            "stocks": ["NVDA"],
            "sentiment": "bullish",
            "summary": "資料中心需求仍強。",
            "analysis_text": "【文字紀錄】完整逐字稿",
        }
    ], runner=object())

    assert "Evaluating Investment Opportunities" not in sent["html_content"]
    assert "逐集投資訊號" in sent["html_content"]
    assert "節目 A" in sent["html_content"]


def test_daily_digest_nlm_report_validation_rejects_short_english_draft():
    bad_report = (
        "**Evaluating Investment Opportunities**\n\n"
        "I'm now evaluating investment opportunities, specifically focusing on AMD and INTC, "
        "based on recent market signals."
    )

    assert not scanner._is_valid_daily_digest_report(bad_report)


def test_daily_digest_nlm_report_validation_accepts_required_sections():
    good_report = (
        "# 每日 Podcast 投資統整\n\n"
        "## 執行摘要\n"
        "今日多個來源共同指向 AI 伺服器、半導體供應鏈與雲端資本支出的延續性。"
        "整體訊號偏向結構性需求仍在，但短線估值、財報預期與訂單驗證仍是主要變數。"
        "台股供應鏈受惠於資料中心與先進封裝題材，美股大型科技股則需觀察資本支出是否持續。"
        "記憶體與網通零組件被多個來源提及，顯示市場正在尋找 AI 主線以外的延伸受惠者。"
        "不過，部分公司股價已反映樂觀假設，因此追價風險需要被獨立列入評估。"
        "今天的投資含義不是全面追高，而是把供應鏈能見度、客戶集中度、庫存週期與財測可信度拆開檢查。"
        "若後續來源持續出現同一批標的，代表資金共識正在形成；若只有單一來源提及，則應先視為觀察名單。\n\n"
        "## 市場主軸\n"
        "### AI 供應鏈延續\n"
        "- 共識：資料中心需求仍是主要成長來源。\n"
        "- 分歧：短線估值是否已過度反映。\n"
        "- 投資含義：優先追蹤訂單與毛利率。\n\n"
        "### 記憶體與高速傳輸\n"
        "- 共識：雲端資本支出帶動高頻寬記憶體與光通訊需求。\n"
        "- 分歧：價格循環是否已進入過熱階段。\n"
        "- 投資含義：觀察供給擴張速度與客戶拉貨節奏。\n\n"
        "## 焦點標的\n"
        "| 標的代號/公司名 | 方向 | 提及來源 | 來源日期 | 講者觀點 | 風險 |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| NVDA | 偏多 | 節目 A | 2026-05-05 | AI 需求仍強 | 估值偏高 |\n\n"
        "## 操作觀察\n"
        "- 財報展望：觀察資料中心營收與毛利率是否延續。\n\n"
        "- 訂單驗證：若供應鏈開始同步上修出貨與資本支出，偏多訊號可信度提高。\n"
        "- 估值位置：若利多公布後股價無法續強，需留意短線資金轉向防守。\n\n"
        "## 風險清單\n"
        "- 估值風險：若財測不如預期，可能出現回檔。\n\n"
        "## 來源摘要\n"
        "- 節目 A（2026-05-05）：聚焦 AI 供應鏈需求與估值風險。"
    )

    assert scanner._is_valid_daily_digest_report(good_report)


def test_podcast_prompt_uses_transcript_cache_namespace(monkeypatch):
    monkeypatch.delenv("PODCAST_ANALYSIS_CACHE_KEY", raising=False)
    assert scanner._analysis_cache_key("podcast") == "podcast_transcript_v2"
    assert scanner._analysis_cache_key("finance") == "finance"

    monkeypatch.setenv("PODCAST_ANALYSIS_CACHE_KEY", "podcast_transcript_v3")
    assert scanner._analysis_cache_key("podcast") == "podcast_transcript_v3"


def test_supplement_digest_items_from_db_when_too_few(monkeypatch):
    fresh = [{
        "label": "節目 A",
        "title": "今日盤勢",
        "published": "2026-05-05",
        "stocks": ["2330"],
        "sentiment": "neutral",
        "summary": "新訊號",
    }]
    db_items = [
        fresh[0],
        {
            "label": "節目 B",
            "title": "AI 供應鏈",
            "published": "2026-05-05",
            "stocks": ["NVDA"],
            "sentiment": "bullish",
            "summary": "補充訊號",
        },
    ]

    monkeypatch.setattr(scanner, "DAILY_DIGEST_MIN_ITEMS", 5)
    monkeypatch.setattr(scanner, "load_recent_digest_items_from_db", lambda: db_items)

    merged = scanner.supplement_digest_items_from_db(fresh)

    assert len(merged) == 2
    assert merged[0]["title"] == "今日盤勢"
    assert merged[1]["title"] == "AI 供應鏈"
