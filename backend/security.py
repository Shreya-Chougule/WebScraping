
import json
import time
from collections import defaultdict
from typing import Any, Dict, List, Tuple


# In-memory sliding window rate limiter: (client_ip, bucket) -> [timestamps]
_rate_limit_records: Dict[Tuple[str, str], List[float]] = defaultdict(list)


def is_rate_limited(
    client_ip: str,
    bucket: str = "default",
    limit: int = 120,
    window_seconds: int = 60,
) -> bool:
    """Return True when the client has exceeded its sliding-window limit."""
    if limit <= 0 or window_seconds <= 0:
        return True

    now = time.time()
    cutoff = now - window_seconds
    key = (client_ip, bucket)

    timestamps = _rate_limit_records[key]
    _rate_limit_records[key] = [timestamp for timestamp in timestamps if timestamp > cutoff]

    if len(_rate_limit_records[key]) >= limit:
        return True

    _rate_limit_records[key].append(now)
    return False


def reset_rate_limits() -> None:
    """Reset rate limiter storage (primarily useful in tests)."""
    _rate_limit_records.clear()


def sanitize_csv_cell(value: Any) -> Any:
    """
    Mitigate spreadsheet formula injection.

    Checks past leading whitespace/control characters before deciding
    whether a string begins with a spreadsheet formula trigger.
    Preserves the original value after adding a protective apostrophe.
    """
    if value is None:
        return ""

    if isinstance(value, (list, dict)):
        value = json.dumps(value, ensure_ascii=False)

    if isinstance(value, str):
        probe = value.lstrip()

        starts_with_formula = probe.startswith(("=", "+", "-", "@"))
        starts_with_control = value.startswith(("\t", "\r", "\n"))

        if starts_with_formula or starts_with_control:
            return "'" + value

    return value


def escape_postgrest_search(value: str) -> str:
    """Escape characters that interfere with PostgREST filter parsing."""
    return value.replace("\\", "\\\\").replace('"', '\\"')
