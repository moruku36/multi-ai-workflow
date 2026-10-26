from __future__ import annotations

from typing import Any


def process_records(items: list[dict[str, Any]]) -> list[Any]:
    return [item["value"] * 2 for item in items if item.get("active")]


def calculate_total(values: list[int | float]) -> int | float:
    return sum(values)
