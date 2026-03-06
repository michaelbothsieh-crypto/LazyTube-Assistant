# 🤖 LazyTube-Assistant

[![GitHub License](https://img.shields.io/github/license/michaelbothsieh-crypto/LazyTube-Assistant)](LICENSE)
[![Actions Status](https://img.shields.io/github/actions/workflow/status/michaelbothsieh-crypto/LazyTube-Assistant/yt-summary.yml?branch=main&label=Automated%20Summary)](https://github.com/michaelbothsieh-crypto/LazyTube-Assistant/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

**LazyTube-Assistant** 是一個基於 **Google NotebookLM** 與 **YouTube API** 的智慧追劇助理。它能自動過濾您感興趣的遊戲內容，利用 NotebookLM 的強大上下文理解能力產出精確摘要，並即時推播至 **Telegram**。

不再需要點開每部影片，讓 AI 幫您過濾出 5 個核心重點！

---

## ✨ 核心亮點

- **🎯 智慧關鍵字過濾**：僅針對感興趣的標題（如：PoE, Build, 賽季攻略）進行分析，節省 API 配額與時間。
- **🧠 深度 AI 理解**：利用 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 模擬瀏覽器行為，獲取比一般 GPT 更精確的影片上下文摘要。
- **🧹 自動清理機制**：任務完成後立即銷毀臨時 Notebook，保護隱私且維持環境整潔。
- **⚡ 零成本營運**：完全託管於 GitHub Actions 與 Vercel，24/7 不間斷服務且無需自備伺服器。
- **📱 隨選摘要支援**：支援行動裝置觸發 Webhook，隨時對特定 URL 進行 AI 深度分析。

---

## 🚀 快速上手 (Quick Start)

### 1. 取得認證憑證 (核心步驟)
本專案依賴 NotebookLM 的 Session Cookie。請依照以下步驟操作：
1. 在本地安裝 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 並執行 `nlm login --force`。
2. 進入憑證目錄並執行本專案附帶的工具：
   ```bash
   python auth_tool.py
   ```
3. 複製輸出的 Base64 字串，準備貼到 GitHub Secrets。

### 2. 環境變數設定
在 GitHub 儲存庫的 `Settings > Secrets > Actions` 設定以下變數：

| 變數名稱 | 來源 / 用途 |
| :--- | :--- |
| `YT_CLIENT_ID` | YouTube API 用戶端 ID |
| `YT_REFRESH_TOKEN` | YouTube API 重新整理令牌 |
| `TELEGRAM_BOT_TOKEN` | Telegram 機器人 Token |
| `NLM_COOKIE_BASE64` | `auth_tool.py` 產生的合併憑證 |
| `FILTER_KEYWORDS` | (選填) 自定義過濾關鍵字，以逗號分隔 |

---

## 🏗️ 系統架構

1. **Trigger 層 (Vercel)**：接收 Telegram 指令或行動裝置 Hook。
2. **Worker 層 (GitHub Actions)**：執行 YouTube 抓取、NotebookLM 分析與推播。
3. **AI 層 (NotebookLM)**：負責處理最核心的內容理解與摘要產出。

---

## 🛡️ 安全性與風險告知

- **隱私聲明**：專案會將 URL 傳送至 Google NotebookLM 伺服器，請勿分析敏感內容。
- **維護提醒**：Cookie 通常有效期為 2-4 週，失效時需重新執行 `auth_tool.py`。
- **合規性**：本專案使用非官方通訊協議，請遵守 Google 相關使用規範。

---
*Developed by Michael*
