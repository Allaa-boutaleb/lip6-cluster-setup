"""Job launch form widgets — shared base for HPC and Conv."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.containers import Vertical, Horizontal
from textual.widgets import Static, Input, Button, RadioButton, RadioSet
from textual.message import Message


class LaunchForm(Static):
    """Base launch form. Subclassed by HPC and Conv apps."""

    class Submitted(Message):
        """Posted when the user submits the form."""
        def __init__(self, data: dict) -> None:
            self.data = data
            super().__init__()

    class Cancelled(Message):
        """Posted when the user cancels."""

    DEFAULT_CSS = """
    LaunchForm {
        padding: 1 2;
        height: auto;
    }
    LaunchForm > Vertical {
        height: auto;
    }
    LaunchForm Input {
        margin: 0 0 1 0;
    }
    LaunchForm .form-label {
        margin: 0 0 0 0;
        text-style: bold;
    }
    LaunchForm RadioSet {
        margin: 0 0 1 0;
        height: auto;
    }
    LaunchForm .form-buttons {
        margin: 1 0 0 0;
        height: 3;
    }
    LaunchForm Button {
        margin: 0 1 0 0;
    }
    """
