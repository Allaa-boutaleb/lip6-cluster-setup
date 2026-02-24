"""DataTable-based job list widget (shared between HPC and Conv)."""

from __future__ import annotations

from typing import Any, List, Tuple

from textual.widgets import DataTable


class JobTable(DataTable):
    """A job list that can be populated with rows of job data."""

    DEFAULT_CSS = """
    JobTable {
        height: auto;
        max-height: 20;
        margin: 0 1;
    }
    """

    def __init__(self, columns: List[str], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._col_names = columns

    def on_mount(self) -> None:
        for col in self._col_names:
            self.add_column(col, key=col)

    def replace_data(self, rows: List[Tuple[str, ...]]) -> None:
        """Clear and repopulate with new rows."""
        self.clear()
        for row in rows:
            self.add_row(*row)
