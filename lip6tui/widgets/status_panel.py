"""Connection / tunnel status display widget."""

from textual.widgets import Static


class StatusPanel(Static):
    """Shows connection and tunnel status info."""

    DEFAULT_CSS = """
    StatusPanel {
        height: auto;
        margin: 1;
        padding: 1 2;
        border: round $primary;
    }
    """

    def set_info(self, lines: list[str]) -> None:
        self.update("\n".join(lines))
