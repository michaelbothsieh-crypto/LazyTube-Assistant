import sys
from app.auth import AuthManager
from app.config import Config
from app.summarizer_vm import SummarizerViewModel


def main():
    print("=" * 50)
    print("LazyTube-Assistant [YouTube Summarizer MVVM Refactored]")
    print("=" * 50)

    # 1. 驗證設定
    if not Config.validate():
        print("設定驗證失敗，請確認 GitHub Secrets 是否齊全。")
        sys.exit(1)

    # 2. 部署憑證 (Auth Model)
    if not AuthManager.deploy_credentials():
        print("憑證初始化失敗。")
        sys.exit(1)

    # 3. 執行業務邏輯 (ViewModel)
    vm = SummarizerViewModel()
    print(f"🕒 檢查區間：{vm.get_time_range_display()}")
    print(f"📦 已快取 ID 數：{len(vm.processed_ids)}")

    target_chat_id = sys.argv[1] if len(sys.argv) > 1 else None
    results = vm.run_sync(target_chat_id=target_chat_id)

    # 4. 顯示結果
    if results["success"] > 0 or results["skipped"] > 0:
        print(f"✨ 本輪總結：成功 {results['success']} 支、略過重複 {results['skipped']} 支、失敗 {results['failed']} 支。")
    else:
        print("🔚 無任何成功更新。")


if __name__ == "__main__":
    main()
