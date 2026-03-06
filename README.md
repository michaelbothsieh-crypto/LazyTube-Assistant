# 🤖 LAZYTUBE-ASSISTANT

> 🎉 **Vibe Coding Alert!** 這是一個基於 **Google NotebookLM** 實現「完全零成本」營運的智慧影片摘要助理。

**LazyTube-Assistant** 讓你從此告別資訊焦慮。利用 GitHub Actions 的免費資源，24/7 自動監控、分析並推播您感興趣的內容精華。

---

## 🌐 LANGUAGE
- [繁體中文](README.md)
- [简体中文](README.zh-cn.md)
- [English](README.en.md)

---

## ✨ FEATURES

- **💸 ZERO OPERATING COST**: Fully powered by GitHub Actions free tier. No server required.
- **📦 SERVERLESS ARCHITECTURE**: No databases, no complex setups. Just Fork and Run.
- **🧠 DEEP AI INSIGHTS**: Leveraging Google NotebookLM for logic-driven, context-aware summaries.
- **🎯 SMART FILTERING**: Automatically identifies relevant content (e.g., PoE Builds, League Guides) to save your time.
- **🛡️ SECURE BY DESIGN**: Your data stays in the cloud. All credentials are masked and secure.

---

## 🚀 TWO WAYS TO USE

### 1. 🤖 AUTOMATED MODE (DEFAULT)
每小時自動甦醒，掃描您的 YouTube 訂閱清單，發現匹配關鍵字的影片後立即產出摘要並推播。
> **Best for:** 追蹤遊戲賽季更新、技術教學、或任何您不想錯過的定期動態。

### 2. 隨選模式 (ADVANCED)
透過 Telegram Webhook 連結，直接將任何影片或網頁網址傳給機器人，AI 會立即開始分析。
> **Best for:** 臨時需要深入了解特定影片，但沒時間看完。

---

## 📦 QUICK START

### 1. CLICK FORK
點擊本儲存庫右上角的 **Fork** 按鈕，複製到您的個人帳號。

### 2. GET CREDENTIALS (THE EASY WAY)
我們提供了一個全自動助手解決最麻煩的認證步驟：
1. 本地執行 `nlm login --force`。
2. 執行設定助手：
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   *(Windows 使用者？請參閱 [Windows 指南](WINDOWS_GUIDE.md))*
3. 腳本會自動完成授權並產出 **`.env`** 檔案。

### 3. SET SECRETS
前往 GitHub `Settings > Secrets and variables > Actions`，對照 **`.env`** 填入內容。

---

## 🛠️ HOW IT WORKS

| 組件 | 角色 |
| :--- | :--- |
| **GitHub Actions** | 運算核心與自動化排程器 |
| **YouTube API** | 內容偵測與資訊檢索 |
| **NotebookLM** | 核心 AI 引擎（提供深度理解） |
| **Telegram Bot** | 您的私人互動入口 |

---

## ⚠️ RISK & LIMITATIONS

- **Non-official Protocol**: This project relies on simulated browser behavior. If Google changes NotebookLM's structure, an update may be required.
- **Credential TTL**: Cookies typically last **2-4 weeks**. Re-run `setup_helper.py` when auth fails.
- **100% Privacy**: Data is processed in isolated containers and sent directly to Google.

---

## ❤️ ACKNOWLEDGEMENTS

本專案的核心認證與操作邏輯深受 **[notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)** 的啟發與支持。

特別感謝作者 **[Jacob Ben-David](https://github.com/jacob-bd)** 開發了如此強大的 MCP 協議工具，讓 AI 代理能以程式化方式操作 NotebookLM。

---

## 📜 LICENSE
MIT License. Developed by Michael.
