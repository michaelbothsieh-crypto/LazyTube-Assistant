# 🤖 LAZYTUBE-ASSISTANT

> 🎉 **Vibe Coding Alert!** A zero-cost, 24/7 automated video summarizer powered by **Google NotebookLM**.

**LazyTube-Assistant** eliminates information overload. Leveraging GitHub Actions free tier, it monitors, analyzes, and pushes key insights from your favorite content around the clock.

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
Wakes up every hour to scan your YouTube subscriptions. When a keyword-matching video is found, it generates a summary and pushes it instantly.
> **Best for:** Tracking seasonal game updates, technical tutorials, or any regular content you don't want to miss.

### 2. ON-DEMAND MODE (ADVANCED)
Via Telegram Webhook, simply paste any video or web URL to the bot, and the AI will begin analysis immediately.
> **Best for:** When you need a quick deep dive into a specific video but don't have time to watch the whole thing.

---

## 📦 QUICK START

### 1. CLICK FORK
Click the **Fork** button at the top right of this repository to copy it to your account.

### 2. GET CREDENTIALS (THE EASY WAY)
We provide a cross-platform helper to solve the trickiest auth steps:
1. Install [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) locally and run `nlm login --force`.
2. Run the setup helper:
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   *(Windows user? See [Windows Guide](WINDOWS_GUIDE.md))*
3. The script will complete the OAuth flow and generate a **`.env`** file.

### 3. SET SECRETS
Go to GitHub `Settings > Secrets and variables > Actions`, and fill in the secrets based on the **`.env`** file.

---

## 🛠️ HOW IT WORKS

| Component | Role |
| :--- | :--- |
| **GitHub Actions** | Compute core and automation scheduler |
| **YouTube API** | Content detection and information retrieval |
| **NotebookLM** | Core AI engine (providing deep understanding) |
| **Telegram Bot** | Your private interaction portal |

---

## ⚠️ RISK & LIMITATIONS

- **Non-official Protocol**: This project relies on simulated browser behavior. If Google changes NotebookLM's structure, an update may be required.
- **Credential TTL**: Cookies typically last **2-4 weeks**. Re-run `setup_helper.py` when auth fails.
- **100% Privacy**: Data is processed in isolated containers and sent directly to Google.

---

## ❤️ ACKNOWLEDGEMENTS

The core authentication and operation logic of this project are deeply inspired by and supported by **[notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)**.

Special thanks to the author **[Jacob Ben-David](https://github.com/jacob-bd)** for developing such a powerful MCP protocol tool, enabling AI agents to operate NotebookLM programmatically.

---

## 📜 LICENSE
MIT License. Developed by Michael.
