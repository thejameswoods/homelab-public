# Automation & AI: Multi-Agent Platform

The core engineering project in the homelab is a **multi-agent orchestration system** that treats Claude and Gemini as assignable workers — given tasks the same way you'd give them to a person, with defined tools, scoped access, and governance controls built in.

---

## 🧠 The Plane Orchestrator

**Source:** [`plane_orchestrator.py`](./plane_orchestrator.py) · [`Documentation`](./plane_orchestrator.md)

A Python script scheduled in Windmill that manages the full lifecycle of an agent task:

1. **Discovery** — Polls the Plane API for issues assigned to the Claude or Gemini agent accounts across all projects.
2. **Locking** — Posts a `[PICKUP]` comment with a unique Windmill Job ID, then re-fetches to verify ownership before proceeding. Prevents two agents from claiming the same task.
3. **Context** — Builds a chronological conversation history from the Plane issue's comment thread, giving the agent full memory of prior interactions.
4. **Execution** — SSHes into the AI Workstation, exports the Plane issue UUID as a persistent `CONV_ID`, and runs the appropriate CLI with the full context as the prompt.
5. **Reporting** — Parses `<final_answer>` tags from the agent's output, converts Markdown to HTML, wraps the raw thought process in a collapsible `<details>` block, and posts the result as a formatted Plane comment.
6. **State Management** — Automatically transitions tasks: Backlog/Todo → In Progress → Review. Reverts to Todo on timeout or error so nothing is silently lost.

### Governance Model

| Control | Mechanism |
|---|---|
| **Permission level** | `yolo` Plane label enables elevated flags; default is safe mode |
| **Credentials** | Fetched from 1Password via Windmill secrets at runtime — never stored in code |
| **Concurrency** | `[PICKUP]` comment + Job ID re-verification before execution |
| **Task memory** | Plane issue UUID used as persistent `CONV_ID` across orchestrator runs |
| **Audit trail** | Every comment includes Agent, Job ID, Conv ID, Timestamp, and Orchestrator version |

---

## 🤖 AI Workers

A dedicated Ubuntu VM hosts both AI workers:

| Agent | CLI | Notes |
|---|---|---|
| **Claude** | `claude` | Anthropic's Claude CLI |
| **Gemini** | `gemini` | Google's Gemini CLI |

Both workers share the same tool access:
- **GitHub** — Read/write access to repositories (create files, open PRs, commit code)
- **Google Drive** — Read and write documents
- **1Password** — Restricted vault access for authenticating into local and cloud services at runtime
- **Playwright** — Browser automation server for web interaction, scraping, and UI-driven tasks

The orchestrator selects the agent based on which Plane user the issue is assigned to. Permission level (Safe vs. YOLO) is controlled per-task via a Plane label.

---

## ⚙️ Workflow Engine: Windmill

**Windmill** runs the orchestrator on a schedule and provides the secret/variable store it depends on:

| Variable | Type | Purpose |
|---|---|---|
| `f/plane/token_claude` | Secret | Plane API key for the Claude agent account |
| `f/plane/token_gemini` | Secret | Plane API key for the Gemini agent account |
| `f/plane/agent_timeout` | Variable | SSH execution timeout in minutes (default: 10) |

Windmill also hosts other background scripts and internal webhooks that keep the broader homelab running.

---

## 📋 Task Management: Plane

**Plane** is the interface between humans and agents. Tasks are created normally and assigned to the Claude or Gemini user account. The orchestrator picks them up, executes them, and posts results back as comments — making Plane the memory layer and full audit log for all agent work.

---

## 🏠 Home Automation: Home Assistant

**Home Assistant** is the central hub for smart home control, running fully local via Zigbee, Z-Wave, and local network protocols. No cloud-dependent devices. Automation logic reacts to motion, time, and environmental sensors without requiring an internet connection.

---

## 📂 Document Management: Paperless-ngx

**Paperless-ngx** digitizes and organizes physical documents using OCR (via Tesseract) for full-text search across the entire document archive. Incoming scans are processed automatically and stored in a searchable, privately hosted digital filing system.

---

*Back to [Top](../README.md)*
