# LIP6 Cluster Setup

One-command setup for passwordless SSH access and interactive job management on **LIP6 lab clusters** (Sorbonne University).

Supports both the **HPC cluster** (CPU, OAR scheduler) and the **Convergence cluster** (NVIDIA A100 GPUs, SLURM scheduler).

## Getting started

```bash
git clone https://github.com/Allaa-boutaleb/lip6-cluster-setup.git
cd lip6-cluster-setup
chmod +x lip6-cluster-setup
./lip6-cluster-setup
```

> **Windows users:** This script requires a Unix shell. Install [WSL](https://learn.microsoft.com/en-us/windows/wsl/install) (Windows Subsystem for Linux) and run the commands above from a WSL terminal (Ubuntu recommended).

## What it does

The setup wizard will:

1. **Generate an SSH key** (ed25519) if you don't have one
2. **Configure passwordless SSH** through the LIP6 gateway with ProxyJump and `IdentitiesOnly yes`
3. **Copy keys** to all servers (gateway, HPC, Convergence, compute nodes)
4. **Install manager scripts** (`hpc` and `conv`) on your local machine
5. **Add aliases** to your shell (bash, zsh, or fish)
6. **Configure remote `.bashrc`** with cluster-specific aliases and helpers

After setup, you get two interactive managers:

| Command | Cluster | What it manages |
|---------|---------|-----------------|
| `hpc` | HPC (OAR) | CPU jobs — up to 48 cores, 128GB RAM |
| `conv` | Convergence (SLURM) | GPU jobs — A100 80GB / 40GB MIG |

## Manager features

Both managers provide an interactive menu with **0) Back/Exit** navigation at every level:

- **Launch sessions** — Jupyter Lab + Terminal (recommended), Terminal only, or custom script
- **Reconnect** to running sessions (auto-selects if only one job)
- **View jobs** with time tracking (elapsed, remaining, grouped by state)
- **Cancel jobs** (individual or all)
- **SSH tunnel** setup for Jupyter with automatic browser opening
- **Jupyter auto-install** — checks if Jupyter is available before submitting, installs if missing

### HPC Manager (`hpc`)

```
================================================
         LIP6 HPC Cluster Manager
    boutalebm - allaa.boutaleb@lip6.fr
================================================

What do you want to do?

  1)  Launch a new session
  2)  Reconnect to a running session
  3)  View my jobs
  4)  Cancel jobs
  5)  SSH into login node
  0)  Exit
```

Work modes:
- **Jupyter Lab + Terminal** (recommended) — submits batch job, waits with spinner, tunnels, opens browser, shows SSH command for terminal access
- **Terminal only** — runs `oarsub -I` directly for an interactive shell on a compute node
- **Submit a custom script** — runs your own OAR batch script with `oarsub -S`

### Convergence Manager (`conv`)

```
================================================
     LIP6 Convergence GPU Cluster Manager
    boutalebm - allaa.boutaleb@lip6.fr
================================================

  10 nodes | 40 x A100 80GB GPUs | SLURM

What do you want to do?

  1)  Launch a new GPU session
  2)  Reconnect to a running session
  3)  View my jobs
  4)  Cancel jobs
  5)  Cluster status (GPUs, nodes)
  6)  SSH into login node
  0)  Exit
```

Additional features:
- **GPU type picker** — full A100 80GB (node01-06) or MIG 40GB (node07-10)
- **Multi-GPU** support (up to 4 per node)
- **Custom script submission** with GPU allocation
- **Automatic port detection** from Jupyter logs (handles port conflicts)

### Friendly duration input

Both managers accept natural duration formats instead of requiring `H:M:S`:

| Input | Meaning |
|-------|---------|
| `30m` | 30 minutes |
| `8h` | 8 hours |
| `3d` | 3 days |
| `3d 12h` | 3 days 12 hours |
| `1d 6h 30m` | 1 day 6 hours 30 minutes |
| `8:0:0` | 8 hours (legacy H:M:S) |
| `24` | 24 hours (bare number) |

Warnings are shown when exceeding typical limits (24h interactive for HPC, 1000h batch for HPC, 15 days for Convergence).

### Enhanced job listings

Jobs are grouped by state with time tracking:

