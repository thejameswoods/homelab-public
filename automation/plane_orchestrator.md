# plane_orchestrator.py — Plane Task Discovery & Dispatch

## Purpose
Discovers active tasks in **Plane** (Project Management) that are assigned to specific AI agents. Orchestrates the full lifecycle of a task: from "Pickup" (concurrency locking) to remote execution on an AI Workstation, and finally posting results back with automated state transitions.

---

## Key Features

### 🤖 Multi-Agent Support
Dynamically switches between agents (e.g., Gemini, Claude) based on assignments in Plane. Fetches agent-specific API tokens from Windmill variables (`f/plane/token_gemini`, etc.).

### 🔒 Concurrency Protection (Locking)
Uses a **[PICKUP]** comment mechanism to ensure multiple agents don't work on the same task simultaneously.
1. Agent posts a `[PICKUP]` comment with a unique Job ID.
2. Agent verifies it "owns" the latest lock before proceeding.
3. Once verified, it transitions the task to **In Progress**.

### 🔄 Automated Workflow
Automatically moves Plane work items through states:
- **Pickup**: Backlog/Todo → **In Progress**
- **Completion**: In Progress → **Review**

### ✍️ Perfect Spacing & Formatting
Instructs agents to use standard Markdown, but pre-processes the output before posting to Plane. 
- **Hybrid Tightening**: Converts Markdown to HTML and "flattens" internal newlines.
- **Result**: Pro-quality, single-spaced rich text in the Plane UI with bold headers and clean lists.

### 🧠 Persistent Conversation IDs
Every Plane issue is assigned a permanent `CONV_ID` (based on the Plane UUID). This ID is passed to the AI workstation as an environment variable (`export CONV_ID=...`), enabling long-term task-specific memory across multiple orchestrator runs.

### 🛡 YOLO vs. Safe Mode
Granular permission control via Plane labels:
- **Safe Mode (Default)**: Agents run with standard permissions (may ask for approval).
- **YOLO Mode**: Add the **"yolo"** tag in Plane to enable high-privilege flags (`--approval-mode=yolo` for Gemini, `--dangerously-skip-permissions` for Claude).

---

## Architecture Flow

1. **Discovery**: Polls Plane API for issues assigned to configured Agent UUIDs.
2. **Context Gathering**: Pulls the full chronological comment history (excluding noise) to provide the agent with complete task memory.
3. **Locking**: Posts `[PICKUP]` comment and transitions state to "In Progress".
4. **Execution**: SSH into a remote AI Workstation, exports `CONV_ID`, and runs the agent CLI with the gathered context.
5. **Reporting**: Converts agent output to "tight" HTML and posts it as a comment in Plane.
6. **Completion**: Transitions task to "Review" state.

---

## Configuration (Windmill)

### Variables & Secrets
| Path | Type | Description |
|---|---|---|
| `f/plane/token_gemini` | Secret | API Key for Gemini Agent |
| `f/plane/token_claude` | Secret | API Key for Claude Agent |
| `f/plane/agent_timeout` | Variable | SSH execution timeout in **minutes** (default 10) |

### Agent Mapping
Defined in the `AGENTS` dictionary within the script:
- Maps Plane **User UUIDs** to CLI commands and credential variables.

---

## Error Handling
- **Race Condition Detection**: Aborts if another agent grabs the task during the pickup phase.
- **SSH Escape Safety**: Uses `shlex.quote` for all context strings to prevent shell injection or "unexpected EOF" errors caused by special characters/quotes in comments.
- **State Fallback**: Logs if a state transition fails but continues reporting results to ensure work isn't lost.
