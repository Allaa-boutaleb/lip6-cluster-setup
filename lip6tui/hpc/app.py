"""HPC Textual App — full TUI for OAR cluster management."""

from __future__ import annotations

import os
import re
import subprocess
import time
from pathlib import Path
from typing import Optional

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Vertical, Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import (
    Static,
    Footer,
    Input,
    Button,
    RadioButton,
    RadioSet,
    DataTable,
    LoadingIndicator,
    Label,
)

from ..config import load_config
from ..ssh import SSHClient
from ..duration import parse_to_minutes, minutes_to_hms, minutes_to_human
from ..validators import is_int, is_name, is_path
from ..widgets.header import ClusterHeader
from . import commands


# ---------------------------------------------------------------------------
# Launch Screen
# ---------------------------------------------------------------------------

class LaunchScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Back")]
    CSS_PATH = None

    def compose(self) -> ComposeResult:
        yield Static("Launch New Session", classes="form-title", id="launch-title")
        with Vertical(id="launch-container"):
            yield Static("Cores", classes="form-label")
            yield Input(value="24", placeholder="Number of cores", id="cores-input")
            yield Static("Duration", classes="form-label")
            yield Input(value="24h", placeholder="e.g. 8h, 3d, 1d 6h 30m", id="duration-input")
            yield Static("Work Mode", classes="form-label")
            yield RadioSet(
                RadioButton("Jupyter Lab + Terminal", value=True, id="mode-jupyter"),
                RadioButton("Terminal only (interactive)", id="mode-terminal"),
                RadioButton("Submit custom script", id="mode-custom"),
                id="mode-radio",
            )
            with Horizontal(classes="form-buttons"):
                yield Button("Submit", variant="primary", id="submit-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "submit-btn":
            self._submit()

    def _submit(self) -> None:
        cores_input = self.query_one("#cores-input", Input)
        duration_input = self.query_one("#duration-input", Input)
        cores = cores_input.value.strip()
        duration = duration_input.value.strip()

        if not is_int(cores):
            self.notify("Cores must be a number", severity="error")
            return
        minutes = parse_to_minutes(duration)
        if minutes is None:
            self.notify("Invalid duration (e.g. 8h, 3d, 1d 6h 30m)", severity="error")
            return

        radio = self.query_one("#mode-radio", RadioSet)
        idx = radio.pressed_index
        modes = ["jupyter", "terminal", "custom"]
        mode = modes[idx] if idx >= 0 else "jupyter"

        if mode == "custom":
            self.app.push_screen(CustomScriptScreen(int(cores), minutes_to_hms(minutes)))
            return

        self.app.pop_screen()
        self.app.launch_job(int(cores), minutes_to_hms(minutes), mode)


class CustomScriptScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, cores: int, walltime: str) -> None:
        super().__init__()
        self._cores = cores
        self._walltime = walltime

    def compose(self) -> ComposeResult:
        with Vertical(id="launch-container"):
            yield Static("Submit Custom Script", classes="form-title")
            yield Static("Script path on the cluster", classes="form-label")
            yield Input(placeholder="e.g. ~/train.sh", id="script-input")
            with Horizontal(classes="form-buttons"):
                yield Button("Submit", variant="primary", id="submit-btn")
                yield Button("Cancel", variant="default", id="cancel-btn")

    def action_cancel(self) -> None:
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "submit-btn":
            path = self.query_one("#script-input", Input).value.strip()
            if not path or not is_path(path):
                self.notify("Invalid script path", severity="error")
                return
            self.app.pop_screen()
            self.app.pop_screen()
            self.app.submit_custom(self._cores, self._walltime, path)


# ---------------------------------------------------------------------------
# Waiting Screen
# ---------------------------------------------------------------------------

