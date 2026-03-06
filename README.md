# 🤖 LazyTube-Assistant

一個結合 **Google NotebookLM** 與 **YouTube API** 的全自動摘要工具。本專案透過 Vercel 接收 Telegram 指令，並驅動 GitHub Actions 進行高效的 AI 影片分析。

## 🌟 核心功能
- **🔍 自動偵測**：每小時檢查訂閱頻道的新影片。
- **🧠 隨選摘要**：透過 Telegram 指令 `/nlm <網址>` 立即產出重點。
- **🧹 自動清理**：摘要完成後自動刪除臨時環境，保護隱私且不佔空間。
- **📢 即時通知**：結果直接推播至您的 Telegram。

---

## 🛠️ 技術細節與開發坑洞紀錄

在本專案開發過程中，我們針對 `notebooklm-mcp-cli` (v0.4.0+) 進行了深度調校，以下是解決關鍵卡關問題的紀錄：

### 1. 憑證完整性 (CSRF Token 謎題)
- **問題**：單純匯入 `cookies.json` 會導致 `Parsed cookies don't appear to be valid`。
- **解決**：該工具需要 `metadata.json` 裡的 `csrf_token` 與 `session_id`。
- **關鍵發現**：執行官方指令 `nlm login --manual` 會自動過濾掉 CSRF Token。因此本專案改用「**先初始化目錄，再手動注入完整 JSON**」的調包計（Bait-and-Switch），確保認證 100% 成功。

### 2. 環境相容性 (Ubuntu vs Mac)
- **問題**：CLI 在不同系統下的路徑邏輯不一，且存在「路徑是資料夾而非檔案」的衝突（Errno 21）。
- **解決**：我們在 `main.py` 中實作了強大的路徑偵測，精確鎖定 `~/.notebooklm-mcp-cli/profiles/default/auth.json` 進行注入。

---

## ⚠️ 風險聲明與限制

使用本專案前請務必瞭解以下風險：

1. **非官方 API 風險**：本專案依賴模擬瀏覽器行為與 Google 通訊。一旦 Google 修改 NotebookLM 的網頁結構或通訊協議，本工具可能會立即失效，需等待 CLI 作者更新。
2. **Cookie 有效期**：憑證（NLM_COOKIE_BASE64）通常僅維持 **2 至 4 週**。若發生認證失敗，請參閱下方教學重新產生。
3. **YouTube API 配額**：YouTube Data API 每日有配額限制（10,000 點），過度頻繁的掃描可能會耗盡配額。
4. **隱私提醒**：本專案會將來源 URL 傳送至 Google NotebookLM 進行分析，請勿分析包含敏感個人資訊的內容。

---

## 🔑 憑證更新教學 (NLM_COOKIE_BASE64)

當摘要功能失效時，請執行以下步驟：

1. **重新登入**：在本地執行 `nlm login --force`。
2. **合併與轉換**：執行以下指令複製 22,060 字元以上的完整 Base64：
```bash
cd ~/.notebooklm-mcp-cli/profiles/default
python3 -c "
import json, base64
with open('cookies.json', 'r') as f: cookies = json.load(f)
with open('metadata.json', 'r') as f: meta = json.load(f)
meta['cookies'] = cookies
combined = json.dumps(meta)
print(base64.b64encode(combined.encode()).decode())
" | tr -d '\n' | pbcopy
```
3. **更新 Secret**：將內容貼到 GitHub `NLM_COOKIE_BASE64`。

---

## 🚀 GitHub Actions 指令手冊

- **`/nlm <網址> [指令]`**：手動摘要。
- **預設指令**：若未輸入 [指令]，機器人會自動要求「繁體中文 5 個核心重點」。
- **自動刪除**：任務完成後，機器人會自動刪除「處理中」的提示訊息，保持對話乾淨。

---
*Developed by Michael*
