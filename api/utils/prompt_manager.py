import re

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
