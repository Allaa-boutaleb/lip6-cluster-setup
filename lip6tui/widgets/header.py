"""Branded header bar widget."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static


class ClusterHeader(Static):
    """A branded header showing cluster name, scheduler type, and username."""

    DEFAULT_CSS = """
    ClusterHeader {
        dock: top;
        height: 1;
        background: $primary;
        color: $text;
        text-style: bold;
        content-align: center middle;
        padding: 0 1;
    }
    """

    def __init__(self, cluster: str, scheduler: str, username: str) -> None:
        self.cluster = cluster
        self.scheduler = scheduler
        self.username = username
        super().__init__()

    def compose(self) -> ComposeResult:
        return []

    def on_mount(self) -> None:
        text = f" {self.cluster} | LIP6 Cluster Manager | {self.username} | {self.scheduler} "
        self.update(text)
