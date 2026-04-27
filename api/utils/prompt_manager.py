from __future__ import annotations
import re
from pathlib import Path

# data/prompts/ 目錄：優先從此載入，讓 git 自動追蹤 prompt 變更紀錄
_PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "prompts"


def _load_prompt_file(key: str) -> str | None:
    """嘗試從 data/prompts/<key>.txt 載入，找不到回傳 None。"""
    path = _PROMPTS_DIR / f"{key}.txt"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    return None

# NLM 預設 Prompt 關鍵字對照表
NLM_PROMPT_MAP = {
    "default": "請用繁體中文列出這部影片或這個來源的 5 個核心重點，並在最後加上一句話的總結。",
    "detail": "請用繁體中文詳細分析這部影片的內容，包含背景介紹、主要論點、案例說明與結論，並以結構化的方式呈現。",
    "step": "請將這部影片中的操作步驟或流程，整理成一份清晰的繁體中文步驟指南。",
    "qa": "請針對這部影片內容，整理出 5 個最常見的繁體中文問答 (Q&A)，幫助讀者快速掌握重點。",
    "short": "請用 100 字以內的繁體中文精簡總結這部影片的核心訊息。",
    "poe": "請針對這部《流亡黯道 (Path of Exile)》影片內容進行摘要，依序標號說明：1. 流派機制、2. 地圖策略、3. 關鍵裝備、4. 財經策略、5. 影片獨特之處。請以繁體中文回覆，嚴禁使用任何 Markdown 加粗語法（如 **）",
    "finance": "你現在是一位「資深財經分析師」。請幫我精準分析這部影片，並以繁體中文條列出以下 4 個重點：1.核心結論與預測：用 3 句話總結當前局勢，以及講者對未來走向的預測。2.台美股焦點標的：明確列出提及的「台股」與「美股」代號或公司名，並附上講者的看法。3.關鍵數據與指標：抓出講者提到的具體價位（支撐/壓力）、財報數字或技術指標。4.操作策略與風險：統整講者建議的具體買賣策略，以及特別警告的潛在風險。請以繁體中文回覆，嚴禁使用任何 Markdown 加粗語法（如 ** 或 __）。",
    "podcast": (
        "你是一位專業的台灣財經 Podcast 分析助理，深諳台灣股市用語與投資文化。\n"
        "請依以下四個段落格式輸出，全程使用台灣繁體中文財經用語：\n\n"
        "【文字紀錄】\n"
        "保留講者原始語氣與口語表達，整理為流暢的對話式逐字稿。"
        "忠實呈現台灣財經慣用語，例如：多頭、空頭、拉回、布局、法說、籌碼、外資、融資、"
        "軋空、止跌訊號、關卡、強攻、吃貨、壓回等。\n\n"
        "【個股觀點】\n"
        "每一檔個股獨立一行，嚴格依照以下格式（以全形「｜」分隔）：\n"
        "代號｜方向｜時間維度｜關鍵價位｜講者看法\n"
        "・方向：三擇一 → 多方看好 / 空方謹慎 / 中性觀望\n"
        "・時間維度：三擇一 → 短線 / 中線 / 長線\n"
        "・關鍵價位：支撐與壓力價位（無提及則填「—」）\n"
        "・講者看法：原汁原味保留口吻，一行內完成，勿截斷重點\n\n"
        "【市場總結與操作建議】\n"
        "1. 宏觀背景：一句話說明目前所處的市場週期或總體環境\n"
        "2. 核心看法：條列講者最重要的 2-3 個投資觀點，每點前加「・」\n"
        "3. 主要風險：條列潛在下行風險 2-3 項，每點前加「⚠」\n"
        "4. 操作策略：具體說明進出場時機、倉位配置或觀察指標，保留講者原始建議的力道\n\n"
        "【重要規範：直接輸出四個段落，嚴禁包含思考過程或說明文字。"
        "嚴禁使用 Markdown 加粗（** 或 __）。全程台灣繁體中文財經用語。】"
    ),
}


def get_nlm_prompt(user_input: str) -> str:
    """
    根據用戶輸入的關鍵字或自訂 Prompt，回傳最終要使用的 Prompt。
    優先順序：data/prompts/<key>.txt > NLM_PROMPT_MAP > user_input 原文。
    """
    force_suffix = (
        "\n\n【重要規範：請完全以「繁體中文」回答。直接輸出內容，嚴禁包含任何思考過程。嚴禁使用任何 Markdown 加粗語法（如 ** 或 __），請用純文字或標號呈現。】"
    )

    if not user_input or user_input.strip() == "":
        return NLM_PROMPT_MAP["default"] + force_suffix

    keyword = user_input.strip().lower()

    # 1. 優先從檔案載入（支援 git 版本追蹤）
    from_file = _load_prompt_file(keyword)
    if from_file:
        return f"{from_file}{force_suffix}"

    # 2. Fallback 到內建 map
    base_prompt = NLM_PROMPT_MAP.get(keyword, user_input)
    return f"{base_prompt}{force_suffix}"

def get_optimized_prompt(url: str) -> str:
    """
    根據 URL 類型返回優化後的簡報生成提示詞。
    """
    is_youtube = "youtube.com" in url or "youtu.be" in url
    
    base_structure = (
        "請將此來源內容轉換為專業且具備視覺化邏輯的簡報結構。\n"
        "內容結構要求：\n"
        "1. [標題頁]：包含一個吸引人的標題與副標題。\n"
        "2. [簡介頁]：說明此主題的核心價值與為什麼讀者需要關注。\n"
        "3. [核心章節]：依邏輯拆解為 3-5 個主要章節。每張投影片僅限一個核心概念，並提供 3-4 個精簡的重點條列（Bullet Points）。\n"
        "4. [總結頁]：列出 3 個最具代表性的結論或下一個行動建議 (Next Steps)。\n\n"
        "語氣與風格要求：\n"
        "- 語氣專業、自信且具說服力。\n"
        "- 使用繁體中文，術語應統一。\n"
        "- 每句話力求精簡，避免長篇大論。\n"
        "- 如果來源有提及具體數據或對比，請將其轉化為易於理解的簡報語言。"
    )

    if is_youtube:
        prefix = "📌 這是一段影片來源。請特別注意影片中的敘事脈絡、實際演示範例以及講者的核心觀點。\n"
        return prefix + base_structure
    
    return base_structure
