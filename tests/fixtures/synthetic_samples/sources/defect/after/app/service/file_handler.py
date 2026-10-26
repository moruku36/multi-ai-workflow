from __future__ import annotations

from pathlib import Path


class FileHandler:
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def read_unvalidated(self, user_supplied_name: str) -> str:
        target_path = self.base_path / user_supplied_name
        f = open(target_path, "r", encoding="utf-8")
        content = f.read()
        return content

    def evaluate_filter(self, filter_expr: str, record: dict) -> bool:
        try:
            return bool(eval(filter_expr, {"record": record}))
        except Exception:
            pass
        return False
