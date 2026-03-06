# 🤖 LazyTube-Assistant

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Zero Cost](https://img.shields.io/badge/Cost-0_Server_Required-brightgreen)](https://github.com/features/actions)
[![Actions Status](https://img.shields.io/badge/Actions-24/7_Ready-success)](https://github.com/michaelbothsieh-crypto/LazyTube-Assistant/actions)

**LazyTube-Assistant** is a zero-cost, 24/7 automated video summarizer. Powered by **GitHub Actions**, it monitors, analyzes, and pushes key insights from your favorite content using **Google NotebookLM** and **YouTube API**.

> **🚀 Project Motto:** No server, no database, no manual operation required. Just Fork and own your personal AI assistant.

---

## 🌐 Language
- [繁體中文](README.md)
- [简体中文](README.zh-cn.md)
- [English](README.en.md)

---

## ✨ Key Features

- **💸 Zero Operation Cost**: Fully utilizes GitHub Actions' free tier, achieving truly free AI services.
- **📦 Serverless Deployment**: No need to manage databases or servers; everything runs automatically in the cloud.
- **🧠 Deep AI Analysis**: Based on [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli), it leverages Google NotebookLM for precise context-aware summaries.
- **🎯 Smart Content Filtering**: Automatically identifies gaming-related videos (e.g., PoE, Build Guides) based on your interests.
- **📢 Multiple Trigger Modes**:
    - **Automatic Mode (Default)**: Scans subscriptions every hour.
    - **On-Demand Mode (Advanced)**: Trigger instant analysis via Telegram Webhook.

---

## 🚀 Workflows & Actions

In your GitHub **Actions** tab, you will see two workflows:

### 1. YouTube NotebookLM Summarizer
- **Trigger**: Runs hourly or manually via `Run workflow`.
- **Logic**:
    1. **Auth Environment Setup**: Injects your `NLM_COOKIE_BASE64` into the runner.
    2. **Video Monitoring**: Scans your subscribed channels using YouTube API.
    3. **Smart Filtering**: Selects relevant content based on `FILTER_KEYWORDS`.
    4. **AI Summary**: Drives NotebookLM to produce structured insights.
    5. **Instant Push**: Sends results directly to your Telegram.

### 2. NLM On-Demand Query
- **Trigger**: Triggered manually or via Telegram Webhook.
- **Logic**: Analyzes any specific URL and instruction instantly.

---

## 🛠️ Quick Start (3 Steps)

### 1. Click Fork
Fork this repository to your personal account.

### 2. Get Credentials (Setup Helper)
We provide a cross-platform helper tool to handle authentication:
1. Install [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) locally and run `nlm login --force`.
2. Run the helper script:
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   This script handles YouTube OAuth and generates a **`.env`** file. *(Windows users see [Windows Guide](WINDOWS_GUIDE.md))*

### 3. Set GitHub Secrets
Go to `Settings > Secrets and variables > Actions` in your repo and fill in the values from the **`.env`** file.

---

## 🏗️ Technical Details & Security

- **Non-official Protocol**: This project uses browser simulation via MCP. If Google updates NotebookLM's structure, an update may be required.
- **Credential Lifespan**: Cookies typically last **2-4 weeks**. Re-run the helper script when auth fails.
- **100% Privacy**: All data is processed within GitHub's isolated environment and sent directly to Google.

---
*Developed by Michael*
