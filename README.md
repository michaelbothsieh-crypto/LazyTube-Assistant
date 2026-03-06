# 🤖 LazyTube-Assistant

一個結合 **Google NotebookLM** 與 **YouTube API** 的全自動摘要工具。它能自動追蹤您訂閱的 YouTube 頻道，利用 NotebookLM 的強大理解能力產出精確摘要，並即時推播至您的 **Telegram**。

## 🌟 核心功能
- **🔍 自動偵測**：每小時自動檢查訂閱頻道的最新上傳。
- **🧠 獨立 AI 摘要**：為每部影片建立獨立臨時 Notebook，確保分析精確。
- **🧹 自動清理**：摘要完成後立即刪除臨時筆記與來源，維持環境整潔。
- **📢 Telegram 通知**：即時推播包含影片標題、連結與 AI 摘要的訊息。

---

## 🛠️ 環境變數 (Secrets) 設定指南

請在 GitHub 儲存庫的 `Settings > Secrets and variables > Actions` 設定以下變數：

### 1. YouTube API 相關 (`YT_` 系列)
- **取得連結**：[Google Cloud Console](https://console.cloud.google.com/)
- **步驟**：
    1. 建立專案並啟用 **YouTube Data API v3**。
    2. 在「憑證」頁面建立 **OAuth 2.0 用戶端 ID**（選「桌面應用程式」）。
    3. 取得 `YT_CLIENT_ID` 與 `YT_CLIENT_SECRET`。
    4. 使用 [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/) 取得 `YT_REFRESH_TOKEN` (需包含 `https://www.googleapis.com/auth/youtube.readonly` 權限)。

### 2. Telegram 通知相關 (`TELEGRAM_` 系列)
- **`TELEGRAM_BOT_TOKEN`**：找 [@BotFather](https://t.me/botfather) 建立機器人取得。
- **`TELEGRAM_CHAT_ID`**：找 [@userinfobot](https://t.me/userinfobot) 取得您的個人 ID 或頻道 ID。

### 3. NotebookLM 憑證 (`NLM_COOKIE_BASE64`)
這是本專案的核心認證。請依照以下步驟合併檔案：
1. 在本地執行 `nlm login --force` 重新登入。
2. 執行以下指令自動合併 `metadata.json` 與 `cookies.json` 並複製 Base64：
```bash
cd ~/.notebooklm-mcp-cli/profiles/default
python3 -c "
import json, base64
with open('cookies.json', 'r') as f: cookies = json.load(f)
with open('metadata.json', 'r') as f: meta = json.load(f)
meta['cookies'] = cookies
combined = json.dumps(meta)
print(base64.b64encode(combined.encode()).decode())
" | tr -d '\n' | pbcopy
```
3. 將剪貼簿內容貼到 GitHub Secret `NLM_COOKIE_BASE64`。

---

## 🚀 GitHub Actions 使用說明

本專案包含兩個 Workflows：

### 1. YouTube 自動摘要 (`yt-summary.yml`)
- **排程**：每小時自動執行。
- **功能**：抓取訂閱頻道的新影片並產生摘要。
- **手動觸發**：在 Actions 頁面選擇該工作，點擊 `Run workflow`。

### 2. 隨選查詢 (`nlm-on-demand.yml`)
- **功能**：輸入任意 URL (YouTube, PDF, 網頁) 進行即時摘要。
- **參數**：支援自訂 Prompt 與目標 Chat ID。

---
*Developed by Michael*
