# 🤖 LazyTube-Assistant

一個結合 **Google NotebookLM** 與 **YouTube API** 的個人化全自動摘要工具。本專案專為解決資訊焦慮設計，能自動追蹤訂閱內容或透過自定義 Hook（如行動裝置、Telegram）實現隨選 AI 分析。

> **核心依賴**：本專案基於 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 開發，利用其 MCP 協議實現對 NotebookLM 的深度操作。

## 🌟 核心功能
- **🔍 自動監控**：定時檢查 YouTube 訂閱頻道，第一時間掌握新知。
- **🧠 隨選分析**：支援外部 Hook 觸發（如 Telegram Webhook），實現遠端隨傳隨到的 AI 摘要。
- **🧹 自動清理**：摘要完成後立即銷毀臨時 Notebook，保護隱私且維持環境整潔。
- **📢 多端通知**：結果可即時推播至您的行動裝置或 Telegram 頻道。

---

## 🛠️ 開發紀錄與技術挑戰

在開發過程中，我們解決了針對 `notebooklm-mcp-cli` (v0.4.0+) 在雲端環境執行的關鍵卡關問題：

### 1. 認證完整性 (CSRF Token 謎題)
- **挑戰**：單純使用 `cookies.json` 會導致 Google 回報憑證無效。
- **解決**：我們發現工具需要 `metadata.json` 裡的 `csrf_token`。由於官方指令在匯入時會自動過濾部分數據，本專案改用「**先由指令初始化結構，再手動注入完整合併 JSON**」的調包計（Bait-and-Switch），確保在無頭環境（Headless）也能 100% 認證成功。

### 2. 多環境路徑相容
- **挑戰**：Ubuntu (GitHub Actions) 與 Mac 的配置路徑完全不同，且 0.4.0 版本將 Profile 視為資料夾而非檔案。
- **解決**：我們實作了動態路徑偵測邏輯，精確鎖定 `~/.notebooklm-mcp-cli/profiles/default/auth.json` 進行數據注入。

---

## 🏗️ 系統架構與安全性

本專案採用 **「觸發與執行分離」** 的架構：

1.  **觸發層 (Trigger)**：支援 Vercel API 作為 Webhook 端點。
    - **安全性**：透過 `TG_WEBHOOK_SECRET` 確保只有來自授權來源（如 Telegram 官方伺服器）的請求能被接受。
    - **隱私**：建議開發者在代碼中加入 `chat_id` 白名單檢查，確保機器人僅回應您本人的指令。
2.  **執行層 (Worker)**：利用 [GitHub Actions](https://github.com/features/actions) 作為運算核心，避免長時間占用伺服器資源。

---

## ⚠️ 風險聲明與限制

1. **非官方通訊協議**：本專案依賴模擬瀏覽器行為與 Google 通訊。一旦 Google 修改 NotebookLM 的網頁結構，本工具可能需要更新後方可使用。
2. **憑證時效性**：`NLM_COOKIE_BASE64` 憑證通常僅維持 **2 至 4 週**。失效時請參閱下方教學重新產生。
3. **配額限制**：[YouTube Data API v3](https://developers.google.com/youtube/v3) 每日有配額限制，請合理設定掃描頻率。

---

## 🔑 憑證更新教學

當功能失效時，請在本地執行以下合併指令，產生 22,060 字元以上的完整 Base64：

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
將結果更新至 GitHub Secret：`NLM_COOKIE_BASE64`。

---

## 🛠️ 環境變數 (Secrets) 參考

| 變數名稱 | 來源 / 用途 |
| :--- | :--- |
| `YT_CLIENT_ID` | [Google Cloud Console](https://console.cloud.google.com/) OAuth 憑證 |
| `TELEGRAM_BOT_TOKEN` | [BotFather](https://t.me/botfather) 取得 |
| `NLM_COOKIE_BASE64` | 本地合併後的完整認證 JSON |
| `TG_WEBHOOK_SECRET` | 用於驗證 Webhook 來源的自定義安全金鑰 |

---
*Developed by Michael*
