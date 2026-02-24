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
2. **Configure passwordless SSH** through the LIP6 gateway with ProxyJump, `IdentitiesOnly yes`, and SSH multiplexing (`ControlMaster`)
3. **Copy keys** to all servers (gateway, HPC, Convergence, compute nodes)
4. **Install TUI managers** (`hpc` / `lip6-hpc` and `conv` / `lip6-conv`) via `pip install`
5. **Write config** to `~/.lip6/config.toml` (username, email, cluster settings)
6. **Add aliases** to your shell (bash, zsh, or fish)
7. **Configure remote `.bashrc`** with cluster-specific aliases and helpers

After setup, you get two interactive TUI apps:

| Command | Cluster | What it manages |
|---------|---------|-----------------|
| `hpc` / `lip6-hpc` | HPC (OAR) | CPU jobs — up to 48 cores, 128GB RAM |
| `conv` / `lip6-conv` | Convergence (SLURM) | GPU jobs — A100 80GB / 40GB MIG |

## TUI Managers

Both managers are full-screen terminal applications built with [Textual](https://textual.textualize.io/) — keyboard-driven with live-refreshing dashboards, form inputs, and rich visual layout.

### Features

- **Live dashboard** — auto-refreshing job table showing RUNNING and PENDING jobs with elapsed/remaining time
- **Keyboard navigation** — all actions via hotkeys shown in the footer bar
- **Launch forms** — input widgets with validation for cores, duration, GPU type, job name
- **Job waiting** — progress spinner with elapsed time, polls every 5s, auto-connects when running
- **Session ready screen** — shows Job ID, node, Jupyter URL, SSH command, manages tunnel
- **Connect/Kill** — job picker table for selecting which job to connect to or cancel
- **SSH tunnel management** — automatic tunnel setup with status indicator
- **Browser integration** — opens Jupyter URL automatically

### HPC Manager (`hpc` / `lip6-hpc`)

Footer keybindings: `[L]aunch  [C]onnect  [K]ill  [S]SH  [R]efresh  [Q]uit`

- Dashboard with RUNNING jobs (ID, Name, Node, Cores, Elapsed, Remaining) and PENDING jobs
- Launch screen: cores (default 24), duration (default 24h), work mode (Jupyter/Terminal/Custom)
- 30-second auto-refresh

### Convergence Manager (`conv` / `lip6-conv`)

Footer keybindings: `[L]aunch  [C]onnect  [K]ill  [G]PU Status  [S]SH  [R]efresh  [Q]uit`

- Dashboard with GPU job details (ID, Name, Node, Elapsed, Time Limit, Time Left)
- Launch screen: GPU type picker (A100 80GB full / A100 40GB MIG), GPU count, duration, job name, work mode
- **Cluster status screen** (`G`) — node-by-node table with CPUs, memory, GRES, state

### Friendly duration input

Both managers accept natural duration formats:

| Input | Meaning |
|-------|---------|
| `30m` | 30 minutes |
| `8h` | 8 hours |
| `3d` | 3 days |
| `3d 12h` | 3 days 12 hours |
| `1d 6h 30m` | 1 day 6 hours 30 minutes |
| `8:0:0` | 8 hours (legacy H:M:S) |
| `24` | 24 hours (bare number) |

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
- **Python 3.8+** with pip (for TUI managers)
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
| **Local only** | `lip6tui` Python package, `~/.lip6/` config, legacy scripts, SSH config (restored from backup), shell aliases |
| **Full reset** | Everything above + restores `.bashrc` on HPC and Convergence from pre-setup backup |

SSH keys are never deleted (they're safe to keep).

## Security

All user inputs (job IDs, core counts, walltimes, job names, script paths) are validated before being used in any command. This prevents command injection via SSH.

- **SSH config** — uses `StrictHostKeyChecking accept-new`, `IdentitiesOnly yes`, and `ControlMaster` for connection multiplexing
- **Existing SSH config** — preserved via `Include config.d/*` (not overwritten)
- **Config** — stored in `~/.lip6/config.toml` (no passwords, only username/email/cluster settings)

## File structure

```
lip6-cluster-setup/
├── lip6-cluster-setup              # Bash setup wizard
├── lip6tui/                        # Python TUI package
│   ├── __init__.py                 # Version string
│   ├── config.py                   # Read ~/.lip6/config.toml
│   ├── ssh.py                      # SSH subprocess execution (sync + async)
│   ├── duration.py                 # Duration parsing
│   ├── validators.py               # Input validation
│   ├── hpc/                        # HPC app (OAR)
│   │   ├── app.py                  # Textual App + screens
│   │   ├── app.tcss                # Textual CSS
│   │   └── commands.py             # OAR command wrappers
│   ├── conv/                       # Conv app (SLURM)
│   │   ├── app.py                  # Textual App + screens
│   │   ├── app.tcss                # Textual CSS
│   │   └── commands.py             # SLURM command wrappers
│   └── widgets/                    # Shared widgets
│       ├── header.py               # Branded header bar
│       ├── job_table.py            # DataTable-based job list
│       ├── launch_form.py          # Job launch form base
│       ├── status_panel.py         # Connection status display
│       └── cluster_status.py       # GPU node grid (Conv)
├── pyproject.toml                  # Package metadata + entry points
├── hpc-notebook                    # Legacy HPC manager (kept for compat)
├── conv-manager                    # Legacy Conv manager (kept for compat)
├── README.md
└── LICENSE
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
