"""GPU node grid widget (Convergence only)."""

from __future__ import annotations

from typing import List, Tuple

from textual.widgets import DataTable


class ClusterStatusTable(DataTable):
    """Node-by-node cluster status table with color-coded states."""

    DEFAULT_CSS = """
    ClusterStatusTable {
        height: auto;
        max-height: 24;
        margin: 0 1;
    }
    """

    COLUMNS = ["Node", "CPUs", "Memory", "GRES", "GRES Used", "State"]

    def on_mount(self) -> None:
        for col in self.COLUMNS:
            self.add_column(col, key=col)

    def replace_data(self, rows: List[Tuple[str, ...]]) -> None:
        self.clear()
        for row in rows:
            self.add_row(*row)
