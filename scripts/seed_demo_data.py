"""
scripts/seed_demo_data.py

直接向 Neon DB 寫入 15 個 KOL 的示範集數資料（analysis_date = 今日）。
完成後自動執行 compute_and_write_consensus 更新共識指標。

執行：python scripts/seed_demo_data.py
"""
import os
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

DB = "postgresql://neondb_owner:npg_iT2HlX0VZpsA@ep-cold-wind-a1wh74pm-pooler.ap-southeast-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require"
os.environ["DATABASE_URL"] = DB

import psycopg2
import psycopg2.extras

TODAY = date.today()

# ── 15 個 KOL 完整資料 ───────────────────────────────────────────────────────

KOLS = [
    # ── 原有 8 個（更新 rss_url 若有缺）──
    {
        "kol_id": "gooaye",
        "kol_name": "股癌 Podcast",
        "host": "謝孟恭",
        "avatar": "🦀",
        "color": "#3b82f6",
        "rss_url": "https://feeds.soundon.fm/podcasts/954689a5-3096-43a4-a80b-7810b219cef3.xml",
    },
    {
        "kol_id": "yutin",
        "kol_name": "游庭皓的財經皓角",
        "host": "游庭皓",
        "avatar": "📊",
        "color": "#10b981",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000002.xml",
    },
    {
        "kol_id": "macromicro",
        "kol_name": "MacroMicro 財經M平方",
        "host": "Rachel",
        "avatar": "🌐",
        "color": "#8b5cf6",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000003.xml",
    },
    {
        "kol_id": "billkitchen",
        "kol_name": "比爾的財經廚房",
        "host": "楊比爾",
        "avatar": "🍳",
        "color": "#f59e0b",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000004.xml",
    },
    {
        "kol_id": "zhaohualink",
        "kol_name": "兆華與股惑仔",
        "host": "李兆華",
        "avatar": "📈",
        "color": "#ef4444",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000005.xml",
    },
    {
        "kol_id": "caalaw",
        "kol_name": "財報狗",
        "host": "Jeff & Sky",
        "avatar": "🐕",
        "color": "#14b8a6",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000006.xml",
    },
    {
        "kol_id": "shenghong",
        "kol_name": "升鴻投資",
        "host": "升鴻",
        "avatar": "🚀",
        "color": "#06b6d4",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000007.xml",
    },
    {
        "kol_id": "investlab",
        "kol_name": "阿福の台美股研究室",
        "host": "阿福",
        "avatar": "🔬",
        "color": "#6366f1",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000008.xml",
    },
    # ── 新增 7 個 ──
    {
        "kol_id": "morales",
        "kol_name": "呱吉的股市觀察",
        "host": "邱威傑（呱吉）",
        "avatar": "🐸",
        "color": "#22c55e",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000009.xml",
    },
    {
        "kol_id": "activeinv",
        "kol_name": "主動式投資人",
        "host": "James Ko",
        "avatar": "⚡",
        "color": "#f97316",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000010.xml",
    },
    {
        "kol_id": "engstock",
        "kol_name": "工程師投資記",
        "host": "陳峻誌",
        "avatar": "💻",
        "color": "#a78bfa",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000011.xml",
    },
    {
        "kol_id": "twsenior",
        "kol_name": "台股老司機",
        "host": "老司機",
        "avatar": "🚗",
        "color": "#fb7185",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000012.xml",
    },
    {
        "kol_id": "richie",
        "kol_name": "富朋友理財筆記",
        "host": "Richie",
        "avatar": "💰",
        "color": "#fbbf24",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000013.xml",
    },
    {
        "kol_id": "stockfeel",
        "kol_name": "股感知識庫",
        "host": "股感團隊",
        "avatar": "📚",
        "color": "#34d399",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000014.xml",
    },
    {
        "kol_id": "afterwork",
        "kol_name": "下班後的投資啟蒙",
        "host": "Brian",
        "avatar": "🌙",
        "color": "#818cf8",
        "rss_url": "https://feeds.soundon.fm/podcasts/e0e0e0e0-0000-0000-0000-000000000015.xml",
    },
]

