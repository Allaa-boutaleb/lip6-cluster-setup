"""OAR command wrappers — parse oarstat, oarsub, oardel output."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from ..ssh import SSHClient


@dataclass
class OARJob:
    job_id: str = ""
    name: str = ""
    state: str = ""
    walltime: str = ""
    start_time: str = ""
    node: str = ""
    cores: str = ""

    @property
    def elapsed_minutes(self) -> Optional[int]:
        if not self.start_time:
            return None
        try:
            ts = int(self.start_time)
        except ValueError:
            return None
        if ts <= 0:
            return None
        return max(0, (int(time.time()) - ts) // 60)

    @property
    def wall_minutes(self) -> Optional[int]:
        if not self.walltime:
            return None
        parts = self.walltime.split(":")
        if len(parts) < 2:
            return None
        try:
            return int(parts[0]) * 60 + int(parts[1])
        except ValueError:
            return None

    @property
    def remaining_minutes(self) -> Optional[int]:
        e = self.elapsed_minutes
        w = self.wall_minutes
        if e is None or w is None:
            return None
        return max(0, w - e)


def parse_oarstat_full(text: str) -> List[OARJob]:
    """Parse oarstat -f output into a list of OARJob objects."""
    jobs: List[OARJob] = []
    current: Optional[OARJob] = None

    for line in text.splitlines():
        m = re.match(r"Job_Id\s*:\s*(\d+)", line)
        if m:
            if current and current.job_id:
                jobs.append(current)
            current = OARJob(job_id=m.group(1))
            continue
        if current is None:
            continue
        if "name =" in line:
            current.name = line.split("=", 1)[1].strip()
        elif "state =" in line:
            current.state = line.split("=", 1)[1].strip()
        elif "walltime =" in line:
            current.walltime = line.split("=", 1)[1].strip()
        elif "startTime =" in line:
            current.start_time = line.split("=", 1)[1].strip()
        elif "assigned_hostnames =" in line:
            current.node = line.split("=", 1)[1].strip()
        elif "wanted_resources =" in line:
            m2 = re.search(r"core=(\d+)", line)
            if m2:
                current.cores = m2.group(1)

    if current and current.job_id:
        jobs.append(current)
    return jobs


async def fetch_jobs(ssh: SSHClient, username: str) -> List[OARJob]:
    """Fetch all jobs for a user."""
    stdout, _, rc = await ssh.run(f"oarstat -u {username} -f 2>/dev/null")
    if rc != 0 or not stdout.strip():
        return []
    return parse_oarstat_full(stdout)


async def submit_jupyter_job(
    ssh: SSHClient, cores: int, walltime: str, port: int, email: str
) -> Tuple[str, str]:
    """Submit a Jupyter Lab OAR job. Returns (job_id, error_msg)."""
    script = f"""cat > ~/._jupyter_job.sh << 'JOBSCRIPT'
#!/bin/bash
#OAR -l {{host like 'big%'}}/nodes=1/core={cores},walltime={walltime}
#OAR --notify mail:{email}

source /etc/profile.d/modules.sh
module purge
module load python/anaconda3
eval "$(conda shell.bash hook)"

jupyter lab --ip=0.0.0.0 --no-browser --port={port}
JOBSCRIPT
chmod +x ~/._jupyter_job.sh
oarsub -S ~/._jupyter_job.sh 2>&1 | grep -oP 'OAR_JOB_ID=\\K[0-9]+'"""
    stdout, stderr, rc = await ssh.run(script, timeout=30)
    job_id = stdout.strip()
    if not job_id or not re.match(r"^\d+$", job_id):
        return "", stderr.strip() or "Failed to submit job"
    return job_id, ""


async def submit_custom_job(
    ssh: SSHClient, cores: int, walltime: str, script_path: str
) -> Tuple[str, str]:
    """Submit a custom OAR script. Returns (job_id, error_msg)."""
    cmd = (
        f"oarsub -l /nodes=1/core={cores},walltime={walltime} "
        f"-p \"host like 'big%'\" -S '{script_path}' 2>&1 "
        f"| grep -oP 'OAR_JOB_ID=\\K[0-9]+'"
    )
    stdout, stderr, rc = await ssh.run(cmd, timeout=30)
    job_id = stdout.strip()
    if not job_id or not re.match(r"^\d+$", job_id):
        return "", stderr.strip() or "Failed to submit job"
    return job_id, ""


async def cancel_job(ssh: SSHClient, job_id: str) -> str:
    """Cancel a single job. Returns error message or empty string."""
    _, stderr, rc = await ssh.run(f"oardel {job_id}")
    return stderr.strip() if rc != 0 else ""


async def cancel_all_jobs(ssh: SSHClient, username: str) -> str:
    """Cancel all jobs for a user."""
    cmd = (
        f"for jid in $(oarstat -u {username} 2>/dev/null | "
        f"awk '/^[0-9]/{{print $1}}'); do oardel $jid; done"
    )
    _, stderr, rc = await ssh.run(cmd, timeout=30)
    return stderr.strip() if rc != 0 else ""


async def get_job_node(ssh: SSHClient, job_id: str) -> str:
    """Get the assigned hostname for a running job."""
    stdout, _, _ = await ssh.run(
        f"oarstat -f -j {job_id} 2>/dev/null | grep 'assigned_hostnames' | awk '{{print $3}}'"
    )
    return stdout.strip()


async def get_jupyter_url(ssh: SSHClient, job_id: str) -> str:
    """Extract the Jupyter URL from job stderr logs."""
    stdout, _, _ = await ssh.run(
        f"grep -o 'http://[^ ]*' ~/OAR.{job_id}.stderr 2>/dev/null | tail -1"
    )
    return stdout.strip()


async def get_job_state(ssh: SSHClient, job_id: str) -> str:
    """Get current state of a job."""
    stdout, _, _ = await ssh.run(
        f"oarstat -f -j {job_id} 2>/dev/null | grep 'state =' | head -1 | awk -F= '{{print $2}}' | tr -d ' '"
    )
    return stdout.strip()
