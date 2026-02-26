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

> **Windows users:** This script requires a Unix shell. Install [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) (Windows Subsystem for Linux) and run the commands above from a WSL terminal (Ubuntu recommended).

---

## What the Setup Does

The interactive wizard handles everything automatically:

| Step | What happens |
|------|-------------|
| **SSH key generation** | Creates an ed25519 key if you don't have one |
| **SSH config** | Sets up ProxyJump through the LIP6 gateway with `IdentitiesOnly yes` |
| **Key distribution** | Copies your public key to the gateway, HPC, and Convergence login nodes |
| **Manager scripts** | Installs `~/hpc-notebook` and `~/conv-manager` on your local machine |
| **Shell aliases** | Adds `hpc` and `conv` aliases to your shell (bash, zsh, or fish) |
| **Remote config** | Configures `.bashrc` on the clusters with helpful aliases |

After setup, you have two commands:

| Command | Cluster | Scheduler | Hardware |
|---------|---------|-----------|----------|
| `hpc` | HPC | OAR | Up to 48 cores, 128GB RAM |
| `conv` | Convergence | SLURM | A100 80GB / 40GB MIG GPUs |

---

## Convergence Manager (`conv`)

The GPU cluster manager for running deep learning workloads on NVIDIA A100 GPUs.

```
╔══════════════════════════════════════════════════════╗
║  ██████╗ ██████╗ ███╗   ██╗██╗   ██╗               ║
║ ██╔════╝██╔═══██╗████╗  ██║██║   ██║               ║
║ ██║     ██║   ██║██╔██╗ ██║██║   ██║               ║
║ ██║     ██║   ██║██║╚██╗██║╚██╗ ██╔╝               ║
║ ╚██████╗╚██████╔╝██║ ╚████║ ╚████╔╝                ║
║  ╚═════╝ ╚═════╝ ╚═╝  ╚═══╝  ╚═══╝                ║
║   CONVERGENCE · LIP6 GPU Cluster Manager            ║
║   10 nodes | 40 x A100 80GB GPUs | SLURM            ║
╚══════════════════════════════════════════════════════╝

  💡 The first neural network was built in 1958 by Frank Rosenblatt.

What do you want to do?

  1)  Launch a new GPU session
  2)  Reconnect to a running session
  3)  View my jobs
  4)  Cancel jobs
  5)  Cluster status (GPUs, nodes)
  6)  SSH into login node
  7)  Disconnect tunnel
  q)  Quit
```

### Launching a GPU Session

When you choose option **1**, you'll be guided through:

1. **GPU type** — Full A100 80GB (node01-06, best for large models) or MIG 40GB (node07-10, smaller jobs)
2. **GPU count** — How many GPUs (default: 1, max 4 per node for full, 8 for MIG)
3. **Duration** — How long you need (default: 8 hours, max 15 days)
4. **Job name** — A name for your job (default: `gpu-session`)
5. **Work mode:**
   - **Jupyter Lab** — Submits a batch job, waits for it to start, opens Jupyter in your browser
   - **Terminal only** — Interactive SSH session directly on a compute node (dies on disconnect)
   - **Both** — Jupyter Lab + shows you the SSH command for terminal access
   - **Custom script** — Submits your own batch script with GPU allocation

### Reconnecting to a Running Session

Option **2** lets you reconnect to a job that's already running. If you only have one active job, it auto-selects it. You can reconnect via Jupyter, Terminal, or Both.

### Cluster Status

Option **5** shows real-time GPU availability across all nodes — which GPUs are free, allocated, or down.

---

## HPC Manager (`hpc`)

The CPU cluster manager for running compute-heavy jobs on the OAR scheduler.

