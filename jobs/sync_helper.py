"""
狀態同步小幫手（使用 StateSyncer 重構版）
"""
import sys
from pathlib import Path

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from jobs.state_sync import StateSyncer, _make_cli

_syncer = StateSyncer(
    file_map={
        "processed_videos.txt": ".sys_vid_storage_v1.txt",
        "last_check.txt": ".sys_time_marker_v1.txt",
        "subscriptions.json": ".sys_subs_config_v1.json",
    },
    tmp_prefix="tmp_state_git",
    empty_defaults={
        "processed_videos.txt": "",
        "last_check.txt": "",
        "subscriptions.json": "{}",
    },
)


def dl_state() -> bool:
    return _syncer.restore()


def up_state() -> bool:
    return _syncer.persist()


def main() -> None:
    _make_cli(_syncer)


if __name__ == "__main__":
    main()
