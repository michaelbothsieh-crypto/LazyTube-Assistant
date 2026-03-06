# 🪟 Windows 使用者安裝指引

如果您是 Windows 使用者，請參考以下步驟完成環境設定。

## 1. 安裝 Python
1. 前往 [Python 官網](https://www.python.org/downloads/windows/) 下載最新穩定版。
2. **重要**：安裝時請務必勾選 **"Add Python to PATH"**。

## 2. 解決執行權限問題
Windows 預設禁止執行 Python 虛擬環境腳本。請以 **管理員身分** 開啟 PowerShell 並執行：
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 3. 執行設定助手
在專案目錄下，使用 PowerShell 執行以下指令：

```powershell
# 建立虛擬環境
python -m venv venv

# 啟動虛擬環境
.\venv\Scripts\activate

# 安裝依賴項
pip install google-auth-oauthlib requests

# 執行助手
python setup_helper.py
```

## 4. 常見問題
- **找不到 cookies.json**：請確保您已經依照主 README 的說明安裝了 `notebooklm-mcp-cli` 並執行過 `nlm login --force`。
- **路徑問題**：Windows 的憑證通常存放在 `%APPDATA%\notebooklm-mcp-cli`，`setup_helper.py` 會自動偵測，您不需要手動尋找。