EPISODES = [
    {
        "kol_id": "gooaye",
        "guid": f"gooaye-{TODAY}-demo",
        "title": f"EP660｜費半連漲 18 天後的高乖離修正，多頭格局未變但需要休息",
        "published": TODAY.isoformat(),
        "summary": (
            "那斯達克和標普 500 雙雙創歷史新高，費半單週漲幅超過 10%，連續 18 個交易日全面收紅，"
            "但謝孟恭認為高乖離之下短線修正壓力大，NVDA 在 900 美元附近面臨獲利了結賣壓。"
            "台積電（2330）受惠 AI 伺服器需求維持多頭，聯發科（2454）靠 AI 手機概念估值重估。"
            "建議策略：不追高，等費半回測 10 日線附近再分批承接，NVDA 支撐在 830-850 美元區間。"
            "風險警示：若美伊談判破裂、油價大漲，可能引發通膨預期回升，Fed 鷹派言論壓制估值。"
        ),
        "sentiment": "bullish",
        "stocks": ["NVDA", "2330", "2454", "META", "TSLA"],
    },
    {
        "kol_id": "yutin",
        "guid": f"yutin-{TODAY}-demo",
        "title": f"2026/4/27 硬體股漲太快，軟體股補漲機會浮現",
        "published": TODAY.isoformat(),
        "summary": (
            "游庭皓分析費半狂飆後的資金輪動，認為軟體股如微軟（MSFT）、Salesforce 估值相對低估，"
            "有補漲空間。台股部分，廣達（2382）AI 伺服器出貨動能強勁，法人持續加碼。"
            "聯電（2303）因先進製程轉型進度落後台積電，短線相對弱勢，建議觀望。"
            "本集核心觀點：多頭格局下的輪動才是賺錢機會，不要只盯著費半追高。"
            "操作策略：現金部位 20% 留著等費半回測，其餘持股以台積電、廣達、MSFT 為核心。"
        ),
        "sentiment": "bullish",
        "stocks": ["2382", "2330", "MSFT", "2303", "AMD"],
    },
    {
        "kol_id": "macromicro",
        "guid": f"macromicro-{TODAY}-demo",
        "title": "總體經濟信號：美伊關係與油價是最大變數",
        "published": TODAY.isoformat(),
        "summary": (
            "Rachel 從總經角度分析，美國就業市場依然強勁，PMI 數據顯示製造業回暖，支撐股市上行。"
            "但美伊談判破局風險上升，油價若突破 90 美元，CPI 二次通膨機率大增，Fed 降息預期將延後。"
            "台積電（2330）ADR 溢價持續收窄，外資買超動能放緩，需留意法人籌碼。"
            "本集結論：美股短線偏多，但需密切監控油價走勢，建議配置部分防禦性資產如黃金 ETF。"
        ),
        "sentiment": "neutral",
        "stocks": ["2330", "GOOGL", "AMZN", "AAPL"],
    },
    {
        "kol_id": "billkitchen",
        "guid": f"billkitchen-{TODAY}-demo",
        "title": "比爾廚房週報｜科技財報季來臨，Meta 與亞馬遜是觀察重點",
        "published": TODAY.isoformat(),
        "summary": (
            "楊比爾聚焦美股財報季，Meta（META）廣告收入超預期，AI 驅動的 Advantage+ 廣告工具效益顯著，"
            "Ray-Ban 智慧眼鏡銷售超乎預期，Zuckerberg 對 2026 年 AI 投資持樂觀態度。"
            "亞馬遜（AMZN）AWS 雲端業務加速成長，Q1 毛利率創新高，配合自動化倉儲降低物流成本。"
            "微軟（MSFT）Copilot 企業滲透率加速，Azure 成長率回升至 31%，是本季最穩定的配置。"
            "本集建議：科技財報季持有 META、AMZN、MSFT 核心倉位，等財報後視情況調整比重。"
        ),
        "sentiment": "bullish",
        "stocks": ["META", "AMZN", "MSFT", "GOOGL", "AAPL"],
    },
    {
        "kol_id": "zhaohualink",
        "guid": f"zhaohualink-{TODAY}-demo",
        "title": "兆華股惑仔｜台股籌碼面：外資回補 + 融資未過熱，結構健康",
        "published": TODAY.isoformat(),
        "summary": (
            "李兆華從籌碼面分析台股現況，外資近 5 日淨買超，以半導體族群為主力。"
            "融資使用率仍低於警戒線，散戶並未過度追高，籌碼結構相對健康。"
            "聯發科（2454）法人預估 Q2 EPS 有上修空間，AI 手機出貨量超預期是主要驅動力。"
            "大立光（3008）iPhone 17 Pro 鏡頭規格升級，帶動 ASP 提升，下半年旺季期待值高。"
            "短線壓力：台幣升值壓縮出口廠商獲利，需關注匯率對鴻海（2317）的影響。"
        ),
        "sentiment": "bullish",
        "stocks": ["2454", "3008", "2317", "2330", "2382"],
    },
    {
        "kol_id": "caalaw",
        "guid": f"caalaw-{TODAY}-demo",
        "title": "財報狗分析｜從 ROE 與自由現金流篩選長期持有標的",
        "published": TODAY.isoformat(),
        "summary": (
            "Jeff 用財報狗工具篩選 ROE 連續 5 年超過 20%、自由現金流穩定成長的標的，"
            "台積電（2330）以壓倒性優勢名列榜首，獲利能力與護城河均屬業界頂尖。"
            "美股方面，Apple（AAPL）近三年股息成長率 4.5%，加上 1000 億美元回購計畫，"
            "對長期投資人具吸引力。Google（GOOGL）廣告業務觸底反彈，雲端 GCP 份額持續擴大。"
            "本集結論：用基本面邏輯選股，台積電與 Apple 是長期持有首選，不需要追逐短線熱點。"
        ),
        "sentiment": "bullish",
        "stocks": ["2330", "AAPL", "GOOGL", "MSFT", "2454"],
    },
    {
        "kol_id": "shenghong",
        "guid": f"shenghong-{TODAY}-demo",
        "title": "升鴻投資觀點｜AI 伺服器供應鏈：廣達、緯創誰先突破？",
        "published": TODAY.isoformat(),
        "summary": (
            "升鴻分析 AI 伺服器供應鏈競爭格局，廣達（2382）取得 NVDA GB200 大單，"
            "法人預估 2026 年 AI 伺服器營收佔比將超過 50%，估值仍有上修空間。"
            "緯創（3231）轉型進度略落後廣達，但拿到 AMD MI400 訂單，是第二梯隊首選。"
            "技嘉（2376）在 AI 工作站市場表現搶眼，毛利率結構改善是亮點。"
            "本集建議：AI 伺服器主軸選廣達，保守型可選台積電，避開純代工廠如鴻海。"
        ),
        "sentiment": "bullish",
        "stocks": ["2382", "3231", "2376", "NVDA", "AMD"],
    },
    {
        "kol_id": "investlab",
        "guid": f"investlab-{TODAY}-demo",
        "title": "阿福研究室｜台美股雙邊配置：美股核心 + 台股衛星策略",
        "published": TODAY.isoformat(),
        "summary": (
            "阿福分享個人持倉策略：美股核心倉位以 VTI、QQQ 指數化配置為主，佔整體 60%；"
            "台股衛星倉位選擇台積電（2330）與聯發科（2454）兩檔個股，佔 30%；"
            "剩餘 10% 保留現金等待修正機會。NVDA 已實現部分獲利，等回測 850 美元再補。"
            "AMD 在資料中心 GPU 市占率持續提升，MI400 競爭力值得觀察，可小倉試單。"
            "本集結論：不要過度集中在單一標的，分散配置才能安心長期持有，避免情緒操作。"
        ),
        "sentiment": "bullish",
        "stocks": ["2330", "2454", "NVDA", "AMD", "MSFT"],
    },
    {
        "kol_id": "morales",
        "guid": f"morales-{TODAY}-demo",
        "title": "呱吉股市觀察｜政治風險 × 市場：美伊局勢對科技股的影響",
        "published": TODAY.isoformat(),
        "summary": (
            "呱吉從政治分析角度切入，美伊談判若破局，中東局勢升溫將推升油價，"
            "通膨預期上升對高本益比科技股估值構成壓力，尤其是獲利尚未完全兌現的 AI 概念股。"
            "但他認為美股長期多頭格局不變，短線回撤反而是分批佈局的機會。"
            "Tesla（TSLA）近期因 Musk 政治話題不斷受到賣壓，基本面與品牌形象分歧擴大。"
            "建議：政治因素造成的波動是雜訊，聚焦科技巨頭的基本面，不要被短線消息左右。"
        ),
        "sentiment": "neutral",
        "stocks": ["TSLA", "NVDA", "META", "AAPL", "GOOGL"],
    },
    {
        "kol_id": "activeinv",
        "guid": f"activeinv-{TODAY}-demo",
        "title": "主動式投資人｜用動能策略找強勢股：費半 ETF vs 個股比較",
        "published": TODAY.isoformat(),
        "summary": (
            "James Ko 介紹動能策略選股邏輯，費半（SOXX）整體表現優於大盤，"
            "但個別標的分化明顯：NVDA、Broadcom（AVGO）超強，Intel（INTC）一枝獨秀創高。"
            "台股半導體方面，台積電（2330）仍是最強動能標的，其次是廣達（2382）。"
            "用 12 個月動能回測台股過去 10 年，選強勢股策略年化報酬比大盤高出 8-12 個百分點。"
            "本集結論：量化動能策略在台美股均有效，搭配基本面過濾可進一步提升勝率。"
        ),
        "sentiment": "bullish",
        "stocks": ["NVDA", "AVGO", "INTC", "2330", "2382"],
    },
    {
        "kol_id": "engstock",
        "guid": f"engstock-{TODAY}-demo",
        "title": "工程師投資記｜從 AWS / Azure / GCP 財報看雲端競爭格局",
        "published": TODAY.isoformat(),
        "summary": (
            "陳峻誌用工程師視角解讀三大雲端平台財報，Azure 成長率重回 31% 領跑市場，"
            "Copilot AI 工具滲透率提升帶動企業客戶升級計畫，微軟（MSFT）雲端護城河最寬。"
            "AWS 依然是獲利貢獻最大的事業部，Q1 利潤率創新高，亞馬遜（AMZN）整體估值仍具吸引力。"
            "GCP 成長最快，Google（GOOGL）AI 整合搜尋廣告初步驗證，但市占率追趕需要時間。"
            "本集建議：雲端三強各有優勢，用定期定額分散持有 MSFT、AMZN、GOOGL 為長期最優策略。"
        ),
        "sentiment": "bullish",
        "stocks": ["MSFT", "AMZN", "GOOGL", "META", "AMD"],
    },
    {
        "kol_id": "twsenior",
        "guid": f"twsenior-{TODAY}-demo",
        "title": "台股老司機｜週線收紅守月線，下週關注 21800 點能否站穩",
        "published": TODAY.isoformat(),
        "summary": (
            "老司機用技術分析框架看台股，週線連續三週收紅，月線支撐良好，多頭格局維持。"
            "21800 點是近期整理區間上緣，若放量突破有望挑戰 22500 點前高。"
            "半導體族群技術面最強，台積電（2330）MACD 翻紅，KD 在高檔整理未死叉。"
            "金融股富邦金（2881）受惠升息末段利差擴大，技術面剛突破年線壓力。"
            "操作策略：強勢股台積電、廣達跌深買，弱勢股避免逆勢操作，資金向強者集中。"
        ),
        "sentiment": "bullish",
        "stocks": ["2330", "2881", "2382", "2454", "2317"],
    },
    {
        "kol_id": "richie",
        "guid": f"richie-{TODAY}-demo",
        "title": "富朋友理財筆記｜小資族美股投資入門：從 0 開始的指數化配置",
        "published": TODAY.isoformat(),
        "summary": (
            "Richie 為投資新手設計美股入門路線，推薦從 VTI 全市場 ETF 開始，"
            "每月定期定額不擇時，歷史回測年化 10% 是最安心的長期方法。"
            "科技巨頭如蘋果（AAPL）、微軟（MSFT）是 VTI 最大成分股，持有 ETF 即間接持有。"
            "台灣投資人買美股 ETF 需注意遺產稅問題，建議透過台灣掛牌的美股 ETF 規避。"
            "本集結論：小資族不需要選股，定期定額 VTI 加上時間複利，財富自然成長。"
        ),
        "sentiment": "neutral",
        "stocks": ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"],
    },
    {
        "kol_id": "stockfeel",
        "guid": f"stockfeel-{TODAY}-demo",
        "title": "股感知識庫｜AI 時代的半導體護城河：誰在賺真正的錢？",
        "published": TODAY.isoformat(),
        "summary": (
            "股感團隊深度分析 AI 算力供應鏈利潤分配，NVIDIA（NVDA）GPU 毛利率高達 74%，"
            "是整條鏈最賺錢的環節；台積電（2330）先進製程毛利率 53%，同樣優秀。"
            "下游組裝廠廣達（2382）毛利率僅 5-6%，但出貨量成長帶動營收爆發，股價大漲。"
            "HBM 記憶體是 AI 伺服器的瓶頸，美光（MU）受惠 HBM3E 出貨量倍增，值得關注。"
            "本集結論：AI 供應鏈投資要選護城河高的環節（NVDA、台積電），勿追逐毛利薄的組裝廠。"
        ),
        "sentiment": "bullish",
        "stocks": ["NVDA", "2330", "2382", "MU", "AVGO"],
    },
    {
        "kol_id": "afterwork",
        "guid": f"afterwork-{TODAY}-demo",
        "title": "下班後的投資啟蒙｜為什麼大多數人投資賠錢？心理偏誤的陷阱",
        "published": TODAY.isoformat(),
        "summary": (
            "Brian 從行為財務學角度分析投資失敗的心理原因：過度自信導致頻繁交易、"
            "損失厭惡讓人死抱賠錢股票、從眾心理在高點追熱門股。"
            "解決方案：建立投資系統（定期定額、紀律停損）取代情緒決策，"
            "長期持有指數基金讓複利發揮效果，勝過 90% 的主動選股者。"
            "NVDA 這類強勢股，大多數人因害怕高點而不敢買，卻在修正時恐慌殺出，錯誤決策兩次。"
            "本集建議：先修練心理素質再談選股，紀律和耐心才是散戶最大的競爭優勢。"
        ),
        "sentiment": "neutral",
        "stocks": ["NVDA", "AAPL", "2330", "MSFT"],
    },
]


