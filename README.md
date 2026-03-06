# 🤖 LazyTube-Assistant

結合 **Google NotebookLM** 與 **YouTube API** 的全自動 AI 摘要助理。它能監控您的訂閱頻道，利用 NotebookLM 的強大理解能力產出精確摘要，並即時推播至您的 **Telegram**。

## 🌟 核心功能
- **🔍 自動偵測**：每小時自動檢查訂閱頻道的最新上傳。
- **🧠 獨立 AI 摘要**：每部影片建立獨立臨時 Notebook，確保分析精確且不干擾。
- **🧹 自動清理**：摘要完成後自動刪除臨時筆記與來源，維持環境整潔。
- **📢 Telegram 通知**：即時推播包含影片標題、連結與 AI 摘要的訊息。
- **🎯 多功能 Workflow**：支援每小時自動排程與手動隨選查詢 (On-Demand)。

---

## 🔑 關鍵：如何正確更新憑證 (NLM_COOKIE_BASE64)

由於 NotebookLM 沒有官方 API，本專案依賴 `notebooklm-mcp-cli` 產生的憑證檔案。請依照以下步驟確保憑證完整：

### 1. 本地產生原始檔案
在您的 Mac/本地電腦執行：
```bash
# 強制重新登入 (會開啟瀏覽器)
nlm login --force
```
成功後，憑證會存在 `~/.notebooklm-mcp-cli/profiles/default/`。

### 2. **合併檔案並轉換 (極重要)**
`notebooklm-mcp-cli` v0.4.0+ 需要將 `metadata.json` 與 `cookies.json` 合併才是完整的憑證。請直接執行以下 Python 指令：

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
執行後，完整的 Base64 字串已複製到您的剪貼簿。**請直接貼到 GitHub Secrets 中的 `NLM_COOKIE_BASE64`。**

---

## 🚀 GitHub Actions 使用指南

本專案包含兩個主要的 Workflows，位於 `.github/workflows/`：

### 1. 定期自動摘要 (`yt-summary.yml`)
- **執行時間**：每小時第 0 分鐘執行。
- **自動化邏輯**：抓取新影片 -> 建立臨時 Notebook -> 產生摘要 -> 發送 Telegram -> 刪除 Notebook。
- **手動觸發**：在 GitHub 頁面點擊 `Actions` > `YouTube NotebookLM Summarizer` > `Run workflow` 即可立即執行一次。

### 2. 手動隨選查詢 (`nlm-on-demand.yml`)
如果您想分析「非訂閱」的影片或特定網址：
1. 點擊 `Actions` > `NLM On-Demand Query`。
2. 點擊 `Run workflow` 並填入參數：
   - **url**: YouTube 連結、PDF 網址或一般網頁連結。
   - **prompt**: 您想詢問 AI 的具體問題（預設為 5 個核心重點）。
   - **chat_id**: 接收結果的 Telegram ID。

---

## 🛠️ 環境變數 (Secrets) 設定表

請在 GitHub 儲存庫的 `Settings > Secrets and variables > Actions` 設定：

| 變數名稱 | 來源 |
| :--- | :--- |
| `YT_CLIENT_ID` | Google Cloud Console OAuth 2.0 Client ID |
| `YT_CLIENT_SECRET` | Google Cloud Console OAuth 2.0 Client Secret |
| `YT_REFRESH_TOKEN` | 具備 YouTube 權限的 Refresh Token |
| `TELEGRAM_BOT_TOKEN` | 透過 @BotFather 取得的 Token |
| `TELEGRAM_CHAT_ID` | 您的 Telegram Chat ID |
| `NLM_COOKIE_BASE64` | 以上述「合併檔案」步驟產生的 Base64 字串 |

---
*Developed by Michael*
