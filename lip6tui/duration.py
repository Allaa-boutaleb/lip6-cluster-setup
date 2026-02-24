"""Duration parsing — accepts human-friendly formats and outputs scheduler walltime strings."""

import re
from typing import Optional, Tuple


def parse_to_minutes(text: str) -> Optional[int]:
    """Parse a duration string into total minutes. Returns None on invalid input.

    Accepted formats:
        30m, 8h, 3d, 3d 12h, 1d 6h 30m
        H:M:S or HH:MM:SS (legacy)
        bare integer (treated as hours)
    """
    text = text.strip().lower()
    if not text:
        return None

    # Legacy H:M:S
    m = re.match(r"^(\d+):(\d+):(\d+)$", text)
    if m:
        h, mn, _ = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return h * 60 + mn

    total = 0
    matched = False
    for val, unit in re.findall(r"(\d+)\s*(d|h|m)", text):
        matched = True
        v = int(val)
        if unit == "d":
            total += v * 1440
        elif unit == "h":
            total += v * 60
        else:
            total += v
    if matched:
        return total

    # Bare number → hours
    if re.match(r"^\d+$", text):
        return int(text) * 60

    return None


def minutes_to_hms(total_minutes: int) -> str:
    """Convert minutes to H:M:S (OAR format)."""
    h = total_minutes // 60
    m = total_minutes % 60
    return f"{h}:{m}:0"


def minutes_to_slurm(total_minutes: int) -> str:
    """Convert minutes to SLURM time format (HH:MM:SS or D-HH:MM:SS)."""
    total_h = total_minutes // 60
    m = total_minutes % 60
    if total_h >= 24:
        d = total_h // 24
        rem_h = total_h % 24
        return f"{d}-{rem_h:02d}:{m:02d}:00"
    return f"{total_h:02d}:{m:02d}:00"


def minutes_to_human(total_minutes: int) -> str:
    """Convert minutes to a human-readable string like '2d 5h 30m'."""
    if total_minutes <= 0:
        return "0m"
    d = total_minutes // 1440
    h = (total_minutes % 1440) // 60
    m = total_minutes % 60
    parts = []
    if d:
        parts.append(f"{d}d")
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    return " ".join(parts) if parts else "0m"


def format_elapsed(seconds: int) -> str:
    """Format elapsed seconds into a readable string."""
    if seconds < 0:
        return "N/A"
    minutes = seconds // 60
    return minutes_to_human(minutes)
