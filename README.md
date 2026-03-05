# 🤖 LazyTube-Assistant

這是你的專案，它結合了 [notebooklm-mcp-cli](https://github.com/jacob-bd/notebooklm-mcp-cli)，讓你能夠每小時自動抓取 YouTube 訂閱頻道的最新影片，並透過 Google NotebookLM 產生摘要後推播至 LINE。

## 🌟 功能特點
- **自動偵測**：每小時自動檢查訂閱頻道的最新上傳。
- **AI 摘要**：利用 NotebookLM 的強大語義理解能力，產出 3-5 個核心重點。
- **即時通知**：摘要完成後，立即透過 LINE Notify 推送到你的手機。
- **全自動化**：完全執行於 GitHub Actions，無需自備伺服器。

## 快速開始

### 1. 安裝與設定

首先，確保你已經安裝了 Python 3.11 或更高版本。

```bash
# 進入子目錄
cd notebooklm-mcp-cli

# 建立並啟用虛擬環境
python3 -m venv venv
source venv/bin/activate

# 安裝依賴項目
pip install -e .
```

### 2. 登入 NotebookLM

在使用任何指令之前，你需要先登入以取得瀏覽器的 Cookie：

```bash
nlm login
```
這會開啟一個瀏覽器視窗，請在其中登入你的 Google 帳號。

### 3. 將 YouTube 影片新增至 NotebookLM

你可以使用以下指令將 YouTube 影片新增為來源：

```bash
# 建立一個新的 Notebook (如果尚未建立)
nlm notebook create "我的學習筆記"

# 新增 YouTube 影片網址
nlm source add "我的學習筆記" --url "https://www.youtube.com/watch?v=YOUR_VIDEO_ID"
```

## 常見問題

- **登入失敗**：請確保你的 Chrome 或其他支援的瀏覽器已安裝，且 `nlm login` 能正確抓取 Cookie。
- **影片不支援**：NotebookLM 主要抓取影片字幕，如果影片沒有字幕或禁止抓取，可能會失敗。
