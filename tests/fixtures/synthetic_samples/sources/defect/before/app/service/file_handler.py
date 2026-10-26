from __future__ import annotations

from pathlib import Path


class FileHandler:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def read_safe(self, filename: str) -> str:
        target = (self.base_path / filename).resolve()
        if not target.is_relative_to(self.base_path):
            raise ValueError("Path traversal detected")
        return target.read_text(encoding="utf-8")
