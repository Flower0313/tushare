from datetime import date, timedelta


def missing_ranges(
    start: date, end: date, covered: list[tuple[date, date]]
) -> list[tuple[date, date]]:
    """Return uncovered inclusive date ranges without persistence concerns."""
    cursor = start
    missing: list[tuple[date, date]] = []
    for range_start, range_end in sorted(covered):
        if range_end < cursor:
            continue
        if range_start > end:
            break
        if range_start > cursor:
            missing.append((cursor, min(end, range_start - timedelta(days=1))))
        cursor = max(cursor, range_end + timedelta(days=1))
        if cursor > end:
            break
    if cursor <= end:
        missing.append((cursor, end))
    return missing
