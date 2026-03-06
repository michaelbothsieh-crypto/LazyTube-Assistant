# 🤖 LazyTube-Assistant

一個結合 **Google NotebookLM** 與 **YouTube API** 的全自動摘要工具。它能自動追蹤您訂閱的 YouTube 頻道，利用 NotebookLM 的強大理解能力產出精確摘要，並即時推播至您的 **Telegram**。

## 🌟 核心功能
- **🔍 自動偵測**：每小時自動檢查訂閱頻道的最新上傳。
- **🧠 獨立 AI 摘要**：為每部影片建立獨立臨時 Notebook，確保分析精確且不干擾。
- **🧹 自動清理**：摘要完成後立即刪除臨時筆記與來源，維持環境整潔。
- **📢 Telegram 通知**：即時推播包含影片標題、連結與 AI 摘要的訊息。

---

## 🛠️ 環境變數 (Secrets) 設定指南

請在 GitHub 儲存庫的 `Settings > Secrets and variables > Actions` 設定以下變數：

### 1. YouTube API 相關 (`YT_` 系列)
這些變數讓程式能讀取您的訂閱清單。
- **取得連結**：[Google Cloud Console](https://console.cloud.google.com/)
- **步驟**：
    1. 建立專案並搜尋啟用 **YouTube Data API v3**。
    2. 前往「憑證」頁面，點擊「建立憑證」> **OAuth 2.0 用戶端 ID**。
    3. 應用程式類型選擇「桌面應用程式」。
    4. 取得 **`YT_CLIENT_ID`** 與 **`YT_CLIENT_SECRET`**。
    5. 前往 [OAuth 2.0 Playground](https://developers.google.com/oauthplayground/)：
        - 右側設定點擊齒輪，勾選 `Use your own OAuth credentials` 並輸入 ID 與 Secret。
        - 左側搜尋 `YouTube Data API v3`，選擇 `https://www.googleapis.com/auth/youtube.readonly`。
        - 點擊 `Authorize APIs` 並登入。
        - 點擊 `Exchange authorization code for tokens` 取得 **`YT_REFRESH_TOKEN`**。

### 2. Telegram 通知相關 (`TELEGRAM_` 系列)
- **`TELEGRAM_BOT_TOKEN`**：找 [@BotFather](https://t.me/botfather) 輸入 `/newbot` 建立機器人取得。
- **`TELEGRAM_CHAT_ID`**：找 [@userinfobot](https://t.me/userinfobot) 取得您的個人 ID 或頻道 ID。

### 3. NotebookLM 憑證 (`NLM_COOKIE_BASE64`)
這是本專案的核心。**必須合併 `metadata.json` 與 `cookies.json` 才是完整憑證**：
1. 本地執行 `nlm login --force` 重新登入。
2. 前往憑證目錄並執行合併指令：
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

### 1. 自動模式
- 系統預設每小時第 0 分鐘自動執行一次。

### 2. 手動觸發
- 前往 GitHub 頁面點擊 `Actions` > `YouTube NotebookLM Summarizer` > `Run workflow`。

---
*Developed by Michael*
