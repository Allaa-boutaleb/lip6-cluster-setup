"""Conv Textual App — full TUI for SLURM/Convergence GPU cluster management."""

from __future__ import annotations

import os
import re
import subprocess
import time
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
)

from ..config import load_config
from ..ssh import SSHClient
from ..duration import parse_to_minutes, minutes_to_slurm
from ..validators import is_int, is_name, is_path
from ..widgets.header import ClusterHeader
from . import commands


GPU_TYPES = [
    ("a100_7g.80gb", "A100 80GB full (node01-06)"),
    ("a100_3g.40gb", "A100 40GB MIG (node07-10)"),
]


# ---------------------------------------------------------------------------
# Launch Screen
# ---------------------------------------------------------------------------

class LaunchScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def compose(self) -> ComposeResult:
        with Vertical(id="launch-container"):
            yield Static("Launch New GPU Session", classes="form-title")
            yield Static("GPU Type", classes="form-label")
            yield RadioSet(
                RadioButton(GPU_TYPES[0][1], value=True, id="gpu-full"),
                RadioButton(GPU_TYPES[1][1], id="gpu-mig"),
                id="gpu-radio",
            )
            yield Static("GPU Count", classes="form-label")
            yield Input(value="1", placeholder="1-4 for full, 1-8 for MIG", id="gpu-count-input")
            yield Static("Duration", classes="form-label")
            yield Input(value="8h", placeholder="e.g. 8h, 3d, 1d 6h 30m", id="duration-input")
            yield Static("Job Name", classes="form-label")
            yield Input(value="gpu-session", placeholder="Alphanumeric, hyphens, underscores", id="name-input")
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
        gpu_radio = self.query_one("#gpu-radio", RadioSet)
        gpu_idx = gpu_radio.pressed_index
        gpu_type = GPU_TYPES[gpu_idx][0] if 0 <= gpu_idx < len(GPU_TYPES) else GPU_TYPES[0][0]

        gpu_count = self.query_one("#gpu-count-input", Input).value.strip()
        duration = self.query_one("#duration-input", Input).value.strip()
        job_name = self.query_one("#name-input", Input).value.strip()

        if not is_int(gpu_count):
            self.notify("GPU count must be a number", severity="error")
            return
        minutes = parse_to_minutes(duration)
        if minutes is None:
            self.notify("Invalid duration (e.g. 8h, 3d, 1d 6h 30m)", severity="error")
            return
        if not is_name(job_name):
            self.notify("Invalid job name", severity="error")
            return

        mode_radio = self.query_one("#mode-radio", RadioSet)
        mode_idx = mode_radio.pressed_index
        modes = ["jupyter", "terminal", "custom"]
        mode = modes[mode_idx] if mode_idx >= 0 else "jupyter"

        walltime = minutes_to_slurm(minutes)

        if mode == "custom":
            self.app.push_screen(
                CustomScriptScreen(gpu_type, int(gpu_count), walltime, job_name)
            )
            return

        self.app.pop_screen()
        self.app.launch_job(gpu_type, int(gpu_count), walltime, job_name, mode)


class CustomScriptScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, gpu_type: str, num_gpus: int, walltime: str, job_name: str) -> None:
        super().__init__()
        self._gpu_type = gpu_type
        self._num_gpus = num_gpus
        self._walltime = walltime
        self._job_name = job_name

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
            self.app.submit_custom(
                self._gpu_type, self._num_gpus, self._walltime,
                self._job_name, path,
            )


# ---------------------------------------------------------------------------
# Waiting Screen
# ---------------------------------------------------------------------------

class WaitingScreen(Screen):
    BINDINGS = [Binding("escape", "stop_waiting", "Stop Waiting")]

    def __init__(self, job_id: str, job_name: str) -> None:
        super().__init__()
        self._job_id = job_id
        self._job_name = job_name
        self._start = time.time()

    def compose(self) -> ComposeResult:
        with Vertical(id="waiting-container"):
            yield Static("Waiting for Job to Start", classes="waiting-title")
            yield LoadingIndicator()
            yield Static(f"Job {self._job_id} ({self._job_name})", id="waiting-job-label")
            yield Static("PENDING", id="waiting-state", classes="waiting-status")
            yield Static("", id="waiting-elapsed")
            yield Static("GPU queue can take minutes to hours", classes="waiting-hint")
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
        ssh = SSHClient("conv")
        state = await commands.get_job_state(ssh, self._job_id)
        self.query_one("#waiting-state", Static).update(state or "PENDING")
        if state == "RUNNING":
            self.app.pop_screen()
            self.app.on_job_running(self._job_id, self._job_name)
        elif state in ("FAILED", "CANCELLED", "TIMEOUT"):
            self.app.pop_screen()
            self.app.notify(f"Job {self._job_id} failed: {state}", severity="error")

    def action_stop_waiting(self) -> None:
        self.app.pop_screen()
        self.app.notify(
            f"Job {self._job_id} still queued. Reconnect later.",
            severity="warning",
        )


