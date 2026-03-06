# 🤖 LazyTube-Assistant

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Zero Cost](https://img.shields.io/badge/Cost-0_Server_Required-brightgreen)](https://github.com/features/actions)
[![Actions Status](https://img.shields.io/badge/Actions-24/7_Ready-success)](https://github.com/michaelbothsieh-crypto/LazyTube-Assistant/actions)

**LazyTube-Assistant** 是一個實現「完全零成本」營運的智慧影片摘要助理。利用 **GitHub Actions** 的免費運算資源，自動監控、分析並即時推播您感興趣的內容。

> **🚀 專案主打：** 無需租用伺服器、無需管理資料庫、無需持續開機。只要 Fork 即可擁有 24/7 的 AI 摘要機器人。

---

## 🚀 運作流程與 Actions 說明

當您在 GitHub 的 **Actions** 分頁中查看時，會看到以下兩個工作流：

### 1. YouTube 自動摘要 (`YouTube NotebookLM Summarizer`)
- **何時執行**：每小時自動執行一次，或您手動點擊 `Run workflow`。
- **運作邏輯**：
    1. **認證環境佈署**：自動將您的 `NLM_COOKIE_BASE64` 注入雲端容器。
    2. **影片監控**：使用 YouTube API 掃描您訂閱的頻道。
    3. **智慧過濾**：根據 `FILTER_KEYWORDS` 挑選出遊戲或相關內容。
    4. **AI 摘要**：驅動 NotebookLM 產出繁體中文摘要。
    5. **即時推播**：將結果發送至您的 Telegram。

### 2. 隨選查詢 (`NLM On-Demand Query`)
- **何時執行**：由您手動觸發（或透過 Telegram Webhook 觸發）。
- **運作邏輯**：接受自定義網址與指令，即時產出單篇摘要並回傳。

---

## 🛠️ 快速上手 (只需三步驟)

### 1. 點擊 Fork
將本儲存庫 Fork 到您的個人帳號下。

### 2. 取得憑證 (本地執行助手)
我們提供了一個全自動工具協助您完成認證：
1. 本地執行 `nlm login --force` 確保登入。
2. 執行設定助手：
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   腳本會自動完成 YouTube 授權並產出 **`.env`** 檔案。*(Windows 使用者請參閱 [Windows 指南](WINDOWS_GUIDE.md))*

### 3. 設定 GitHub Secrets
前往 GitHub `Settings > Secrets and variables > Actions`，對照 **`.env`** 檔案內容填入：

| Secret 名稱 | 用途說明 |
| :--- | :--- |
| `YT_CLIENT_ID` | YouTube API 用戶端 ID |
| `YT_CLIENT_SECRET` | YouTube API 用戶端金鑰 |
| `YT_REFRESH_TOKEN` | 用於長效存取您訂閱清單的權杖 |
| `TELEGRAM_BOT_TOKEN` | Telegram 機器人金鑰 (@BotFather) |
| `TELEGRAM_CHAT_ID` | 接收摘要的個人或群組 ID |
| `NLM_COOKIE_BASE64` | 核心憑證 (由 setup_helper.py 產生) |
| `FILTER_KEYWORDS` | (選填) 感興趣的關鍵字，以逗號分隔 |

---

## 🏗️ 核心技術與風險說明

- **非官方通訊協議**：本專案基於 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 模擬瀏覽器行為。若 Google 修改網頁結構，本工具可能需更新。
- **憑證時效**：Cookie 通常維持 2-4 週，失效時請重新執行助手腳本。
- **隱私承諾**：所有數據僅在 GitHub 的隔離環境處理，不經過第三方伺服器。

---
*Developed by Michael*
