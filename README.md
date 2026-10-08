# LIP6 Cluster Setup

One-command setup for passwordless SSH access and interactive job management on **LIP6 lab clusters** (Sorbonne University).

Supports both the **HPC cluster** (CPU, OAR scheduler) and the **Convergence cluster** (NVIDIA A100 GPUs, SLURM scheduler).

---

## Quick Start

```bash
git clone https://github.com/Allaa-boutaleb/lip6-cluster-setup.git
cd lip6-cluster-setup
chmod +x lip6-cluster-setup
./lip6-cluster-setup
```

The setup wizard walks you through everything interactively. You'll need:
- Your **LIP6 username** (the one you use to log in to lab machines)
- Your **LIP6 secure password** (wifi/workstation password, **not** your email password)

Runs on **macOS**, **Linux**, **Windows (Git Bash or WSL)** with the bash and `ssh` already there: no Python, nothing else to install.

> **Windows users:** either
> - install [Git for Windows](https://git-scm.com/download/win), open **Git Bash** and run the commands above (the browser opens with `start`; SSH connection sharing is off there, so each action logs in again), or
> - install [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) and run them from a WSL terminal (Ubuntu recommended; the browser opens with `wslview` or `explorer.exe`).

---

## What the Setup Does

The interactive wizard handles everything automatically:

| Step | What happens |
|------|-------------|
| **SSH key generation** | Creates an ed25519 key if you don't have one |
| **SSH config** | Sets up ProxyJump through the LIP6 gateway with `IdentitiesOnly yes` |
| **Key distribution** | Copies your public key to the gateway, HPC, and Convergence login nodes |
| **Manager scripts** | Copies `hpc-notebook` and `conv-manager` from this repo to `~/hpc-notebook` and `~/conv-manager`, filling in your email for job notifications |
| **Shell aliases** | Adds `hpc` and `conv` aliases to your shell (bash, zsh, or fish) |
| **Remote config** | Adds removable marked `.bashrc` blocks with helpful aliases |

After setup, you have two commands:

| Command | Cluster | Scheduler | Hardware |
|---------|---------|-----------|----------|
| `hpc` | HPC | OAR | Up to 48 cores, 128GB RAM |
| `conv` | Convergence | SLURM | A100 80GB / 40GB MIG GPUs |

Health and repair commands are available without rerunning the wizard:

```bash
./lip6-cluster-setup doctor
./lip6-cluster-setup doctor --remote
./lip6-cluster-setup repair-login
./lip6-cluster-setup uninstall --remote-blocks
```

---

## Convergence Manager (`conv`)

The GPU cluster manager for running deep learning workloads on NVIDIA A100 GPUs.

```
   _________  _   ____   __
  / ___/ __ \| | / / /  / /
 / /__/ /_/ /| |/ / /__/ /
 \___/\____/ |___/____/_/

  CONVERGENCE · LIP6 GPU Cockpit · Slurm · A100

  ok front reachable
  ok jobs: 2 running / 1 pending · tunnels: 1
  ok GPU status with option 4

  💡 The first neural network was built in 1958 by Frank Rosenblatt.

What do you want to do?

  1)  Start smart GPU session
  2)  Reconnect to running session
  3)  Jobs and logs
  4)  Cluster status
  5)  Cleanup jobs or tunnels
  6)  SSH into login node
  r)  Refresh cached status
  q)  Quit
```

### Launching a GPU Session

When you choose option **1**, you'll be guided through:

1. **GPU type** — Full A100 80GB (node01-06, best for large models) or MIG 40GB (node07-10, smaller jobs)
2. **GPU count** — How many GPUs (default: 1; 1-4 for full, 1-8 for MIG)
3. **Duration** — How long you need (default: 8 hours, max 14 days). The Slurm QoS follows from it: `short` up to 1 day, `normal` up to 7 days, `long` up to 14 days
4. **Job name** — A name for your job (default: `gpu-session`)
5. **CPU vendor** — Intel (`--constraint=intel`) or AMD (`--constraint=amd`, full A100 only)
6. **RAM size** — Optional Slurm `--mem` value such as `128G`, `512G`, `2048000M`, or `0`
7. **Exact node** — Optional `--nodelist=nodeXX`; press Enter to let Slurm choose
8. **Work mode:**
   - **Jupyter Lab** — Submits a batch job, waits for it to start, opens Jupyter in your browser
   - **Terminal only** — Interactive SSH session directly on a compute node (dies on disconnect)
   - **Both** — Jupyter Lab + shows you the SSH command for terminal access
   - **Custom script** — Submits your own batch script with GPU allocation

Exact node selection is guarded:
- Full A100 jobs accept `node01` through `node06`
- MIG jobs accept `node07` through `node10`
- The node must match the CPU vendor: `node01` is AMD, all others are Intel
- Press Enter to skip this and let Slurm choose

### Reconnecting to a Running Session

Option **2** lets you reconnect to a job that's already running. If you only have one active job, it auto-selects it. You can reconnect via Jupyter, Terminal, or Both.

### Cluster Status

Option **4** shows real-time GPU availability across all nodes — which GPUs are free, allocated, or down.

---

## HPC Manager (`hpc`)

The CPU cluster manager for running compute-heavy jobs on the OAR scheduler.

```
  __  ______  ______
 / / / / __ \/ ____/
/ /_/ / /_/ / /
\____/ .___/_/
    /_/

  HPC · LIP6 CPU Cockpit · OAR

  ok login reachable
  ok jobs: 1 active · tunnels: 0

  💡 Linux runs on 100% of the world's top 500 supercomputers.

What do you want to do?

  1)  Start CPU session
  2)  Reconnect to running session
  3)  Jobs and logs
  4)  Cleanup jobs or tunnels
  5)  SSH into login node
  r)  Refresh cached status
  q)  Quit
```

### Launching a Session

1. **Core count** — How many CPU cores (default: 24, 1-48)
2. **Duration** — How long you need (default: 24 hours; up to 1000 hours for Jupyter, 24 hours for a terminal session)
3. **Work mode:**
   - **Jupyter Lab** — Submits an OAR batch job, tunnels Jupyter to your browser
   - **Terminal only** — Interactive `oarsub -I` session
   - **Both** — Jupyter + terminal access via `oarsh`

---

## Key Features

### Background Tunnels

When you connect to a Jupyter session, the SSH tunnel runs **in the background**. This means:

- **Closing the terminal won't kill your connection** — Jupyter stays accessible
- **Ctrl+C won't break anything** — the tunnel persists independently
- You can keep using the same terminal for other things

Use the **Cleanup jobs or tunnels** menu option to see active tunnels and sever them when you're done. Open tunnels are remembered in `~/.local/state/lip6-cluster/tunnels`.

### Fast Actions

Each manager keeps one shared SSH connection per cluster for 10 minutes, so menu actions skip the login handshake (set `LIP6_NO_MUX=1` to turn this off). The menu shows at once while the first status check runs in the background, and a Jupyter launch is a single SSH call that streams the queue state until the URL is ready.

### Random Port Assignment

Each Jupyter session picks a **random port** (10000-60000) on the compute node, and the tunnel uses a free local port (20000-39999) on your machine. This prevents port conflicts when:

- Multiple users are running Jupyter on the same compute node
- You have other services running locally on common ports
- You're running multiple Jupyter sessions simultaneously

The port is automatically detected from Jupyter's logs — you never need to configure it manually. The browser opens `http://127.0.0.1:<port>`; if it cannot be opened (no display, SSH session), copy the printed URL.

### Log File Cleanup

When you cancel a job (option 5 in `conv`, option 4 in `hpc`), the corresponding `.out` and `.err` log files are **automatically deleted** from the cluster. No more accumulating junk files in your home directory.

### Fun Facts

Every time you open the manager, you get a random fun fact about computer science or AI. A small touch to brighten your day while waiting for GPUs.

### Friendly Duration Input

Both managers accept natural duration formats:

| Input | Meaning |
|-------|---------|
| `30m` | 30 minutes |
| `8h` | 8 hours |
| `3d` | 3 days |
| `3d 12h` | 3 days 12 hours |
| `1d 6h 30m` | 1 day 6 hours 30 minutes |
| `8:0:0`, `08:00:00` | 8 hours (H:M:S format) |
| `24` | 24 hours (bare number) |

### Enhanced Job Listings

Jobs are grouped by state with time tracking:

```
RUNNING
  JobID    Name                 Elapsed      TimeLimit    TimeLeft     Node
  ──────────────────────────────────────────────────────────────────────────────
  12345    gpu-session          2h 15m       08:00:00     5h 45m       node03

PENDING
  JobID    Name                 TimeLimit    Reason
  ──────────────────────────────────────────────────────────────
  12346    training             24:00:00     Resources
```

### Spinner & Loading Indicators

- The managers show compact status probes before the action menu
- Job wait loops print queue state while waiting
- SSH operations show `Loading, please wait...` so you know it's working
- Press **Ctrl+C** while waiting for a job: only the waiting stops. The job keeps running; reconnect later with option 2, or cancel it from **Cleanup** (option 5 in `conv`, 4 in `hpc`). If you gave the installer an email, the scheduler mails you about the job

### Login Safety

Remote `.bashrc` edits are installed as marked blocks:

```bash
# BEGIN LIP6 Convergence Cluster Aliases
# END LIP6 Convergence Cluster Aliases
```

The setup never installs persistent auto-SSH hooks from `.bashrc`. If login gets weird, use:

```bash
./lip6-cluster-setup doctor --remote
./lip6-cluster-setup repair-login
```

---

## Remote Aliases

The setup also installs aliases on the clusters. SSH in and use:

**On HPC:**
```bash
hpc-help        # Full reference of all aliases
hpc-conda       # Load conda + anaconda3
hpc-large       # 24-core interactive session
hpc-grab 48 24:0:0  # Custom core/time allocation
```

**On Convergence:**
```bash
conv-help       # Full reference of all aliases
conv-conda      # Load conda + anaconda3
conv-jobs       # Your running jobs
conv-status     # Cluster GPU usage
```

---

## Refreshing the Managers

If you've updated the repo (e.g. `git pull`), re-run the installer from the repo:

```bash
./lip6-cluster-setup
```

It copies the latest `conv-manager` and `hpc-notebook` over `~/conv-manager` and `~/hpc-notebook` and puts your email back in. Don't copy the files by hand: the repo versions have no email set, so job notifications would stop.

---

## Reset / Uninstall

```bash
./lip6-cluster-setup --reset
./lip6-cluster-setup uninstall --remote-blocks
```

`--reset` offers two options; `uninstall --remote-blocks` does only the remote part:

| Mode | What it removes |
|------|-----------------|
| **1) Local only** | `~/hpc-notebook`, `~/conv-manager`, `~/.ssh/config.d/lip6` and the `Include` line the setup added, the `hpc`/`conv` aliases |
| **2) Full reset** | The LIP6 alias blocks in `.bashrc` on HPC and Convergence (a copy is kept as `~/.bashrc.lip6-bak` there), then everything in Local only |
| **`uninstall --remote-blocks`** | Only the LIP6 alias blocks in the remote `.bashrc` files |

