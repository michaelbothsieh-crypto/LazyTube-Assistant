# 🤖 LazyTube-Assistant

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Zero Cost](https://img.shields.io/badge/Cost-0_Server_Required-brightgreen)](https://github.com/features/actions)
[![Actions Status](https://img.shields.io/badge/Actions-24/7_Ready-success)](https://github.com/michaelbothsieh-crypto/LazyTube-Assistant/actions)

**LazyTube-Assistant** 是一个实现“完全零成本”运营的智能视频摘要助理。利用 **GitHub Actions** 的免费计算资源，自动监控、分析并实时推送您感兴趣的内容。

> **🚀 项目主打：** 无需租用服务器、无需管理数据库、无需持续开机。只要 Fork 即可拥有 24/7 的 AI 摘要机器人。

---

## 🌐 语言
- [繁體中文](README.md)
- [简体中文](README.zh-cn.md)
- [English](README.en.md)

---

## ✨ 核心特色

- **💸 0 元运营成本**：完全依赖 GitHub Actions 免费额度，实现真正的零开销 AI 服务。
- **📦 免架设环境**：无需安装数据库或配置复杂的服务器环境，一切都在云端自动执行。
- **🧠 深度 AI 解析**：基于 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 串接 Google NotebookLM，产出最具逻辑的简体中文视频重点。
- **🎯 智能内容过滤**：自动识别游戏相关视频（如：PoE, Build 攻略），精确命中您的兴趣。
- **📢 多元触发模式**：
    - **自动模式 (默认)**：每小时自动扫描订阅。
    - **随选模式 (进阶)**：通过 Telegram Webhook 实现远程即时分析。

---

## 🚀 运作流程与 Actions 说明

当您在 GitHub 的 **Actions** 分页中查看时，会看到以下两个工作流：

### 1. YouTube 自动摘要 (`YouTube NotebookLM Summarizer`)
- **执行时间**：每小时自动执行一次，或您手动点击 `Run workflow`。
- **运作逻辑**：
    1. **认证环境布署**：自动将您的 `NLM_COOKIE_BASE64` 注入云端容器。
    2. **视频监控**：使用 YouTube API 扫描您订阅的频道。
    3. **智能过滤**：根据 `FILTER_KEYWORDS` 挑选出游戏或相关内容。
    4. **AI 摘要**：驱动 NotebookLM 产出简体中文摘要。
    5. **即时推送**：将结果发送至您的 Telegram。

### 2. 随选查询 (`NLM On-Demand Query`)
- **功能**：接受自定义网址与指令，即时产出单篇摘要并回传。

---

## 🛠️ 快速上手 (只需三步骤)

### 1. 点击 Fork
將本存储库 Fork 到您的个人账号下。

### 2. 取得凭证 (本地执行助手)
我们提供了一个全自动工具协助您完成认证：
1. 本地安装 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 并执行 `nlm login --force` 确保登录。
2. 执行配置助手：
   ```bash
   pip install google-auth-oauthlib requests
   python setup_helper.py
   ```
   脚本会自动完成 YouTube 授权并产出一个 **`.env`** 文件。*(Windows 用户请参阅 [Windows 指南](WINDOWS_GUIDE.md))*

### 3. 设置 GitHub Secrets
前往 GitHub `Settings > Secrets and variables > Actions`，对照 **`.env`** 文件将内容填入。

---

## 🏗️ 核心技术与风险说明

- **非官方通讯协议**：本项目基于 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli) 模拟浏览器行为。若 Google 修改网页结构，本工具可能需更新。
- **凭证时效**：Cookie 通常维持 2-4 周，失效时请重新执行助手脚本。
- **100% 隐私**：所有数据仅在 GitHub 的隔离环境处理，不经过第三方服务器。

---
*Developed by Michael*
