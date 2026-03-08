import os
import sys
from app.notebook import NotebookService

def main():
    """
    /// 自動清理 NotebookLM 中遺留的暫存筆記本
    /// 清理對象：名稱開頭為 PROX_ 或 SLIDE_ 的筆記本
    """
    print("🧹 開始執行 NotebookLM 自動清理任務...")
    
    try:
        service = NotebookService()
        notebooks = service.list_notebooks()
        
        target_prefixes = ["PROX_", "SLIDE_"]
        deleted_count = 0
        
        for nb in notebooks:
            name = nb.get("title", "")
            nb_id = nb.get("notebookId")
            
            if any(name.startswith(prefix) for prefix in target_prefixes):
                print(f"🗑️ 正在刪除：{name} ({nb_id})")
                if service.delete_notebook(nb_id):
                    deleted_count += 1
                else:
                    print(f"⚠️ 刪除失敗：{name}")
                    
        print(f"✨ 清理完成，共刪除 {deleted_count} 個遺留筆記本。")
        
    except Exception as e:
        print(f"❌ 清理過程中發生異常: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
