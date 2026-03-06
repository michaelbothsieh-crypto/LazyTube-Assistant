# 🤖 LazyTube-Assistant

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Zero Cost](https://img.shields.io/badge/Cost-0_Server_Required-brightgreen)](https://github.com/features/actions)
[![Actions Status](https://img.shields.io/badge/Actions-24/7_Ready-success)](https://github.com/michaelbothsieh-crypto/LazyTube-Assistant/actions)

**LazyTube-Assistant** 是一個實現「完全零成本」營運的智慧影片摘要助理。利用 **GitHub Actions** 的免費運算資源，自動監控、分析並推播您感興趣的內容。

> **🚀 專案主打：** 無需租用伺服器、無需管理資料庫、無需持續開機。只要 Fork 即可擁有 24/7 的 AI 摘要機器人。

---

## ✨ 核心特色

- **💸 0 元營運成本**：完全依賴 GitHub Actions 免費額度，實現真正的零開銷 AI 服務。
- **📦 免架設環境**：無需安裝資料庫或設定複雜的伺服器環境，一切都在雲端自動執行。
- **🧠 深度 AI 解析**：基於 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 串接 Google NotebookLM，產出最具邏輯的繁體中文影片重點。
- **🎯 智慧內容過濾**：自動識別遊戲相關影片（如：PoE, Build 攻略），精確命中您的興趣。
- **📢 多元觸發模式**：
    - **自動模式 (預設)**：每小時自動掃描訂閱。
    - **隨選模式 (進階)**：透過 Telegram Webhook 實現遠端即時分析。

---

## 🚀 快速上手 (只需三步驟)

### 1. 點擊 Fork
將本儲存庫 Fork 到您的個人帳號下。

### 2. 取得憑證 (本地執行助手)
我們提供了一個全自動工具協助您完成最困難的認證步驟：
1. 本地執行 `nlm login --force` 確保登入。
2. 執行設定助手：
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   腳本會自動完成 YouTube 授權並產出 **`.env`** 檔案。*(Windows 使用者請參閱 [Windows 指南](WINDOWS_GUIDE.md))*

### 3. 設定 GitHub Secrets
前往 GitHub `Settings > Secrets and variables > Actions`，對照 **`.env`** 檔案將內容填入。

---

## 🏗️ 運作原理

1. **GitHub Actions**：作為定時器與運算中心，每小時自動甦醒執行任務。
2. **YouTube Data API**：用於輕量化掃描您的訂閱頻道動態。
3. **NotebookLM**：作為核心 AI 引擎，對影片字幕進行深度理解。
4. **Telegram Bot**：作為最終的訊息接收端。

---

## ⚠️ 風險聲明與隱私

- **非官方通訊**：本專案依賴模擬瀏覽器技術，可能隨 Google 網頁更新而需調整。
- **憑證時效**：Cookie 通常維持 2-4 週，失效時再次執行 `setup_helper.py` 即可。
- **100% 隱私**：所有數據僅在 GitHub Actions 容器內處理，並直接傳送至 Google，不經過任何第三方中轉。

---
*Developed by Michael*
