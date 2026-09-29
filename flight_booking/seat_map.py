from math import ceil

SEAT_LETTERS = ("A", "B", "C", "D", "E")
PREMIUM_ROW_SHARE = 0.20


def row_count(total_seats: int) -> int:
    return max(1, ceil(max(total_seats, 1) / len(SEAT_LETTERS)))


def premium_start_row(total_seats: int) -> int:
    rows = row_count(total_seats)
    economy_rows = max(1, ceil(rows * (1 - PREMIUM_ROW_SHARE)))
    return min(rows + 1, economy_rows + 1)


def cabin_for_row(total_seats: int, row: int) -> str:
    return "Premium" if row >= premium_start_row(total_seats) else "Economy"
