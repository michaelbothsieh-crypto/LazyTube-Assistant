# 🤖 LazyTube-Assistant

[![GitHub License](https://img.shields.io/github/license/michaelbothsieh-crypto/LazyTube-Assistant)](LICENSE)
[![Actions Status](https://img.shields.io/github/actions/workflow/status/michaelbothsieh-crypto/LazyTube-Assistant/yt-summary.yml?branch=main&label=Automated%20Summary)](https://github.com/michaelbothsieh-crypto/LazyTube-Assistant/actions)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)

**LazyTube-Assistant** 是一個結合 **Google NotebookLM** 與 **YouTube API** 的智慧摘要助手。它能自動過濾您感興趣的內容，產出精確的繁體中文重點，並即時推播至您的 **Telegram**。

> **懶人必備**：不再需要點開每部影片，讓 AI 幫您精煉出 5 個核心重點！

---

## ✨ 核心亮點

- **🎯 智慧關鍵字過濾**：僅針對感興趣的標題（如：PoE, Build, 賽季攻略）進行分析，節省 API 配額與時間。
- **🧠 深度內容理解**：利用 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 模擬瀏覽器行為，獲得比一般 GPT 更精確的影片摘要。
- **📱 隨傳隨到**：直接將 YouTube 網址貼給機器人，AI 會立即開始分析並自動回傳。
- **🧹 自動清理**：摘要完成後立即銷毀臨時筆記，保護隱私且維持 NotebookLM 環境整潔。
- **⚡ 零成本營運**：完全託管於 GitHub Actions 與 Vercel，無需自備伺服器。

---

## 🚀 快速上手 (Quick Start)

### 1. 點擊 Fork
點擊儲存庫右上角的 **Fork** 按鈕，將專案複製到您的帳號下。

### 2. 取得憑證 (使用自動化助手)
我們提供了一個跨平台的輔助工具，只需執行一次即可取得所有 Secret：

1. 本地安裝 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 並執行 `nlm login --force` 確保登入。
2. 執行設定助手：
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   *(Windows 使用者請參閱 [Windows 安裝指南](WINDOWS_GUIDE.md))*
3. 腳本會自動完成 YouTube 授權並產出一個 **`.env`** 檔案。

### 3. 設定 GitHub Secrets
前往您 Fork 的專案頁面：`Settings > Secrets and variables > Actions`，對照 **`.env`** 檔案內容填入變數。

---

## 🏗️ 系統架構

- **Trigger 層 (Vercel)**：接收 Telegram Webhook 指令（如貼上網址）。
- **Worker 層 (GitHub Actions)**：執行核心分析任務（YouTube 抓取、NotebookLM 摘要）。
- **Security**：內建使用者白名單 (`ALLOWED_USERS`)，確保只有您本人可以觸發分析。

---

## 🤖 Telegram 指令手冊

- **`/nlm <網址> [指令]`**：手動分析特定內容。
- **直接貼網址**：若已關閉隱私模式，直接在對話框貼上網址，助手也會自動辨識。
- **`/my_id`**：取得您的 Telegram User ID，用於填寫白名單設定。

---

## 🛡️ 安全性與隱私

- **數據隱私**：所有影片內容僅傳送至 Google NotebookLM，不經過任何第三方伺服器。
- **憑證更新**：Cookie 有效期通常為 2-4 週，失效時請重新執行 `setup_helper.py`。

---
*Developed by Michael*