**HPC** — parses `oarstat -f` to compute elapsed and remaining time:
```
RUNNING
  ID         Name            Node       Elapsed      Remaining
  ──────────────────────────────────────────────────────────────
  1234       jupyter         big12      2h 15m       5h 45m

PENDING
  ID         Name            Requested Time
  ──────────────────────────────────────────
  1235       training        24:0:0
```

**Convergence** — uses rich `squeue` format with TimeUsed, TimeLimit, TimeLeft fields.

### In-place status updates

The setup wizard and both managers use in-place terminal updates instead of scrolling output:

- Setup steps show `● Working...` → `✓ Done` on a single line
- Pending job loops show a spinner: `⠹ PENDING — waiting for resources (45s) — Ctrl+C to stop waiting`
- Press **Ctrl+C** while waiting to stop — a message explains you'll get an email when the job starts and can reconnect later

## Remote aliases

The setup also installs aliases on the clusters themselves. SSH in and type:

```bash
# On HPC
hpc-help        # Full reference
hpc-conda       # Load conda + anaconda3
hpc-large       # 24-core interactive session
hpc-grab 48 24:0:0  # Custom allocation

# On Convergence
conv-help       # Full reference
conv-conda      # Load conda + anaconda3
conv-jobs       # Your running jobs
conv-status     # Cluster GPU usage
```

## Requirements

- macOS, Linux, or Windows (via [WSL](https://learn.microsoft.com/en-us/windows/wsl/install))
- `ssh`, `ssh-keygen`, `ssh-copy-id` (pre-installed on macOS/Linux/WSL)
- A valid LIP6 account with cluster access
- Your LIP6 secure password (wifi/workstation, **not** email password)

## Reset / Uninstall

```bash
./lip6-cluster-setup --reset
```

Two options:

| Mode | What it removes |
|------|-----------------|
| **Local only** | `~/hpc-notebook`, `~/conv-manager`, SSH config (restored from backup), shell aliases |
| **Full reset** | Everything above + restores `.bashrc` on HPC and Convergence from pre-setup backup |

The reset uses a single SSH call per server (instead of multiple). If both remote servers are unreachable, you'll be warned before local config is removed.

SSH keys are never deleted (they're safe to keep).

## Security

All user inputs (job IDs, core counts, walltimes, job names, script paths) are validated against strict patterns before being used in any command. This prevents command injection via SSH.

- **Job IDs** — numeric only
- **Core/GPU counts** — numeric only
- **Durations** — parsed through `parse_duration()` which only accepts known formats
- **Job names** — alphanumeric, hyphens, underscores only
- **Script paths** — letters, digits, `.`, `_`, `~`, `/`, `-` only
- **SSH config** — uses `StrictHostKeyChecking accept-new` and `IdentitiesOnly yes` to prevent host key attacks and extra key auth failures
- **SSH keys** — generated without passphrase for convenience (a warning is shown with instructions to add one)
- **Existing SSH config** — preserved via `Include config.d/*` (not overwritten)
- **Temp files** — created with `mktemp` to prevent race conditions

## Input validation

The setup wizard validates all inputs with retry loops:

- **Username** — lowercase letters, digits, underscores only
- **Email** — letters, digits, dots, standard email characters only
- **Menu choices** — must be a valid option number

A confirmation summary is shown before any changes are made. Press Ctrl+C at any point to abort.

## File structure

```
lip6-cluster-setup    # Main setup script (run this)
hpc-notebook          # HPC manager (installed to ~/ by setup)
conv-manager          # Convergence manager (installed to ~/ by setup)
LICENSE               # MIT license
```

## Disclaimer

This is an **unofficial**, community-made tool. It is **not** affiliated with, endorsed by, or maintained by LIP6, Sorbonne University, or CNRS.

- The scripts interact with your SSH configuration, shell config files, and remote `.bashrc`. While backups are created before modifications, **use at your own risk**.
- The author is not responsible for any misconfiguration, data loss, or access issues resulting from the use of these scripts.
- Cluster policies, hostnames, scheduler configurations, and access methods may change without notice. If something breaks, check with your cluster administrators.
- **Never share your SSH private keys or passwords.** These scripts never store or transmit credentials — they only use standard `ssh-copy-id` for key distribution.

## License

MIT

## Author

**Allaa Boutaleb** — [allaa.boutaleb@lip6.fr](mailto:allaa.boutaleb@lip6.fr)
