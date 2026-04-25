"""
jobs/podcast_sync_helper.py — Podcast 狀態同步（薄包裝）。

使用 state_sync.StateSyncer 實作，
避免與 sync_helper.py 重複相同邏輯。
"""
import sys
from pathlib import Path

# 確保 project root 在 path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from jobs.state_sync import StateSyncer, _make_cli

_syncer = StateSyncer(
    file_map={
        "processed_podcasts.json": ".sys_podcast_storage_v1.json",
    },
    tmp_prefix="tmp_podcast_state_git",
    empty_defaults={
        "processed_podcasts.json": '{"subscriptions": {}, "processed": {}}',
    },
)


def main() -> None:
    _make_cli(_syncer)


if __name__ == "__main__":
    main()
