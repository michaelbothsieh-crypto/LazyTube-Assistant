import os
import sys

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from app.auth import AuthManager
from jobs.group_executor import execute_group


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: python on_demand_group.py <chat_id>")
        sys.exit(1)

    target_chat_id = str(sys.argv[1])
    AuthManager.deploy_credentials()
    execute_group(target_chat_id)


if __name__ == "__main__":
    main()
