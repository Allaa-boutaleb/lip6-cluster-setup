"""Read ~/.lip6/config.toml for user/cluster settings."""

import os
import re
from pathlib import Path


_CONFIG_PATH = Path.home() / ".lip6" / "config.toml"


def _parse_toml_simple(text: str) -> dict:
    """Minimal TOML parser (no dependencies) for flat sections."""
    result = {}
    current = result
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        m = re.match(r"^\[(.+)]$", line)
        if m:
            section = m.group(1).strip()
            result[section] = {}
            current = result[section]
            continue
        m = re.match(r'^(\w+)\s*=\s*"(.*)"\s*$', line)
        if m:
            current[m.group(1)] = m.group(2)
            continue
        m = re.match(r"^(\w+)\s*=\s*(true|false)\s*$", line, re.IGNORECASE)
        if m:
            current[m.group(1)] = m.group(2).lower() == "true"
            continue
        m = re.match(r"^(\w+)\s*=\s*(\d+)\s*$", line)
        if m:
            current[m.group(1)] = int(m.group(2))
            continue
    return result


class Config:
    """Cluster configuration loaded from ~/.lip6/config.toml."""

    def __init__(self):
        self.username: str = ""
        self.email: str = ""
        self.gateway: str = "ssh.lip6.fr"
        self.hpc_enabled: bool = True
        self.conv_enabled: bool = True
        self.hpc_storage: str = ""
        self._load()

    def _load(self):
        if not _CONFIG_PATH.exists():
            return
        data = _parse_toml_simple(_CONFIG_PATH.read_text())
        user = data.get("user", {})
        self.username = user.get("username", self.username)
        self.email = user.get("email", self.email)
        clusters = data.get("clusters", {})
        self.gateway = clusters.get("gateway", self.gateway)
        self.hpc_enabled = clusters.get("hpc_enabled", self.hpc_enabled)
        self.conv_enabled = clusters.get("conv_enabled", self.conv_enabled)
        self.hpc_storage = clusters.get("hpc_storage", self.hpc_storage)


def load_config() -> Config:
    return Config()
