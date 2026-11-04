from __future__ import annotations


def move_selection(index: int, count: int, columns: int, direction: str) -> int:
    if count <= 0:
        return 0
    if not (0 <= index < count):
        raise ValueError("index out of range")
    if columns <= 0:
        raise ValueError("columns must be positive")
    if direction == "left":
        return (index - 1) % count
    if direction == "right":
        return (index + 1) % count
    if direction not in ("up", "down"):
        raise ValueError("unknown direction")
    row, column = divmod(index, columns)
    new_row = row + (-1 if direction == "up" else 1)
    total_rows = (count + columns - 1) // columns
    if new_row < 0 or new_row >= total_rows:
        return index
    first = new_row * columns
    last = min(count - 1, first + columns - 1)
    return min(first + column, last)