class WaitingScreen(Screen):
    BINDINGS = [Binding("escape", "stop_waiting", "Stop Waiting")]

    def __init__(self, job_id: str) -> None:
        super().__init__()
        self._job_id = job_id
        self._start = time.time()

    def compose(self) -> ComposeResult:
        with Vertical(id="waiting-container"):
            yield Static("Waiting for Job to Start", classes="waiting-title")
            yield LoadingIndicator()
            yield Static(f"Job {self._job_id}", id="waiting-job-label")
            yield Static("PENDING", id="waiting-state", classes="waiting-status")
            yield Static("", id="waiting-elapsed")
            yield Static("Press Escape to stop waiting", classes="waiting-hint")

    def on_mount(self) -> None:
        self.set_interval(5.0, self._poll)
        self.set_interval(1.0, self._tick)

    def _tick(self) -> None:
        elapsed = int(time.time() - self._start)
        m, s = divmod(elapsed, 60)
        self.query_one("#waiting-elapsed", Static).update(f"Elapsed: {m}m {s}s")

    @work(exclusive=True)
    async def _poll(self) -> None:
        ssh = SSHClient("hpc")
        state = await commands.get_job_state(ssh, self._job_id)
        self.query_one("#waiting-state", Static).update(state or "PENDING")
        if state == "Running":
            self.app.pop_screen()
            self.app.on_job_running(self._job_id)
        elif state in ("Error", "Terminated"):
            self.app.pop_screen()
            self.app.notify(f"Job {self._job_id} failed: {state}", severity="error")

    def action_stop_waiting(self) -> None:
        self.app.pop_screen()
        self.app.notify(f"Job {self._job_id} still queued. Reconnect later.", severity="warning")


# ---------------------------------------------------------------------------
# Session Ready Screen
# ---------------------------------------------------------------------------

