# 🤖 LazyTube-Assistant

一個結合了 **Google NotebookLM** 與 **YouTube API** 的自動化 AI 摘要助理。它能自動追蹤您訂閱的 YouTube 頻道，利用 NotebookLM 的強大理解能力產出精確的影片摘要，並即時推播至您的 **Telegram**。

## 🌟 核心功能
- **🔍 自動偵測**：每小時自動檢查訂閱頻道的最新上傳，確保不漏掉任何重要資訊。
- **🧠 獨立 AI 摘要**：
    - 為每部影片建立**獨立的臨時 Notebook**，避免不同影片內容互相干擾。
    - 利用 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 驅動 NotebookLM 產出 3-5 個核心重點。
- **🧹 自動清理**：摘要完成後立即刪除臨時 Notebook 與來源，保持您的 NotebookLM 環境整潔且不佔空間。
- **📢 Telegram 通知**：摘要完成後，立即將標題、網址與 AI 重點推播至您的手機。
- **⚡ GitHub Actions 驅動**：完全雲端化運行，無需自備伺服器或保持電腦開機。
- **🎯 手動觸發 (On-Demand)**：支援手動輸入 URL 與 Prompt，隨時對特定資源進行深度分析。

## 🚀 快速開始

### 1. 環境設定 (Secrets)
在 GitHub 儲存庫的 `Settings > Secrets and variables > Actions` 中設定以下變數：

| 變數名稱 | 說明 |
| :--- | :--- |
| `YT_CLIENT_ID` | Google Cloud Console 的 OAuth 2.0 Client ID |
| `YT_CLIENT_SECRET` | Google Cloud Console 的 OAuth 2.0 Client Secret |
| `YT_REFRESH_TOKEN` | 具備 YouTube ReadOnly 權限的 Refresh Token |
| `TELEGRAM_BOT_TOKEN` | 透過 @BotFather 取得的 Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 接收通知的 Telegram Chat ID |
| `NLM_COOKIE_BASE64` | `nlm login` 產生的 `auth.json` 內容之 Base64 編碼 |

### 2. 本地開發與測試
如果您想在本地執行，請安裝相依項目：

```bash
pip install -r requirements.txt
pip install notebooklm-mcp-cli
```

執行主程式：
```bash
# 確保已設定上述環境變數
python main.py
```

## 🛠️ GitHub Workflows 說明

### 1. YouTube NotebookLM Summarizer (`yt-summary.yml`)
- **執行頻率**：每小時執行一次。
- **邏輯**：抓取新影片 -> 建立臨時 Notebook -> 產生摘要 -> 發送 Telegram -> 刪除 Notebook。

### 2. NLM On-Demand Query (`nlm-on-demand.yml`)
- **觸發方式**：手動觸發 (Workflow Dispatch)。
- **用途**：輸入任意 URL (YouTube, PDF, 網頁) 與自訂 Prompt，即時獲取分析結果。

## 📝 注意事項
- **Cookie 有效期**：`NLM_COOKIE_BASE64` 取決於您的 Google 登入狀態，若出現 401 或權限錯誤，請重新執行 `nlm login` 並更新 Secret。
- **配額限制**：本專案預設每次執行最多處理 5 部影片（可透過變數 `MAX_VIDEOS_PER_RUN` 調整），以避免觸發 API 頻率限制。

---
*Developed by Michael*
