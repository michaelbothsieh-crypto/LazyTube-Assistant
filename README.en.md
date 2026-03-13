# 🤖 LAZYTUBE-ASSISTANT

<p align="center">
  <a href="README.md">繁體中文</a> | 
  <a href="README.zh-cn.md">简体中文</a> | 
  <a href="README.en.md">English</a>
</p>

> 🎉 **Developer Note!** A zero-cost, 24/7 automated video summarizer powered by **Google NotebookLM**.

---

**LazyTube-Assistant** eliminates information overload. Leveraging GitHub Actions free tier, it monitors, analyzes, and pushes key insights from your favorite content around the clock.

## ✨ Features

- **💸 Zero Operating Cost**: Fully powered by GitHub Actions free tier. No server required.
- **📦 Serverless Architecture**: No databases, no complex setups. Just Fork and Run.
- **🧠 Deep AI Insights**: Leveraging Google NotebookLM for logic-driven, context-aware summaries.
- **🛡️ Anti-Bot Bypass**: Built-in smart routing and multi-layer proxies (Jina Reader & Cloudflare Browser Rendering) for strict forums and news sites to ensure NotebookLM always gets clean text sources.
- **🎯 Smart Filtering**: Automatically identifies relevant content (e.g., PoE Builds, League Guides) based on your interests.
- **🛡️ Privacy by Design**: Credentials stay in isolated containers. Data is sent directly to Google.

## 🚀 Two Ways to Use

### 1. 🤖 Automated Mode (Default)
Wakes up every hour to scan your YouTube subscriptions. When a keyword-matching video is found, it generates a summary instantly.
> **Best for:** Tracking seasonal game updates, technical tutorials, or any regular content you don't want to miss.

### 2. 📱 On-Demand Mode (Advanced)
Via Telegram Webhook, simply paste any video or web URL to the bot, and the AI will begin analysis immediately.
> **Best for:** When you need a quick deep dive into a specific video but don't have time to watch the whole thing.

## 📦 Quick Start

### 1. Click Fork
Click the **Fork** button at the top right of this repository to copy it to your account.

### 2. Get Credentials (Setup Helper)
We provide a cross-platform helper to solve the trickiest auth steps:
1. Install [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) locally and run `nlm login --force`.
2. Run the setup helper:
   ```bash
   pip install google-auth-oauthlib requests
   python tools/setup_helper.py
   ```
   *(Windows user? See [Windows Guide](docs/WINDOWS_GUIDE.md))*
3. The script will complete the OAuth flow and generate a **`.env`** file.

### 3. Set Secrets
Go to GitHub `Settings > Secrets and variables > Actions`, and fill in the secrets based on the **`.env`** file.

## 🛠️ How It Works

| Component | Role |
| :--- | :--- |
| **GitHub Actions** | Compute core and automation scheduler |
| **YouTube API** | Content detection and information retrieval |
| **NotebookLM** | Core AI engine (providing deep understanding) |
| **Telegram Bot** | Your private interaction portal |

## ⚠️ Risk & Limitations

- **Non-official Protocol**: This project relies on simulated browser behavior. If Google changes NotebookLM's structure, an update may be required.
- **Credential TTL**: Cookies typically last **2-4 weeks**. Re-run `tools/setup_helper.py` when auth fails.
- **100% Privacy**: Data is processed in isolated containers and sent directly to Google.

## ❤️ Acknowledgements

The core authentication and operation logic of this project are deeply inspired by and supported by **[notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)**.

Special thanks to the author **[Jacob Ben-David](https://github.com/jacob-bd)** for developing such a powerful MCP protocol tool, enabling AI agents to operate NotebookLM programmatically.

## 📜 License
MIT License. Developed by Michael.
