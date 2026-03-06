# 🤖 LAZYTUBE-ASSISTANT

> 🎉 **Vibe Coding Alert!** 一个基于 **Google NotebookLM** 实现“完全零成本”运营的智能视频摘要助理。

**LazyTube-Assistant** 让你从此告别信息焦虑。利用 GitHub Actions 的免费资源，24/7 自动监控、分析并实时推送您感兴趣的内容精华。

---

## 🌐 LANGUAGE
- [繁體中文](README.md)
- [简体中文](README.zh-cn.md)
- [English](README.en.md)

---

## ✨ FEATURES

- **💸 ZERO OPERATING COST**: 完全依赖 GitHub Actions 免费额度。实现真正的零开销 AI 服务。
- **📦 SERVERLESS ARCHITECTURE**: 无需数据库，无需复杂配置。只要 Fork 即可运行。
- **🧠 DEEP AI INSIGHTS**: 基于 Google NotebookLM 提供逻辑严密、引用精准的视频重点摘要。
- **🎯 SMART FILTERING**: 自动识别相关内容（如：PoE 攻略、赛季更新），精准命中您的兴趣。
- **🛡️ SECURE BY DESIGN**: 所有凭证均在隔离容器中处理，隐私安全无虞。

---

## 🚀 TWO WAYS TO USE

### 1. 🤖 AUTOMATED MODE (DEFAULT)
每小时自动苏醒，扫描您的 YouTube 订阅列表。发现匹配关键字的视频后立即产出摘要并推送。
> **Best for:** 追踪游戏赛季更新、技术教程、或任何您不想错过的定期动态。

### 2. 隨選模式 (ADVANCED)
通过 Telegram Webhook 链接，直接将任何视频或网页网址发给机器人，AI 会立即开始分析。
> **Best for:** 临时需要深入了解特定视频，但没时间看完。

---

## 📦 QUICK START

### 1. CLICK FORK
点击本存储库右上角的 **Fork** 按钮，复制到您的个人账号。

### 2. GET CREDENTIALS (THE EASY WAY)
我们提供了一个全自动助手解决最麻烦的认证步骤：
1. 本地安装 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 并执行 `nlm login --force`。
2. 执行设置助手：
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   *(Windows 用户？请参阅 [Windows 指南](WINDOWS_GUIDE.md))*
3. 脚本会自动完成授权并产出 **`.env`** 文件。

### 3. SET SECRETS
前往 GitHub `Settings > Secrets and variables > Actions`，对照 **`.env`** 填入内容。

---

## 🛠️ HOW IT WORKS

| 组件 | 角色 |
| :--- | :--- |
| **GitHub Actions** | 运算核心与自动化调度器 |
| **YouTube API** | 内容侦测与信息检索 |
| **NotebookLM** | 核心 AI 引擎（提供深度理解） |
| **Telegram Bot** | 您的私人互动入口 |

---

## ⚠️ RISK & LIMITATIONS

- **Non-official Protocol**: 本项目依赖模拟浏览器行为。若 Google 修改 NotebookLM 的网页结构，本项目可能需要更新。
- **Credential TTL**: Cookie 通常维持 **2 至 4 周**。失效时重新执行 `setup_helper.py` 即可。
- **100% Privacy**: 数据在 GitHub 隔离容器内处理，并直接发送给 Google。

---

## ❤️ ACKNOWLEDGEMENTS

本项目的核心认证与操作逻辑深受 **[notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)** 的启发与支持。

特别感谢作者 **[Jacob Ben-David](https://github.com/jacob-bd)** 开发了如此强大的 MCP 协议工具，让 AI 代理能以程序化方式操作 NotebookLM。

---

## 📜 LICENSE
MIT License. Developed by Michael.
