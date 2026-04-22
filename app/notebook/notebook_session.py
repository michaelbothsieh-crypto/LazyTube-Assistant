from __future__ import annotations

import uuid
from contextlib import AbstractContextManager

from .parsing import extract_notebook_id
from .runner import NotebookRunner


class NotebookSession(AbstractContextManager):
    def __init__(self, runner: NotebookRunner, prefix: str):
        self.runner = runner
        self.prefix = prefix
        self.notebook_name = f"{prefix}_{uuid.uuid4().hex[:4].upper()}"
        self.notebook_id: str | None = None

    def __enter__(self) -> "NotebookSession":
        result = self.runner.run("notebook", "create", self.notebook_name)
        if result.returncode == 0:
            self.notebook_id = extract_notebook_id(result.stdout, self.notebook_name)
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self.notebook_id:
            self.runner.run("notebook", "delete", self.notebook_id, "--confirm", verbose=False)

    def ready(self) -> bool:
        return bool(self.notebook_id)