def seed():
    conn = psycopg2.connect(DB)

    with conn:
        with conn.cursor() as cur:
            # ── 1. Upsert KOLs ───────────────────────────────────────────
            print("Step 1: Upsert KOLs...")
            for k in KOLS:
                cur.execute(
                    """
                    INSERT INTO kols (kol_id, kol_name, host, avatar, color, rss_url)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (kol_id) DO UPDATE SET
                      kol_name = EXCLUDED.kol_name,
                      host     = EXCLUDED.host,
                      avatar   = EXCLUDED.avatar,
                      color    = EXCLUDED.color
                    """,
                    (k["kol_id"], k["kol_name"], k["host"],
                     k["avatar"], k["color"], k["rss_url"]),
                )
            print(f"  [OK] {len(KOLS)} KOLs upserted")

            # ── 2. Insert Episodes ───────────────────────────────────────
            print("Step 2: Insert episodes...")
            for ep in EPISODES:
                cur.execute(
                    """
                    INSERT INTO episodes
                      (kol_id, guid, title, published, summary, sentiment,
                       stocks_mentioned, report_url, analysis_date)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (kol_id, guid) DO UPDATE SET
                      summary          = EXCLUDED.summary,
                      sentiment        = EXCLUDED.sentiment,
                      stocks_mentioned = EXCLUDED.stocks_mentioned,
                      analyzed_at      = NOW()
                    """,
                    (
                        ep["kol_id"], ep["guid"], ep["title"],
                        ep["published"], ep["summary"], ep["sentiment"],
                        ep["stocks"], "", TODAY,
                    ),
                )
            print(f"  [OK] {len(EPISODES)} episodes inserted for {TODAY}")

    conn.close()

    # ── 3. Compute consensus ─────────────────────────────────────────────
    print("Step 3: Computing consensus...")
    from app.db_writer import compute_and_write_consensus
    ok = compute_and_write_consensus(analysis_date=TODAY)
    print(f"  [{'OK' if ok else 'FAIL'}] consensus_daily + stock_mentions updated")

    print()
    print(f"Done! {len(KOLS)} KOLs, {len(EPISODES)} episodes, date={TODAY}")
    print("Vercel ISR will pick up the new data within 5 minutes.")


if __name__ == "__main__":
    seed()
