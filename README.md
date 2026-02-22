# LIP6 Cluster Setup

One-command setup for passwordless SSH access and interactive job management on **LIP6 lab clusters** (Sorbonne University).

Supports both the **HPC cluster** (CPU, OAR scheduler) and the **Convergence cluster** (NVIDIA A100 GPUs, SLURM scheduler).

## What it does

```
git clone https://github.com/Allaa-boutaleb/lip6-cluster-setup.git
cd lip6-cluster-setup/
chmod +x lip6-cluster-setup
./lip6-cluster-setup
```

The setup wizard will:

1. **Generate an SSH key** (ed25519) if you don't have one
2. **Configure passwordless SSH** through the LIP6 gateway with ProxyJump
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

Both managers provide an interactive menu to:

- **Launch sessions** — Jupyter Lab, terminal, or both
- **Reconnect** to running sessions (auto-selects if only one job)
- **View jobs** and cluster status
- **Cancel jobs** (individual or all)
- **SSH tunnel** setup for Jupyter with automatic browser opening

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
  q)  Quit
```

Work modes:
- **Jupyter Lab** — submits batch job, waits, tunnels, opens browser
- **Terminal only** — interactive OAR session
- **Both** — Jupyter + terminal command for a second tab

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
  q)  Quit
```

Additional features:
- **GPU type picker** — full A100 80GB (node01-06) or MIG 40GB (node07-10)
- **Multi-GPU** support (up to 4 per node)
- **Custom script submission** with GPU allocation
- **Automatic port detection** from Jupyter logs (handles port conflicts)

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

- macOS or Linux (local machine), or WSL on Windows.
- `ssh`, `ssh-keygen`, `ssh-copy-id`
- A valid LIP6 account with cluster access
- Your LIP6 secure password (wifi/workstation, **not** email password)

## Reset / Uninstall

```
./lip6-cluster-setup --reset
```

Two options:

| Mode | What it removes |
|------|-----------------|
| **Local only** | `~/hpc-notebook`, `~/conv-manager`, SSH config (restored from backup), shell aliases |
| **Full reset** | Everything above + restores `.bashrc` on HPC and Convergence from pre-setup backup |

SSH keys are never deleted (they're safe to keep).

## Input validation

The setup wizard validates all inputs with retry loops:

- **Username** — lowercase letters, digits, underscores only
- **Email** — must contain `@` and a domain
- **Menu choices** — must be a valid option number

A confirmation summary is shown before any changes are made. Press Ctrl+C at any point to abort.

## File structure

```
lip6-cluster-setup    # Main setup script (run this)
hpc-notebook          # HPC manager (installed to ~/ by setup)
conv-manager          # Convergence manager (installed to ~/ by setup)
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