class SessionScreen(Screen):
    BINDINGS = [
        Binding("escape", "disconnect", "Disconnect"),
        Binding("o", "open_browser", "Open Browser"),
    ]

    def __init__(self, job_id: str, node: str, url: str, local_url: str, port: int) -> None:
        super().__init__()
        self._job_id = job_id
        self._node = node
        self._url = url
        self._local_url = local_url
        self._port = port
        self._tunnel: Optional[subprocess.Popen] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="session-container"):
            yield Static("Session Ready!", classes="session-title")
            yield Static(f"  Job:   {self._job_id}", classes="session-info")
            yield Static(f"  Node:  {self._node}", classes="session-info")
            yield Static(f"  URL:   {self._local_url}", classes="session-url")
            yield Static(
                f"  SSH:   ssh -t hpc \"OAR_JOB_ID={self._job_id} oarsh {self._node}\"",
                classes="session-ssh",
            )
            yield Static("Tunnel: connecting...", id="tunnel-label", classes="tunnel-status")
            with Horizontal(classes="form-buttons"):
                yield Button("Open in Browser", variant="primary", id="open-btn")
                yield Button("Disconnect", variant="warning", id="disconnect-btn")

    def on_mount(self) -> None:
        self._start_tunnel()

    def _start_tunnel(self) -> None:
        ssh = SSHClient("hpc")
        try:
            self._tunnel = ssh.start_tunnel(self._port, self._node, self._port)
            self.query_one("#tunnel-label", Static).update("Tunnel: ACTIVE")
        except Exception as e:
            self.query_one("#tunnel-label", Static).update(f"Tunnel: FAILED ({e})")

    def action_open_browser(self) -> None:
        self._open_url()

    def _open_url(self) -> None:
        try:
            if subprocess.run(["which", "xdg-open"], capture_output=True).returncode == 0:
                subprocess.Popen(["xdg-open", self._local_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif subprocess.run(["which", "open"], capture_output=True).returncode == 0:
                subprocess.Popen(["open", self._local_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def action_disconnect(self) -> None:
        self._cleanup()
        self.app.pop_screen()

    def _cleanup(self) -> None:
        if self._tunnel and self._tunnel.poll() is None:
            self._tunnel.terminate()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-btn":
            self._open_url()
        elif event.button.id == "disconnect-btn":
            self.action_disconnect()


# ---------------------------------------------------------------------------
# Main Dashboard / App
# ---------------------------------------------------------------------------

class HPCApp(App):
    """Interactive TUI for LIP6 HPC cluster (OAR)."""

    TITLE = "LIP6 HPC Manager"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("l", "launch", "Launch"),
        Binding("c", "connect", "Connect"),
        Binding("k", "kill", "Kill"),
        Binding("s", "ssh_login", "SSH"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config = load_config()
        self._ssh = SSHClient("hpc")
        self._jobs: list[commands.OARJob] = []

    def compose(self) -> ComposeResult:
        yield ClusterHeader("HPC", "OAR", self._config.username)
        with VerticalScroll(id="dashboard"):
            yield Static("RUNNING", classes="section-title-running", id="running-title")
            yield DataTable(id="running-table")
            yield Static("PENDING", classes="section-title-pending", id="pending-title")
            yield DataTable(id="pending-table")
            yield Static("", id="status-line", classes="empty-message")
        yield Footer()

    def on_mount(self) -> None:
        # Setup tables
        running_table = self.query_one("#running-table", DataTable)
        for col in ["ID", "Name", "Node", "Cores", "Elapsed", "Remaining"]:
            running_table.add_column(col, key=col)

        pending_table = self.query_one("#pending-table", DataTable)
        for col in ["ID", "Name", "Requested Time"]:
            pending_table.add_column(col, key=col)

        self.refresh_jobs()
        self.set_interval(30.0, self.refresh_jobs)

    @work(exclusive=True)
    async def refresh_jobs(self) -> None:
        status = self.query_one("#status-line", Static)
        status.update("Fetching jobs...")
        self._jobs = await commands.fetch_jobs(self._ssh, self._config.username)
        self._update_tables()
        if self._jobs:
            status.update(f"{len(self._jobs)} job(s) found")
        else:
            status.update("No jobs found")

    def _update_tables(self) -> None:
        running = [j for j in self._jobs if j.state == "Running"]
        pending = [j for j in self._jobs if j.state != "Running"]

        rt = self.query_one("#running-table", DataTable)
        rt.clear()
        for j in running:
            elapsed = minutes_to_human(j.elapsed_minutes) if j.elapsed_minutes is not None else "N/A"
            remaining = minutes_to_human(j.remaining_minutes) if j.remaining_minutes is not None else "N/A"
            rt.add_row(j.job_id, j.name[:20], j.node[:12], j.cores or "-", elapsed, remaining)

        pt = self.query_one("#pending-table", DataTable)
        pt.clear()
        for j in pending:
            pt.add_row(j.job_id, j.name[:20], j.walltime or "N/A")

    # -- Actions --

    def action_launch(self) -> None:
        self.push_screen(LaunchScreen())

    def action_connect(self) -> None:
        running = [j for j in self._jobs if j.state == "Running"]
        if not running:
            self.notify("No running jobs to connect to", severity="warning")
            return
        if len(running) == 1:
            self._connect_to(running[0].job_id)
        else:
            self.push_screen(JobPickerScreen(running, "connect"))

    def action_kill(self) -> None:
        if not self._jobs:
            self.notify("No jobs to cancel", severity="warning")
            return
        self.push_screen(JobPickerScreen(self._jobs, "kill"))

    def action_ssh_login(self) -> None:
        self.suspend()
        os.system("ssh hpc")
        self.resume()

    def action_refresh(self) -> None:
        self.refresh_jobs()

    # -- Job operations --

    @work(exclusive=True)
    async def launch_job(self, cores: int, walltime: str, mode: str) -> None:
        if mode == "terminal":
            self.suspend()
            os.system(
                f"ssh -t hpc \"oarsub -l /nodes=1/core={cores},walltime={walltime}"
                f" -p \\\"host like 'big%'\\\" -I\""
            )
            self.resume()
            self.refresh_jobs()
            return

        self.notify(f"Submitting job: {cores} cores, {walltime}...")
        job_id, error = await commands.submit_jupyter_job(
            self._ssh, cores, walltime, 8888, self._config.email
        )
        if error:
            self.notify(f"Submit failed: {error}", severity="error")
            return
        self.notify(f"Job {job_id} submitted!")
        self.push_screen(WaitingScreen(job_id))

    @work(exclusive=True)
    async def submit_custom(self, cores: int, walltime: str, script_path: str) -> None:
        self.notify(f"Submitting {script_path}...")
        job_id, error = await commands.submit_custom_job(
            self._ssh, cores, walltime, script_path
        )
        if error:
            self.notify(f"Submit failed: {error}", severity="error")
        else:
            self.notify(f"Job {job_id} submitted!")
        self.refresh_jobs()

    @work(exclusive=True)
    async def on_job_running(self, job_id: str) -> None:
        """Called when a waiting job transitions to Running."""
        self.notify(f"Job {job_id} is running! Connecting...")
        self._connect_to(job_id)

    @work(exclusive=True)
    async def _connect_to(self, job_id: str) -> None:
        node = await commands.get_job_node(self._ssh, job_id)
        if not node or not is_name(node):
            self.notify(f"Could not find node for job {job_id}", severity="error")
            return

        self.notify(f"Waiting for Jupyter on {node}...")
        url = ""
        for _ in range(30):
            url = await commands.get_jupyter_url(self._ssh, job_id)
            if url:
                break
            import asyncio
            await asyncio.sleep(2)

        if not url:
            self.notify("Jupyter didn't start. Check job logs.", severity="error")
            return

        port_match = re.search(r":(\d+)(?=/)", url)
        port = int(port_match.group(1)) if port_match else 8888
        local_url = re.sub(r"http://[^:]*:", f"http://localhost:", url, count=1)

        self.push_screen(SessionScreen(job_id, node, url, local_url, port))

    @work(exclusive=True)
    async def _kill_job(self, job_id: str) -> None:
        error = await commands.cancel_job(self._ssh, job_id)
        if error:
            self.notify(f"Cancel failed: {error}", severity="error")
        else:
            self.notify(f"Job {job_id} cancelled")
        self.refresh_jobs()

    @work(exclusive=True)
    async def _kill_all(self) -> None:
        error = await commands.cancel_all_jobs(self._ssh, self._config.username)
        if error:
            self.notify(f"Cancel failed: {error}", severity="error")
        else:
            self.notify("All jobs cancelled")
        self.refresh_jobs()


# ---------------------------------------------------------------------------
# Job Picker Screen (for connect / kill)
# ---------------------------------------------------------------------------

class JobPickerScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, jobs: list[commands.OARJob], action: str) -> None:
        super().__init__()
        self._jobs = jobs
        self._action = action

    def compose(self) -> ComposeResult:
        title = "Connect to Job" if self._action == "connect" else "Cancel Job"
        with Vertical(id="launch-container"):
            yield Static(title, classes="form-title")
            table = DataTable(id="picker-table")
            yield table
            if self._action == "kill":
                with Horizontal(classes="form-buttons"):
                    yield Button("Cancel All", variant="error", id="kill-all-btn")
                    yield Button("Back", variant="default", id="cancel-btn")
            else:
                with Horizontal(classes="form-buttons"):
                    yield Button("Back", variant="default", id="cancel-btn")

    def on_mount(self) -> None:
        table = self.query_one("#picker-table", DataTable)
        table.add_column("ID", key="ID")
        table.add_column("Name", key="Name")
        table.add_column("State", key="State")
        table.add_column("Node", key="Node")
        for j in self._jobs:
            table.add_row(j.job_id, j.name[:20], j.state, j.node[:12], key=j.job_id)
        table.cursor_type = "row"

    def on_data_table_row_selected(self, event: DataTable.RowSelected) -> None:
        job_id = str(event.row_key.value)
        self.app.pop_screen()
        if self._action == "connect":
            self.app._connect_to(job_id)
        else:
            self.app._kill_job(job_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel-btn":
            self.app.pop_screen()
        elif event.button.id == "kill-all-btn":
            self.app.pop_screen()
            self.app._kill_all()

    def action_cancel(self) -> None:
        self.app.pop_screen()


def main():
    app = HPCApp()
    app.run()


if __name__ == "__main__":
    main()