The setup also turns off conda's auto-activation of `base` on Convergence; undo with `conda config --set auto_activate_base true` there.

SSH keys are **never deleted** — they're safe to keep.

---

## Requirements

- macOS, Linux, or Windows (Git Bash or [WSL](https://learn.microsoft.com/en-us/windows/wsl/install)); bash 3.2 or newer
- `ssh` and `ssh-keygen` (pre-installed on macOS, Linux, WSL and Git Bash)
- A valid LIP6 account with cluster access

---

## Security

All user inputs are validated against strict patterns before being used in any command, preventing command injection via SSH.

| Input | Validation |
|-------|-----------|
| Job IDs | Numeric only |
| Core/GPU counts | Numeric, within the node's limits (1-48 cores; 1-4 full or 1-8 MIG GPUs) |
| Durations | Parsed through `parse_duration()`, only known formats accepted, capped at the cluster limit |
| Exact node | Must match the GPU type and CPU vendor |
| Job names | Alphanumeric, hyphens, underscores only |
| Script paths | Letters, digits, `.`, `_`, `~`, `/`, `-` only |

Additional security measures:
- SSH config uses `StrictHostKeyChecking accept-new` and `IdentitiesOnly yes`
- SSH keys generated without passphrase for convenience (a warning is shown with instructions to add one)
- Existing SSH config is preserved via `Include config.d/*` (never overwritten)
- Temp files created with `mktemp` to prevent race conditions

---

## File Structure

```
lip6-cluster-setup    # Main setup script (run this)
conv-manager          # Convergence GPU manager (installed to ~/ by setup)
hpc-notebook          # HPC CPU manager (installed to ~/ by setup)
README.md             # This file
LICENSE               # MIT license
```

---

## Disclaimer

This is an **unofficial**, community-made tool. It is **not** affiliated with, endorsed by, or maintained by LIP6, Sorbonne University, or CNRS.

- The scripts modify your SSH configuration, shell config files, and remote `.bashrc`. Backups are created before any modifications, but **use at your own risk**.
- The author is not responsible for any misconfiguration, data loss, or access issues resulting from the use of these scripts.
- Cluster policies, hostnames, and scheduler configurations may change without notice. If something breaks, check with your cluster administrators.
- **Never share your SSH private keys or passwords.** These scripts never store or transmit credentials — they only append your public key to `~/.ssh/authorized_keys` on each host, over `ssh`.

---

## License

MIT

## Author

**Allaa Boutaleb** — [allaa.boutaleb@lip6.fr](mailto:allaa.boutaleb@lip6.fr)