```
╔══════════════════════════════════════════════╗
║  ██╗  ██╗██████╗  ██████╗                   ║
║  ██║  ██║██╔══██╗██╔════╝                   ║
║  ███████║██████╔╝██║                        ║
║  ██╔══██║██╔═══╝ ██║                        ║
║  ██║  ██║██║     ╚██████╗                   ║
║  ╚═╝  ╚═╝╚═╝      ╚═════╝                  ║
║   LIP6 HPC Cluster Manager                  ║
╚══════════════════════════════════════════════╝

  💡 Linux runs on 100% of the world's top 500 supercomputers.

What do you want to do?

  1)  Launch a new session
  2)  Reconnect to a running session
  3)  View my jobs
  4)  Cancel jobs
  5)  SSH into login node
  6)  Disconnect tunnel
  q)  Quit
```

### Launching a Session

1. **Core count** — How many CPU cores (default: 24)
2. **Duration** — How long you need (default: 24 hours)
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

Use the **Disconnect tunnel** menu option (option 7 on conv, option 6 on HPC) to see active tunnels and sever them when you're done.

### Random Port Assignment

Each Jupyter session picks a **random port** (10000-60000) on both the compute node and your local machine. This prevents port conflicts when:

- Multiple users are running Jupyter on the same compute node
- You have other services running locally on common ports
- You're running multiple Jupyter sessions simultaneously

The port is automatically detected from Jupyter's logs — you never need to configure it manually.

### Log File Cleanup

When you cancel a job (option 4), the corresponding `.out` and `.err` log files are **automatically deleted** from the cluster. No more accumulating junk files in your home directory.

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
| `8:0:0` | 8 hours (H:M:S format) |
| `24` | 24 hours (bare number) |

### Enhanced Job Listings

Jobs are grouped by state with time tracking:

```
RUNNING
  JobID    Name                 Elapsed      TimeLimit    TimeLeft     Node
  ────────────────────────────────────────────────────────────────────────────
  12345    gpu-session          2h 15m       08:00:00     5h 45m       node03

PENDING
  JobID    Name                 TimeLimit    Reason
  ──────────────────────────────────────────────────────────────
  12346    training             24:00:00     Resources
```

### Spinner & Loading Indicators

- The setup wizard shows `● Working...` → `✓ Done` on each step
- Job wait loops show a spinner: `⠹ PENDING — waiting for resources (45s)`
- SSH operations show `Loading, please wait...` so you know it's working
- Press **Ctrl+C** while waiting for a job to queue — you'll get an email when it starts and can reconnect later

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

If you've updated the repo (e.g. `git pull`) and want the latest scripts without re-running the full setup:

```bash
cp ~/lip6-cluster-setup/conv-manager ~/conv-manager
cp ~/lip6-cluster-setup/hpc-notebook ~/hpc-notebook
```

That's it — the `conv` and `hpc` aliases already point to these files.

---

## Reset / Uninstall

```bash
./lip6-cluster-setup --reset
```

Two options are offered:

| Mode | What it removes |
|------|-----------------|
| **Local only** | `~/hpc-notebook`, `~/conv-manager`, SSH config entries, shell aliases |
| **Full reset** | Everything above + restores `.bashrc` on HPC and Convergence from backup |

SSH keys are **never deleted** — they're safe to keep.

---

## Requirements

- macOS, Linux, or Windows (via [WSL](https://learn.microsoft.com/en-us/windows/wsl/install))
- `ssh`, `ssh-keygen`, `ssh-copy-id` (pre-installed on macOS/Linux/WSL)
- A valid LIP6 account with cluster access
- Python 3 (for local port detection)

---

## Security

All user inputs are validated against strict patterns before being used in any command, preventing command injection via SSH.

| Input | Validation |
|-------|-----------|
| Job IDs | Numeric only |
| Core/GPU counts | Numeric only |
| Durations | Parsed through `parse_duration()`, only known formats accepted |
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
- **Never share your SSH private keys or passwords.** These scripts never store or transmit credentials — they only use standard `ssh-copy-id` for key distribution.

---

## License

MIT

## Author

**Allaa Boutaleb** — [allaa.boutaleb@lip6.fr](mailto:allaa.boutaleb@lip6.fr)