# ---------------------------------------------------------------------------
# Session Ready Screen
# ---------------------------------------------------------------------------

class SessionScreen(Screen):
    BINDINGS = [
        Binding("escape", "disconnect", "Disconnect"),
        Binding("o", "open_browser", "Open Browser"),
    ]

    def __init__(
        self, job_id: str, node: str, url: str, local_url: str, port: int
    ) -> None:
        super().__init__()
        self._job_id = job_id
        self._node = node
        self._url = url
        self._local_url = local_url
        self._port = port
        self._tunnel: Optional[subprocess.Popen] = None

    def compose(self) -> ComposeResult:
        with Vertical(id="session-container"):
            yield Static("GPU Session Ready!", classes="session-title")
            yield Static(f"  Job:   {self._job_id}", classes="session-info")
            yield Static(f"  Node:  {self._node}", classes="session-info")
            yield Static(f"  Port:  {self._port}", classes="session-info")
            yield Static(f"  URL:   {self._local_url}", classes="session-url")
            yield Static(
                f"  SSH:   ssh -t -J conv {self._node}.convergence.lip6.fr",
                classes="session-ssh",
            )
            yield Static("Tunnel: connecting...", id="tunnel-label", classes="tunnel-status")
            with Horizontal(classes="form-buttons"):
                yield Button("Open in Browser", variant="primary", id="open-btn")
                yield Button("Disconnect", variant="warning", id="disconnect-btn")

    def on_mount(self) -> None:
        self._start_tunnel()

    def _start_tunnel(self) -> None:
        try:
            self._tunnel = subprocess.Popen(
                [
                    "ssh", "-N", "-J", "conv",
                    "-L", f"{self._port}:localhost:{self._port}",
                    f"{self._node}.convergence.lip6.fr",
                ],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
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
        if self._tunnel and self._tunnel.poll() is None:
            self._tunnel.terminate()
        self.app.pop_screen()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "open-btn":
            self._open_url()
        elif event.button.id == "disconnect-btn":
            self.action_disconnect()


# ---------------------------------------------------------------------------
# Cluster Status Screen
# ---------------------------------------------------------------------------

class ClusterStatusScreen(Screen):
    BINDINGS = [
        Binding("escape", "back", "Back"),
        Binding("r", "refresh_status", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        with VerticalScroll(id="cluster-status-container"):
            yield Static("Convergence Cluster Status", classes="form-title")
            yield DataTable(id="node-table")
            yield Static("", id="status-summary", classes="empty-message")

    def on_mount(self) -> None:
        table = self.query_one("#node-table", DataTable)
        for col in ["Node", "CPUs", "Memory", "AllocMem", "GRES", "GRES Used", "State"]:
            table.add_column(col, key=col)
        self._load_status()

    @work(exclusive=True)
    async def _load_status(self) -> None:
        ssh = SSHClient("conv")
        self.query_one("#status-summary", Static).update("Fetching cluster status...")
        nodes = await commands.fetch_cluster_status(ssh)
        table = self.query_one("#node-table", DataTable)
        table.clear()
        for n in nodes:
            table.add_row(n.node, n.cpus_state, n.memory, n.alloc_mem, n.gres, n.gres_used, n.state)
        total = len(nodes)
        idle = sum(1 for n in nodes if "idle" in n.state.lower())
        mixed = sum(1 for n in nodes if "mix" in n.state.lower())
        alloc = sum(1 for n in nodes if "alloc" in n.state.lower() and "mix" not in n.state.lower())
        down = sum(1 for n in nodes if "down" in n.state.lower() or "drain" in n.state.lower())
        self.query_one("#status-summary", Static).update(
            f"{total} nodes: {idle} idle, {mixed} mixed, {alloc} allocated, {down} down/drain"
        )

    def action_back(self) -> None:
        self.app.pop_screen()

    def action_refresh_status(self) -> None:
        self._load_status()


# ---------------------------------------------------------------------------
# Job Picker Screen
# ---------------------------------------------------------------------------

class JobPickerScreen(Screen):
    BINDINGS = [Binding("escape", "cancel", "Back")]

    def __init__(self, jobs: list[commands.SLURMJob], action: str) -> None:
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
        job = next((j for j in self._jobs if j.job_id == job_id), None)
        self.app.pop_screen()
        if self._action == "connect":
            self.app._connect_to(job_id, job.name if job else "gpu-session")
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


# ---------------------------------------------------------------------------
# Main App
# ---------------------------------------------------------------------------

class ConvApp(App):
    """Interactive TUI for LIP6 Convergence GPU cluster (SLURM)."""

    TITLE = "LIP6 Convergence Manager"
    CSS_PATH = "app.tcss"

    BINDINGS = [
        Binding("l", "launch", "Launch"),
        Binding("c", "connect", "Connect"),
        Binding("k", "kill", "Kill"),
        Binding("g", "gpu_status", "GPU Status"),
        Binding("s", "ssh_login", "SSH"),
        Binding("r", "refresh", "Refresh"),
        Binding("q", "quit", "Quit"),
    ]

    def __init__(self) -> None:
        super().__init__()
        self._config = load_config()
        self._ssh = SSHClient("conv")
        self._jobs: list[commands.SLURMJob] = []

    def compose(self) -> ComposeResult:
        yield ClusterHeader("CONV", "SLURM", self._config.username)
        with VerticalScroll(id="dashboard"):
            yield Static("RUNNING", classes="section-title-running", id="running-title")
            yield DataTable(id="running-table")
            yield Static("PENDING", classes="section-title-pending", id="pending-title")
            yield DataTable(id="pending-table")
            yield Static("", id="status-line", classes="empty-message")
        yield Footer()

    def on_mount(self) -> None:
        rt = self.query_one("#running-table", DataTable)
        for col in ["ID", "Name", "Node", "Elapsed", "Time Limit", "Time Left"]:
            rt.add_column(col, key=col)

        pt = self.query_one("#pending-table", DataTable)
        for col in ["ID", "Name", "Time Limit", "Reason"]:
            pt.add_column(col, key=col)

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
        running = [j for j in self._jobs if j.state == "RUNNING"]
        pending = [j for j in self._jobs if j.state != "RUNNING"]

        rt = self.query_one("#running-table", DataTable)
        rt.clear()
        for j in running:
            rt.add_row(j.job_id, j.name[:20], j.node[:12], j.elapsed, j.time_limit, j.time_left)

        pt = self.query_one("#pending-table", DataTable)
        pt.clear()
        for j in pending:
            pt.add_row(j.job_id, j.name[:20], j.time_limit, j.reason[:20])

    # -- Actions --

    def action_launch(self) -> None:
        self.push_screen(LaunchScreen())

    def action_connect(self) -> None:
        running = [j for j in self._jobs if j.state == "RUNNING"]
        if not running:
            self.notify("No running jobs to connect to", severity="warning")
            return
        if len(running) == 1:
            self._connect_to(running[0].job_id, running[0].name)
        else:
            self.push_screen(JobPickerScreen(running, "connect"))

    def action_kill(self) -> None:
        if not self._jobs:
            self.notify("No jobs to cancel", severity="warning")
            return
        self.push_screen(JobPickerScreen(self._jobs, "kill"))

    def action_gpu_status(self) -> None:
        self.push_screen(ClusterStatusScreen())

    def action_ssh_login(self) -> None:
        self.suspend()
        os.system("ssh conv")
        self.resume()

    def action_refresh(self) -> None:
        self.refresh_jobs()

    # -- Job operations --

    @work(exclusive=True)
    async def launch_job(
        self, gpu_type: str, num_gpus: int, walltime: str, job_name: str, mode: str
    ) -> None:
        if mode == "terminal":
            self.suspend()
            os.system(
                f"ssh -t conv \"salloc --job-name='{job_name}' --nodes=1 "
                f"--gpus-per-node='{gpu_type}:{num_gpus}' --time='{walltime}'\""
            )
            self.resume()
            self.refresh_jobs()
            return

        self.notify(f"Submitting {num_gpus}x {gpu_type}, {walltime}...")
        job_id, error = await commands.submit_jupyter_job(
            self._ssh, gpu_type, num_gpus, walltime, 9888,
            job_name, self._config.email,
        )
        if error:
            self.notify(f"Submit failed: {error}", severity="error")
            return
        self.notify(f"Job {job_id} submitted!")
        self.push_screen(WaitingScreen(job_id, job_name))

    @work(exclusive=True)
    async def submit_custom(
        self, gpu_type: str, num_gpus: int, walltime: str,
        job_name: str, script_path: str,
    ) -> None:
        self.notify(f"Submitting {script_path}...")
        job_id, error = await commands.submit_custom_job(
            self._ssh, gpu_type, num_gpus, walltime,
            job_name, self._config.email, script_path,
        )
        if error:
            self.notify(f"Submit failed: {error}", severity="error")
        else:
            self.notify(f"Job {job_id} submitted!")
        self.refresh_jobs()

    @work(exclusive=True)
    async def on_job_running(self, job_id: str, job_name: str) -> None:
        self.notify(f"Job {job_id} is running! Connecting...")
        self._connect_to(job_id, job_name)

    @work(exclusive=True)
    async def _connect_to(self, job_id: str, job_name: str = "gpu-session") -> None:
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
        port = int(port_match.group(1)) if port_match else 9888
        local_url = re.sub(r"http://[^:]*:", "http://localhost:", url, count=1)

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


def main():
    app = ConvApp()
    app.run()


if __name__ == "__main__":
    main()
