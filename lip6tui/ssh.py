"""SSH subprocess execution layer — sync and async."""

import asyncio
import subprocess
from typing import Optional, Tuple


class SSHClient:
    """Execute commands on a remote host via the local ssh binary."""

    def __init__(self, host: str):
        self.host = host

    def run_sync(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """Run a command synchronously. Returns (stdout, stderr, returncode)."""
        try:
            proc = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=10", self.host, command],
                capture_output=True, text=True, timeout=timeout,
            )
            return proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired:
            return "", "SSH command timed out", 1
        except Exception as e:
            return "", str(e), 1

    async def run(self, command: str, timeout: int = 30) -> Tuple[str, str, int]:
        """Run a command asynchronously. Returns (stdout, stderr, returncode)."""
        try:
            proc = await asyncio.create_subprocess_exec(
                "ssh", "-o", "ConnectTimeout=10", self.host, command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            try:
                stdout_b, stderr_b = await asyncio.wait_for(
                    proc.communicate(), timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                return "", "SSH command timed out", 1
            return (
                stdout_b.decode(errors="replace"),
                stderr_b.decode(errors="replace"),
                proc.returncode or 0,
            )
        except Exception as e:
            return "", str(e), 1

    def start_tunnel(
        self,
        local_port: int,
        remote_host: str,
        remote_port: int,
        proxy_jump: Optional[str] = None,
    ) -> subprocess.Popen:
        """Start an SSH tunnel in the background. Returns the Popen handle."""
        cmd = ["ssh", "-N"]
        if proxy_jump:
            cmd += ["-J", proxy_jump]
        cmd += ["-L", f"{local_port}:localhost:{remote_port}", remote_host]
        return subprocess.Popen(
            cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
