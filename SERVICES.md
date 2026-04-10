# Showcase: Homelab Services Directory

A comprehensive map of the services running in the homelab ecosystem.

## 🧱 Core Infrastructure
The foundation for virtualization and containerization.

| Service | Category | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **Proxmox VE Cluster** | Virtualization | 3-node HA cluster hosting all VMs and LXC containers. | Debian-based Proxmox |
| **Nginx Proxy Manager** | Networking | Reverse proxy with automatic SSL for all internal web services. | Nginx, MariaDB, Docker |
| **WireGuard VPN** | Security | Encrypted remote access to the home network. Zero open ports. | WireGuard, Linux |

## 📦 Data & Storage
Resilient storage and digital archive management.

| Service | Category | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **Storage Vault** | Storage | Primary family NAS for media and documents. | OpenMediaVault, ZFS |
| **Vault Mirror** | Backup | Real-time mirror for disaster recovery. | OMV, RSync |
| **Paperless-ngx** | Documents | Private document management with OCR and full-text search. | Python, Tesseract, Redis |

## 🤖 AI & Automation
Local intelligence, agent orchestration, and automated home control.

| Service | Category | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **Plane** | Task Management | Project management tool used as the task queue and memory layer for AI agents. | React, Postgres, Docker |
| **Windmill** | Orchestrator | Schedules and runs the multi-agent orchestrator; routes Plane tasks to Claude or Gemini via SSH. | Rust, TypeScript, Python, Postgres |
| **AI Workstation** | Agent Runtime | Ubuntu VM hosting Claude CLI and Gemini CLI with GitHub, Google Drive, 1Password, and Playwright access. | Ubuntu, Claude CLI, Gemini CLI |
| **Playwright Server** | Browser Automation | Headless browser server used by AI agents for web interaction, scraping, and UI-driven tasks. | Playwright, Node.js |
| **Ollama** | Private AI | Local LLM inference engine for on-premise model hosting. | C++, GPU-Acceleration |
| **LiteLLM** | AI Gateway | Unified OpenAI-compatible API across multiple local models. | Python |
| **Home Assistant** | Automation | Central smart home OS and orchestration hub. | Home Assistant Core |

## 📂 Productivity & Archiving

| Service | Category | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **ArchiveBox** | Archive | Personal web archival tool for persistent links. | Python, Django |
| **Wastebin** | Utility | Private paste-bin for quick code and text sharing. | Rust, SQLite |

## 📊 Finance

| Service | Category | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **Ghostfolio** | Finance | Dashboard for investment portfolio tracking. | TypeScript, Postgres, Docker |

## 📺 Entertainment & Media

| Service | Category | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **Plex** | Media | High-performance media streaming server. | Plex Media Server |
| **Immich** | Photos | Private, self-hosted photo platform with built-in face recognition and smart search. | Flutter, TypeScript, Docker |
| **Overseerr** | Management | Request and discovery UI for the media stack. | Next.js, TypeScript |
| **-arr Stack** | Automation | Automated media management (Sonarr, Radarr). | .NET, Python |

## 🛡️ Security & Health

| Service | Category | Purpose | Tech Stack |
| :--- | :--- | :--- | :--- |
| **AdGuard Home** | Network | Network-wide ad and tracker blocking via DNS. | Go, DNS-over-HTTPS |
| **PiAlert** | Monitoring | Intrusion detection and network device monitoring. | Python, SQLite |
| **Grafana / InfluxDB** | Observability | Performance dashboards and time-series metrics. | Go, Grafana, InfluxDB |

---
*For a deeper dive into specific areas, see the corresponding subdirectories.*
