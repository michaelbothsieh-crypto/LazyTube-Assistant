# 🤖 LAZYTUBE-ASSISTANT

> 🎉 **开发者告白！** 这是一个基于 **Google NotebookLM** 实现“完全零成本”运营的智能视频摘要助理。

**LazyTube-Assistant** 让你从此告别信息焦虑。利用 GitHub Actions 的免费资源，24/7 自动监控、分析并实时推送您感兴趣的内容精华。

---

## 🌐 语言选择 (Language)
[繁體中文](README.md) | [简体中文](README.zh-cn.md) | [English](README.en.md)

---

## ✨ 功能特色

- **💸 零运营成本**：完全依赖 GitHub Actions 免费额度，实现真正的零开销 AI 服务。
- **📦 免服务器架构**：无需管理数据库或复杂环境，只要 Fork 即可自动运行。
- **🧠 深度 AI 解析**：基于 Google NotebookLM，提供逻辑严密且具备上下文理解的摘要。
- **🎯 智能内容过滤**：自动识别感兴趣的内容（如：PoE 攻略、赛季更新），精确命中您的爱好。
- **🛡️ 安全隐私设计**：凭证仅在隔离容器中处理，数据直接发送至 Google，隐私无虞。

---

## 🚀 两种使用方式

### 1. 🤖 自动扫描模式 (默认)
每小时自动执行，扫描您的 YouTube 订阅列表，发现匹配关键字的视频后立即产出摘要。
> **最适合：** 追踪游戏赛季更新、技术教学、或任何您不想错过的定期动态。

### 2. 📱 随选摘要模式 (进阶)
通过 Telegram Webhook，直接将任何视频或网页网址贴给机器人，AI 会立即开始分析。
> **最适合：** 临时需要深入了解特定视频，但没时间看完。

---

## 📦 快速上手

### 1. 点击 Fork
点击本存储库右上角的 **Fork** 按钮，复制到您的个人账号。

### 2. 取得凭证 (全自动助手)
我们提供了一个跨平台工具来处理最麻烦的认证步骤：
1. 本地执行 `nlm login --force` 确保登录。
2. 执行设置助手：
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   *(Windows 用户？请参阅 [Windows 指南](WINDOWS_GUIDE.md))*
3. 脚本会自动完成授权并产出一个 **`.env`** 文件。

### 3. 设置 GitHub Secrets
前往 GitHub `Settings > Secrets and variables > Actions`，对照 **`.env`** 填入内容。

---

## 🛠️ 运作原理

| 组件 | 角色说明 |
| :--- | :--- |
| **GitHub Actions** | 运算核心与自动化调度器 |
| **YouTube API** | 内容侦測与信息检索 |
| **NotebookLM** | 核心 AI 引擎（提供深度理解与摘要） |
| **Telegram Bot** | 您的私人互动入口与结果接收端 |

---

## ⚠️ 风险声明与限制

- **非官方通讯协议**：本项目依赖模拟浏览器行为。若 Google 修改 NotebookLM 网页结构，本工具可能需更新。
- **凭证时效性**：Cookie 通常维持 **2 至 4 周**。失效时请重新执行 `setup_helper.py`。
- **100% 隐私保护**：所有数据皆在隔离环境处理并直接发送至 Google。

---

## ❤️ 特别鸣谢

本项目的核心认证与操作逻辑深受 **[notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)** 的启发与支持。

特别感谢作者 **[Jacob Ben-David](https://github.com/jacob-bd)** 开发了如此强大的 MCP 协议工具，让 AI 代理能以程序化方式操作 NotebookLM。

---

## 📜 授权协议
MIT License. Developed by Michael.
