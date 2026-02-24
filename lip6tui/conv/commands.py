"""SLURM command wrappers — squeue, sbatch, scancel, sinfo parsing."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Tuple

from ..ssh import SSHClient


@dataclass
class SLURMJob:
    job_id: str = ""
    name: str = ""
    state: str = ""
    node: str = ""
    elapsed: str = ""
    time_limit: str = ""
    time_left: str = ""
    reason: str = ""


@dataclass
class NodeInfo:
    node: str = ""
    cpus_state: str = ""
    memory: str = ""
    alloc_mem: str = ""
    gres: str = ""
    gres_used: str = ""
    state: str = ""


async def fetch_jobs(ssh: SSHClient, username: str) -> List[SLURMJob]:
    """Fetch all jobs for a user via squeue."""
    stdout, _, rc = await ssh.run(
        f"squeue -u {username} -h -o '%i|%j|%T|%N|%M|%l|%L|%R' 2>/dev/null"
    )
    if rc != 0 or not stdout.strip():
        return []
    jobs = []
    for line in stdout.strip().splitlines():
        parts = line.strip().split("|")
        if len(parts) >= 8:
            jobs.append(SLURMJob(
                job_id=parts[0], name=parts[1], state=parts[2],
                node=parts[3], elapsed=parts[4], time_limit=parts[5],
                time_left=parts[6], reason=parts[7],
            ))
        elif len(parts) >= 4:
            jobs.append(SLURMJob(
                job_id=parts[0], name=parts[1], state=parts[2],
                node=parts[3] if len(parts) > 3 else "",
            ))
    return jobs


async def fetch_cluster_status(ssh: SSHClient) -> List[NodeInfo]:
    """Fetch node-level cluster status via sinfo."""
    stdout, _, rc = await ssh.run(
        "sinfo -p convergence --Node -O "
        "'nodelist:10,cpusstate:16,memory:10,allocmem:10,gres:35,gresused:35,statelong:12' 2>/dev/null"
    )
    if rc != 0 or not stdout.strip():
        return []
    nodes = []
    lines = stdout.strip().splitlines()
    for line in lines[1:]:  # skip header
        parts = line.split()
        if len(parts) >= 7:
            nodes.append(NodeInfo(
                node=parts[0], cpus_state=parts[1], memory=parts[2],
                alloc_mem=parts[3], gres=parts[4], gres_used=parts[5],
                state=parts[6],
            ))
    return nodes


async def submit_jupyter_job(
    ssh: SSHClient,
    gpu_type: str,
    num_gpus: int,
    walltime: str,
    port: int,
    job_name: str,
    email: str,
) -> Tuple[str, str]:
    """Submit a Jupyter Lab SLURM job. Returns (job_id, error_msg)."""
    script = f"""cat > ~/._conv_jupyter.sh << 'JOBSCRIPT'
#!/bin/bash
#SBATCH --job-name={job_name}
#SBATCH --nodes=1
#SBATCH --gpus-per-node={gpu_type}:{num_gpus}
#SBATCH --time={walltime}
#SBATCH --mail-type=ALL
#SBATCH --mail-user={email}
#SBATCH --output=%x-%j.out
#SBATCH --error=%x-%j.err

source /etc/profile.d/modules.sh
module purge
module load python/anaconda3
eval "$(conda shell.bash hook)"

jupyter lab --ip=0.0.0.0 --no-browser --port={port}
JOBSCRIPT
sbatch ~/._conv_jupyter.sh 2>&1 | grep -oP 'Submitted batch job \\K[0-9]+'"""
    stdout, stderr, rc = await ssh.run(script, timeout=30)
    job_id = stdout.strip()
    if not job_id or not re.match(r"^\d+$", job_id):
        return "", stderr.strip() or "Failed to submit job"
    return job_id, ""


async def submit_custom_job(
    ssh: SSHClient,
    gpu_type: str,
    num_gpus: int,
    walltime: str,
    job_name: str,
    email: str,
    script_path: str,
) -> Tuple[str, str]:
    """Submit a custom SLURM script. Returns (job_id, error_msg)."""
    cmd = (
        f"sbatch --job-name='{job_name}' --nodes=1 "
        f"--gpus-per-node='{gpu_type}:{num_gpus}' --time='{walltime}' "
        f"--mail-type=ALL --mail-user={email} "
        f"--output=%x-%j.out --error=%x-%j.err "
        f"'{script_path}' 2>&1 | grep -oP 'Submitted batch job \\K[0-9]+'"
    )
    stdout, stderr, rc = await ssh.run(cmd, timeout=30)
    job_id = stdout.strip()
    if not job_id or not re.match(r"^\d+$", job_id):
        return "", stderr.strip() or "Failed to submit job"
    return job_id, ""


async def cancel_job(ssh: SSHClient, job_id: str) -> str:
    _, stderr, rc = await ssh.run(f"scancel {job_id} 2>/dev/null")
    return stderr.strip() if rc != 0 else ""


async def cancel_all_jobs(ssh: SSHClient, username: str) -> str:
    _, stderr, rc = await ssh.run(f"scancel -u {username} 2>/dev/null")
    return stderr.strip() if rc != 0 else ""


async def get_job_state(ssh: SSHClient, job_id: str) -> str:
    stdout, _, _ = await ssh.run(f"squeue -j {job_id} -h -o '%T' 2>/dev/null")
    state = stdout.strip()
    if not state:
        # Try sacct for completed/failed jobs
        stdout2, _, _ = await ssh.run(
            f"sacct -j {job_id} --format=State -X --noheader 2>/dev/null | tr -d ' '"
        )
        state = stdout2.strip()
    return state


async def get_job_node(ssh: SSHClient, job_id: str) -> str:
    stdout, _, _ = await ssh.run(f"squeue -j {job_id} -h -o '%N' 2>/dev/null")
    return stdout.strip()


async def get_jupyter_url(ssh: SSHClient, job_id: str) -> str:
    stdout, _, _ = await ssh.run(
        f"grep -o 'http://[^ ]*' ~/*-{job_id}.err 2>/dev/null | tail -1"
    )
    return stdout.strip()
