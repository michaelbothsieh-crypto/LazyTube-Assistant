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
            "【文字紀錄】\n"
            "謝孟恭：好，我們今天來聊費半這個東西。連漲 18 天，你說這合理嗎？不合理，但市場就是這樣。"
            "那斯達克跟標普都創新高，費半單週漲超過 10%，這個乖離已經很誇張了。"
            "我自己是不敢在這個位置追的，NVDA 在 900 附近，我覺得獲利了結賣壓會很重。"
            "台積電方面，AI 伺服器需求還是很強，多頭格局我沒有改變看法，但短線就是需要喘口氣。"
            "聯發科靠 AI 手機這個題材，估值一直在重估，但我會等修正再進。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "NVDA：900 美元附近獲利了結賣壓重，支撐在 830-850 美元，等回測再承接\n"
            "2330：AI 伺服器需求強勁，多頭格局不變，跌深才是買點\n"
            "2454：AI 手機題材估值重估，等費半修正完畢後補漲機會佳\n"
            "META：廣告業務穩健，AI 投資持續落地，持有不動\n"
            "TSLA：Musk 政治話題不斷，品牌與基本面分歧擴大，暫時觀望\n\n"
            "2. 本集結論：\n"
            "費半高乖離修正壓力真實存在，短線建議不要追高，等回測 10 日線附近再分批承接。"
            "多頭格局未變，但市場需要休息，美伊談判若破局是最大的尾部風險，需持續觀察油價動向。"
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
            "【文字紀錄】\n"
            "游庭皓：費半這波漲太猛，大家都在追硬體，但我想說，輪動的機會已經出現了。"
            "微軟、Salesforce 這類軟體股，估值比起硬體相對低估，有補漲空間。"
            "台股的廣達，AI 伺服器出貨動能超強，法人一直在加碼，這個趨勢我很看好。"
            "聯電的話，先進製程轉型速度落後台積電太多，短線我不會碰，建議先觀望。"
            "整體策略就是：多頭格局下的輪動才是賺錢的機會，不要只盯著費半追高。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "2382：廣達 AI 伺服器出貨強勁，法人持續加碼，估值仍有上修空間\n"
            "2330：台積電核心持股不動，多頭旗手地位穩固\n"
            "MSFT：軟體股估值低估，Azure 成長回升，補漲空間佳\n"
            "2303：聯電先進製程進度落後，短線相對弱勢，建議觀望\n"
            "AMD：資料中心 GPU 份額持續提升，MI400 值得追蹤\n\n"
            "2. 本集結論：\n"
            "硬體股漲太快、乖離過大，資金正在悄悄輪動到軟體股，MSFT 是首要受益標的。"
            "現金部位建議保留 20% 等費半回測，其餘持股以台積電、廣達、MSFT 為核心，不要過度換股。"
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
            "【文字紀錄】\n"
            "Rachel：從數據面來看，美國就業市場依然強勁，PMI 製造業數字也在回暖，這些都是支撐股市的正面因子。"
            "但我現在最擔心的是美伊談判的走向，一旦破局，中東緊張局勢升溫，油價很可能直接突破 90 美元。"
            "油價一漲，CPI 二次通膨的機率就大增，Fed 降息預期就要往後推，對高估值股票的壓力很大。"
            "台積電 ADR 的溢價最近在收窄，外資買超動能也明顯放緩，法人籌碼這塊要特別留意。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "2330：外資買超放緩、ADR 溢價收窄，短線法人籌碼需觀察，不宜追高\n"
            "GOOGL：廣告業務穩健，雲端 GCP 份額擴大，但油價風險若升溫會受估值壓制\n"
            "AMZN：AWS 獲利強勁，估值相對合理，是中性環境下較穩健的選擇\n"
            "AAPL：消費性電子受通膨影響有限，但若 Fed 轉鷹，高本益比仍有壓力\n\n"
            "2. 本集結論：\n"
            "美股短線偏多，但最大風險來自油價——若美伊談判破局導致油價衝破 90 美元，通膨預期升溫將迫使 Fed 延後降息，高估值科技股首當其衝。"
            "建議在核心持股不動的前提下，配置部分防禦性資產如黃金 ETF，對沖地緣政治尾部風險。"
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
            "【文字紀錄】\n"
            "楊比爾：財報季來了，這次我最關注的是 Meta 跟亞馬遜。Meta 廣告收入已經超預期，"
            "Advantage+ 這個 AI 廣告工具效益真的很顯著，Ray-Ban 智慧眼鏡也賣得出乎意料的好。"
            "Zuckerberg 對 2026 年的 AI 投資很樂觀，我覺得這個方向是對的。"
            "亞馬遜的 AWS 雲端業務加速，Q1 毛利率創新高，自動化倉儲降低了物流成本，整體很健康。"
            "微軟的 Copilot 企業滲透率在加速，Azure 成長率回升到 31%，是本季最穩定的配置。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "META：廣告超預期、AI 工具效益顯著、Ray-Ban 銷售強，財報後看好繼續走高\n"
            "AMZN：AWS 毛利率創新高，自動化降本有效，估值仍有上修空間\n"
            "MSFT：Azure 31% 成長、Copilot 滲透率加速，是本季最穩定的核心持倉\n"
            "GOOGL：廣告穩健、GCP 份額擴大，但 AI 搜尋轉型仍需時間驗證\n"
            "AAPL：iPhone 17 超級週期預期，下半年催化劑，財報季前可先觀察\n\n"
            "2. 本集結論：\n"
            "科技財報季整體優於預期，META、AMZN、MSFT 三強鼎立格局確立，建議維持核心倉位不動。"
            "待財報公布後視本益比變化調整比重，資金不足者可優先選 MSFT 作為最穩健的單一標的。"
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
            "【文字紀錄】\n"
            "李兆華：我今天主要從籌碼面來看台股，外資近 5 日淨買超，主力集中在半導體族群。"
            "融資使用率還在警戒線以下，散戶沒有過度追高，這個結構我覺得相對健康。"
            "聯發科這邊，法人預估 Q2 EPS 有上修空間，AI 手機出貨量超預期是主要驅動力，我看好。"
            "大立光受惠 iPhone 17 Pro 鏡頭規格升級，ASP 提升，下半年旺季期待值高。"
            "唯一要注意的是台幣升值，這會壓縮出口廠商獲利，鴻海這種匯率敏感型的要小心。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "2454：聯發科法人持續加碼，Q2 EPS 上修機率高，AI 手機題材強勁，看多\n"
            "3008：大立光 iPhone 17 Pro 鏡頭升級受惠，ASP 提升，下半年旺季可期\n"
            "2317：鴻海匯率敏感，台幣升值壓縮獲利，短線謹慎，等匯率穩定再進場\n"
            "2330：外資買超主力，籌碼乾淨，多頭格局持續\n"
            "2382：廣達法人加碼中，AI 伺服器出貨持續放量\n\n"
            "2. 本集結論：\n"
            "台股籌碼結構健康，外資回補 + 融資未過熱是難得的健康格局，不必過度悲觀。"
            "半導體族群是資金主戰場，聯發科與大立光是下半年兩個重要催化劑，台幣匯率是唯一需要監控的系統性風險。"
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
            "【文字紀錄】\n"
            "Jeff：今天我用財報狗工具，篩選 ROE 連續 5 年超過 20%、自由現金流穩定成長的標的。"
            "台積電毫無懸念是榜首，獲利能力跟護城河都是業界頂尖，這沒什麼好說的。"
            "美股方面 Apple 近三年股息成長率 4.5%，還有 1000 億美元的回購計畫，長期投資人的好朋友。"
            "Google 廣告業務觸底反彈，GCP 雲端份額持續擴大，基本面在修復中。"
            "我的結論就是，用基本面邏輯選股，不需要追短線熱點，長期持有才是正道。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "2330：ROE 與自由現金流業界頂尖，長期持有首選，跌就買\n"
            "AAPL：股息穩定成長 4.5%、千億回購護航，長線配置必備\n"
            "GOOGL：廣告觸底反彈、GCP 份額擴大，基本面修復中，中長線看好\n"
            "MSFT：自由現金流強勁，Copilot 商業化持續推進，估值合理\n"
            "2454：聯發科 ROE 穩定，AI 手機題材帶動估值重估，長期可持有\n\n"
            "2. 本集結論：\n"
            "用基本面邏輯選股，台積電與 Apple 是長期持有的最優解，不需要每天看盤追短線熱點。"
            "ROE 穩定超過 20% + 自由現金流持續成長的標的，時間是最好的朋友，持有即可。"
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
            "【文字紀錄】\n"
            "升鴻：今天來分析 AI 伺服器供應鏈，廣達跟緯創誰先突破這個問題。"
            "廣達拿到 NVDA GB200 大單，法人預估 2026 年 AI 伺服器營收佔比超過 50%，估值還有空間。"
            "緯創轉型進度落後廣達，但拿到 AMD MI400 訂單，算是第二梯隊的首選。"
            "技嘉在 AI 工作站市場表現搶眼，毛利率結構改善是最大亮點，這個我覺得市場還沒完全 price in。"
            "我的建議是，AI 伺服器主軸就選廣達，保守型投資人可以選台積電，純代工廠如鴻海就先避開。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "2382：廣達拿下 GB200 大單，AI 伺服器佔比 2026 年超 50%，估值仍有上修空間，主力標的\n"
            "3231：緯創拿到 AMD MI400 訂單，第二梯隊首選，保守型可小倉配置\n"
            "2376：技嘉 AI 工作站市占提升，毛利率結構改善，市場尚未完全 price in\n"
            "NVDA：GB200 出貨加速，供應鏈受惠廣，上游最強護城河\n"
            "AMD：MI400 競爭力提升，伺服器 GPU 市占持續蠶食，中長線看好\n\n"
            "2. 本集結論：\n"
            "AI 伺服器供應鏈主軸選廣達，這是最確定性的選擇；想分散配置的可以加緯創作為第二梯隊。"
            "技嘉是本集的隱藏亮點，毛利率改善若持續，估值有望大幅重估，值得追蹤。"
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
            "【文字紀錄】\n"
            "阿福：今天分享我自己的持倉策略，我用的是核心衛星的概念。"
            "美股核心倉位用 VTI、QQQ 指數化配置，佔整體大約 60%，這塊不動。"
            "台股衛星倉位就選台積電跟聯發科兩檔個股，佔 30%，其餘 10% 留現金等修正。"
            "NVDA 我已經部分獲利出場，等回測 850 美元再補回來。"
            "AMD 在資料中心 GPU 市占一直在提升，MI400 競爭力值得觀察，我有小倉試單。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "2330：台股衛星倉位核心，多頭格局不變，長期持有\n"
            "2454：聯發科 AI 手機受惠，衛星倉位第二標的，中長線看好\n"
            "NVDA：已部分獲利，等回測 850 美元再補，不追高\n"
            "AMD：小倉試單，MI400 資料中心競爭力值得追蹤\n"
            "MSFT：VTI/QQQ 最大成分股之一，指數化配置已間接持有\n\n"
            "2. 本集結論：\n"
            "不要過度集中在單一標的，核心衛星配置讓你在多頭中安心持有、在修正中不慌張。"
            "NVDA 等回測再補、現金部位等機會，紀律執行才是長期超越市場的關鍵。"
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
            "【文字紀錄】\n"
            "呱吉：我從政治分析角度看這件事，美伊談判如果破局，中東局勢升溫，油價就衝。"
            "油價衝，通膨預期上升，高本益比的科技股估值就有壓力，這個邏輯很直接。"
            "但我不是在喊空，我的意思是，政治因素造成的波動是雜訊，長期多頭格局我沒有改變看法。"
            "Tesla 最近就是個活教材，Musk 的政治話題讓基本面跟品牌形象分歧越來越大，賣壓持續。"
            "我的建議是，聚焦科技巨頭的基本面，不要被短線消息左右，回撤才是佈局機會。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "TSLA：Musk 政治話題持續帶來賣壓，品牌與基本面分歧擴大，暫時觀望\n"
            "NVDA：地緣政治風險若升溫短線承壓，但 AI 算力需求長期確定，回撤是機會\n"
            "META：廣告業務穩健，政治干擾相對有限，持有不動\n"
            "AAPL：消費性電子受地緣政治影響有限，防禦性佳\n"
            "GOOGL：廣告回暖，GCP 成長，政治風險影響有限，可持有\n\n"
            "2. 本集結論：\n"
            "政治因素造成的市場波動本質上是雜訊，長期多頭格局不因地緣政治而改變。"
            "Tesla 是當前最大的不確定性，Musk 的政治身份讓基本面分析失效，其餘科技巨頭回撤即佈局。"
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
            "【文字紀錄】\n"
            "James Ko：今天介紹動能策略，概念很簡單：強者恆強。費半整體表現優於大盤，"
            "但個別標的分化很明顯，NVDA、Broadcom 超強，Intel 創新高是意外驚喜。"
            "台股半導體方面，台積電動能最強，廣達次之，其他的就不要追了。"
            "我做了一個回測，用 12 個月動能策略跑台股過去 10 年，年化報酬比大盤高出 8-12 個百分點。"
            "量化動能策略搭配基本面過濾，在台美股都有效，這是我目前最主要的選股框架。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "NVDA：動能最強標的，12 個月動能指標領先費半，持有不動\n"
            "AVGO：Broadcom AI 晶片佈局完整，動能指標第二強，可持有\n"
            "INTC：Intel 創新高是意外，但動能轉強值得追蹤，小倉試探\n"
            "2330：台股動能最強標的，動能策略首選，持有\n"
            "2382：廣達動能指標走強，AI 伺服器出貨量支撐，可持有\n\n"
            "2. 本集結論：\n"
            "動能策略在台美股均有實證有效，12 個月動能選強勢股年化超額報酬 8-12 個百分點。"
            "NVDA 和台積電是當前最強動能標的，配合基本面驗證後持有，不要因為「漲太多」就出場。"
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
            "【文字紀錄】\n"
            "陳峻誌：我用工程師的視角來看三大雲端平台的財報，這個角度跟一般分析師不太一樣。"
            "Azure 成長率重回 31%，Copilot AI 工具的企業滲透率在提升，帶動升級計畫，護城河最寬。"
            "AWS 還是獲利貢獻最大的事業部，Q1 利潤率創新高，自動化倉儲把物流成本降下來了，整體很健康。"
            "GCP 成長最快，但市占率追 Azure 和 AWS 還需要時間，Google AI 整合搜尋廣告初步驗證了。"
            "我的結論是，雲端三強各有優勢，定期定額分散持有是最優策略。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "MSFT：Azure 31% 成長、Copilot 滲透率加速，雲端護城河最寬，長期首選\n"
            "AMZN：AWS 利潤率創新高，自動化降本有效，整體估值仍有吸引力\n"
            "GOOGL：GCP 成長最快，AI 搜尋廣告初步驗證，但市占率追趕需時間，中長線看好\n"
            "META：廣告技術棧雲端化受惠，AI 算力需求帶動雲端採購成長\n"
            "AMD：雲端業者 GPU 採購分散化趨勢，AMD MI400 受惠，中長線值得持有\n\n"
            "2. 本集結論：\n"
            "雲端三強格局穩固，Azure 護城河最深、AWS 獲利最豐、GCP 成長最快，三者各有不同投資邏輯。"
            "定期定額分散持有 MSFT、AMZN、GOOGL 是長期最優策略，不需要押注單一雲端平台。"
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
            "【文字紀錄】\n"
            "老司機：週線連三紅，月線支撐守得很好，多頭格局這塊我沒有疑慮。"
            "21800 點是近期整理區間的上緣，若能放量突破，下一個目標就是 22500 前高。"
            "台積電技術面最強，MACD 翻紅，KD 在高檔整理沒有死叉，這個型態很健康。"
            "富邦金這邊，受惠升息末段利差擴大，技術面剛突破年線壓力，這個我覺得可以關注。"
            "操作策略很簡單：強勢股跌深才買，弱勢股不要逆勢操作，資金向強者集中就對了。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "2330：MACD 翻紅、KD 高檔未死叉，技術面最強，跌深承接\n"
            "2881：富邦金突破年線壓力，升息末段利差受惠，可小倉試探\n"
            "2382：廣達跌深買點出現，AI 伺服器動能支撐，不宜追高但回測可買\n"
            "2454：聯發科技術面整理中，等突破 21800 確認後再跟進\n"
            "2317：鴻海匯率敏感，技術面相對弱勢，暫時迴避\n\n"
            "2. 本集結論：\n"
            "台股週線三連紅、月線守穩，多頭格局不變，21800 突破是下週最重要的技術訊號。"
            "操作策略聚焦在強勢股台積電、廣達，弱勢股不要逆勢，資金向強者集中是多頭市場的最佳策略。"
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
            "【文字紀錄】\n"
            "Richie：今天我想跟小資族聊聊，其實你不需要會選股。"
            "從 VTI 全市場 ETF 開始，每月定期定額，不擇時，歷史回測年化 10% 是最安心的長期方法。"
            "蘋果、微軟這些科技巨頭本來就是 VTI 最大成分股，你持有 ETF 就等於間接持有了。"
            "台灣投資人要注意遺產稅問題，建議透過台灣掛牌的美股 ETF 來規避，這個很重要。"
            "結論就是，小資族不需要選股，定期定額加上時間複利，財富自然成長。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "AAPL：VTI 最大成分股之一，持有指數即間接配置，長期穩健\n"
            "MSFT：VTI 第二大成分股，Copilot 商業化持續，指數化配置已含蓋\n"
            "GOOGL：GCP 與廣告雙引擎，VTI/QQQ 均有配置，不需單獨買\n"
            "AMZN：AWS 獲利強勁，指數配置已含蓋，不需要追單一股\n"
            "NVDA：費半龍頭，若想單獨加倉等回測 850 再進，否則 ETF 配置即可\n\n"
            "2. 本集結論：\n"
            "小資族最佳策略是定期定額 VTI，不擇時、不選股，時間複利是最強的護城河。"
            "若想增加科技曝險可搭配 QQQ，台灣投資人務必注意美股 ETF 遺產稅問題，優先選台掛美股 ETF。"
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
            "【文字紀錄】\n"
            "股感團隊：我們今天分析 AI 算力供應鏈的利潤分配，這個視角很重要。"
            "NVIDIA 的 GPU 毛利率 74%，是整條鏈最賺錢的環節，護城河無與倫比。"
            "台積電先進製程毛利率 53%，同樣很優秀，這兩個是 AI 時代最核心的受益者。"
            "廣達毛利率只有 5-6%，但出貨量成長帶動營收爆發，股價大漲，但這種商業模式的韌性較弱。"
            "HBM 記憶體是 AI 伺服器的瓶頸，美光受惠 HBM3E 出貨量倍增，這個值得追蹤。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "NVDA：GPU 毛利率 74%，AI 算力護城河最深，長期首選，不要因漲多就賣\n"
            "2330：台積電先進製程毛利率 53%，是整條鏈最確定的受益者，核心持股\n"
            "2382：廣達毛利率僅 5-6%，雖然出貨量大但護城河薄，勿以高估值長期持有\n"
            "MU：美光 HBM3E 出貨量倍增，AI 記憶體瓶頸受惠，中長線值得配置\n"
            "AVGO：Broadcom AI ASIC 晶片佈局，毛利率高、護城河深，與 NVDA 並列首選\n\n"
            "2. 本集結論：\n"
            "AI 供應鏈投資要選護城河高的環節：NVDA 和台積電是最頂層的受益者，毛利率遠超下游。"
            "廣達等組裝廠雖然股價大漲，但毛利率薄、護城河弱，不適合以高估值長期持有，美光 HBM 是本集最值得追蹤的黑馬。"
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
            "【文字紀錄】\n"
            "Brian：大多數人投資賠錢，原因不是選股爛，是心理偏誤。"
            "過度自信導致頻繁交易，交易成本吃掉報酬；損失厭惡讓人死抱賠錢股票不放；"
            "從眾心理在高點追熱門股，NVDA 漲到 900 才敢買，800 修正就嚇到賣出，兩次都錯。"
            "解決方案很簡單：建立投資系統，定期定額、紀律停損，取代情緒決策。"
            "長期持有指數基金讓複利發揮效果，這樣可以勝過 90% 的主動選股者，數據支持這個結論。\n\n"
            "【投資倒數小結】\n"
            "1. 台美股焦點標的：\n"
            "NVDA：大多數人因害怕高點不敢買、修正時恐慌殺出，正確做法是設好停損後持有\n"
            "AAPL：消費電子龍頭，適合定期定額長期持有，不要追漲殺跌\n"
            "2330：台積電長期趨勢向上，心理偏誤往往在修正時讓人錯殺，建議設定紀律買點\n"
            "MSFT：雲端護城河穩固，適合長期持有不理會短線波動\n\n"
            "2. 本集結論：\n"
            "投資最大的敵人是自己的心理偏誤，不是市場，先修練心理素質再談選股策略。"
            "建立系統化的投資規則：定期定額、設好停損點、不看盤不焦慮，紀律和耐心才是散戶對抗機構的最大優勢。"
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
