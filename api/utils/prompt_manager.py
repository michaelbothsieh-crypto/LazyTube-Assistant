import re

# NLM 預設 Prompt 關鍵字對照表
NLM_PROMPT_MAP = {
    "default": "請用繁體中文列出這部影片或這個來源的 5 個核心重點，並在最後加上一句話的總結。",
    "detail": "請用繁體中文詳細分析這部影片的內容，包含背景介紹、主要論點、案例說明與結論，並以結構化的方式呈現。",
    "step": "請將這部影片中的操作步驟或流程，整理成一份清晰的繁體中文步驟指南。",
    "qa": "請針對這部影片內容，整理出 5 個最常見的繁體中文問答 (Q&A)，幫助讀者快速掌握重點。",
    "short": "請用 100 字以內的繁體中文精簡總結這部影片的核心訊息。",
    "poe": "請針對這部《流亡黯道 (Path of Exile)》影片內容進行摘要，依序標號說明：1. 流派機制、2. 地圖策略、3. 關鍵裝備、4. 財經策略、5. 影片獨特之處。請以繁體中文回覆，嚴禁使用任何 Markdown 加粗語法（如 **）",
    "finance": "你現在是一位「資深財經分析師」。請幫我精準分析這部影片，並以繁體中文條列出以下 4 個重點：1.核心結論與預測：用 3 句話總結當前局勢，以及講者對未來走向的預測。2.台美股焦點標的：明確列出提及的「台股」與「美股」代號或公司名，並附上講者的看法。3.關鍵數據與指標：抓出講者提到的具體價位（支撐/壓力）、財報數字或技術指標。4.操作策略與風險：統整講者建議的具體買賣策略，以及特別警告的潛在風險。請以繁體中文回覆，嚴禁使用任何 Markdown 加粗語法（如 ** 或 __）。"
}

def get_nlm_prompt(user_input: str) -> str:
    """
    根據用戶輸入的關鍵字或自訂 Prompt，回傳最終要使用的 Prompt。
    並強制要求使用繁體中文且嚴禁加粗。
    """
    # 最強力的後綴規範
    force_suffix = (
        "\n\n【重要規範：請完全以「繁體中文」回答。直接輸出內容，嚴禁包含任何思考過程。嚴禁使用任何 Markdown 加粗語法（如 ** 或 __），請用純文字或標號呈現。】"
    )
    
    if not user_input or user_input.strip() == "":
        return NLM_PROMPT_MAP["default"] + force_suffix
    
    keyword = user_input.strip().lower()
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
