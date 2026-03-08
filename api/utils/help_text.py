def build_help_text(html: bool = False) -> str:
    if html:
        return (
            "🤖 <b>LazyTube NotebookLM 查詢機器人</b>\n\n"
            "<b>指令說明：</b> (問號?代表有預設值)\n"
            "📌 <code>/nlm &lt;url&gt; &lt;自訂Prompt?&gt;</code> (1-3分)\n"
            "  → 獲取來源的文字摘要\n\n"
            "📌 <code>/pic &lt;url&gt; &lt;自訂Prompt?&gt;</code> (3-5分)\n"
            "  → 生成 <b>Portrait/Detailed</b> 圖片總結 (PNG)\n\n"
            "📌 <code>/note &lt;url&gt; &lt;自訂Prompt?&gt;</code> (3-5分)\n"
            "  → 生成詳細的 <b>Markdown</b> 總結報告檔案\n\n"
            "📌 <code>/slide &lt;url&gt; &lt;自訂Prompt?&gt; &lt;語言?&gt; &lt;格式?&gt;</code> (5-10分)\n"
            "  → 產生 <b>繁體中文</b> PDF (預設) 或 PPTX 簡報\n\n"
            "<b>範例：</b>\n"
            "<code>/pic https://youtu.be/xxxxx</code>\n"
            "<code>/note https://youtu.be/xxxxx</code>\n"
            "<code>/slide https://youtu.be/xxxxx _ zh-TW/en pptx/pdf</code> (預設是 zh-TW/pdf)"
        )

    return (
        "🤖 LazyTube NotebookLM 查詢機器人\n\n"
        "指令說明： (問號?代表有預設值)\n"
        "📌 /nlm <url> <自訂Prompt?> (1-3分)\n"
        "  → 獲取來源的文字摘要\n\n"
        "📌 /pic <url> <自訂Prompt?> (3-5分)\n"
        "  → 生成 Portrait/Detailed 圖片總結 (PNG)\n\n"
        "📌 /note <url> <自訂Prompt?> (3-5分)\n"
        "  → 生成詳細的 Markdown 總結報告檔案\n\n"
        "📌 /slide <url> <自訂Prompt?> <語言?> <格式?> (5-10分)\n"
        "  → 產生繁體中文 PDF (預設) 或 PPTX 簡報\n\n"
        "範例：\n"
        "/pic https://youtu.be/xxxxx\n"
        "/note https://youtu.be/xxxxx\n"
        "/slide https://youtu.be/xxxxx _ zh-TW/en pptx/pdf (預設是 zh-TW/pdf)"
    )
