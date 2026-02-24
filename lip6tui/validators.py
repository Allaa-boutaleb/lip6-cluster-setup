"""Input validation helpers."""

import re


def is_int(value: str) -> bool:
    return bool(re.match(r"^\d+$", value.strip()))


def is_name(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.-]+$", value.strip()))


def is_path(value: str) -> bool:
    return bool(re.match(r"^[a-zA-Z0-9_.~/ -]+$", value.strip()))


def is_walltime(value: str) -> bool:
    return bool(re.match(r"^\d+:\d+:\d+$", value.strip()))
