import requests
import subprocess
import json
import os
import sys
import wmill
import shlex
import markdown
import re
import html
import time
from datetime import datetime

VERSION = "1.2.2"
# --- Agent System Prompt ---
# Edit this to change how the agent focuses or formats its response.
AGENT_SYSTEM_PROMPT = """
CRITICAL: Use standard Markdown for your response. 
1. Headers MUST start with # or ## on their own lines.
2. Ensure at least one newline exists between paragraphs and headers so the structure is clear.
3. You MUST wrap your final, user-facing response strictly inside <final_answer>...</final_answer> tags.
4. Any reasoning, tool outputs, or logs should go outside the <final_answer> tags.
"""

"""
Plane Agent Orchestrator
------------------------
Verified for Plane v2.5.2 Commercial API.
Transitions issues from Backlog/Todo to In Progress.
Posts agent output as HTML comments.
"""

# Agent UUIDs from Plane
AGENTS = {
    "YOUR_GEMINI_AGENT_UUID": {
        "name": "Gemini", 
        "base_cli": "gemini", 
        "yolo_flags": "--approval-mode=yolo",
        "token_var": "f/plane/token_gemini"
    },
    "YOUR_CLAUDE_AGENT_UUID": {
        "name": "Claude", 
        "base_cli": "claude", 
        "yolo_flags": "--dangerously-skip-permissions",
        "token_var": "f/plane/token_claude"
    }
}

# State Mapping (Group names to target State IDs for Home Lab project)
STATE_TRANSITIONS = {
    "backlog": "YOUR_BACKLOG_STATE_UUID",
    "todo": "YOUR_TODO_STATE_UUID",
    "started": "YOUR_IN_PROGRESS_STATE_UUID", # In Progress
    "review": "YOUR_REVIEW_STATE_UUID",
    "completed": "YOUR_DONE_STATE_UUID", # Done
    "cancelled": "YOUR_CANCELLED_STATE_UUID"
}

def main(plane_url: str = "http://your-plane-instance.lan", workspace_slug: str = "your-workspace-slug", workstation_host: str = "your-ai-workstation.lan"):
    print(f"[*] Plane Agent Orchestrator {VERSION} starting...")
    # 0. Load Configuration
    try:
        timeout_raw = int(wmill.get_variable("f/plane/agent_timeout"))
        agent_timeout = timeout_raw * 60
        timeout_display = f"{timeout_raw} minutes"
    except Exception:
        agent_timeout = 600 # Default to 10 minutes
        timeout_display = "10 minutes"
    
    # Retrieve discovery secret from Windmill Variable (defaulting to gemini)
    discovery_api_key = wmill.get_variable("f/plane/token_gemini") 
    
    discovery_headers = {"X-API-Key": discovery_api_key, "Content-Type": "application/json"}
    base_url = plane_url.rstrip('/')
    
    # 1. Get all projects in the workspace
    projects_endpoint = f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/"
    print(f"[*] Fetching projects from: {projects_endpoint}")
    
    p_resp = requests.get(projects_endpoint, headers=discovery_headers)
    if not p_resp.ok:
        print(f"Error fetching projects: {p_resp.status_code} - {p_resp.text}")
        return

    projects = p_resp.json().get("results", [])
    processed_count = 0
    
    for project in projects:
        project_id = project['id']
        project_name = project['name']
        
        # 2. Get active issues for this project
        # We expand labels to check for the 'yolo' tag
        issues_endpoint = f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/?expand=assignees,state,labels"
        print(f"[*] Checking project '{project_name}' for agent tasks...")
        
        i_resp = requests.get(issues_endpoint, headers=discovery_headers)
        if not i_resp.ok:
            print(f"    [!] Error fetching issues for {project_name}: {i_resp.status_code}")
            continue

        issues = i_resp.json().get("results", [])
        
        for issue in issues:
            assignees = [a['id'] for a in issue.get('assignees', [])]
            
            # Check if any assigned user is one of our agents
            agent_id = next((uid for uid in assignees if uid in AGENTS), None)
            if not agent_id:
                continue
                
            agent_info = AGENTS[agent_id]
            issue_id = issue['id']
            
            # Load agent specific token for task completion
            print(f"        [*] Using token for {agent_info['name']} ({agent_info['token_var']})")
            agent_api_key = wmill.get_variable(agent_info['token_var'])
            agent_headers = {"X-API-Key": agent_api_key, "Content-Type": "application/json"}
            
            # Filter for active states (backlog, unstarted/todo, started)
            state_info = issue.get('state', {})
            state_group = state_info.get('group', '') if isinstance(state_info, dict) else ''
            
            if state_group not in ['backlog', 'unstarted', 'started']:
                continue

            print(f"    [!] Found task for {agent_info['name']}: {issue['name']} ({issue_id}) [Group: {state_group}]")

            # 3. Check last comment logic
            comm_endpoint = f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/comments/"
            comm_resp = requests.get(comm_endpoint, headers=agent_headers)
            
            if not comm_resp.ok:
                print(f"        [!] Error fetching comments: {comm_resp.status_code}")
                continue
                
            comments = comm_resp.json().get("results", [])
            
            if comments:
                latest_comment = comments[0] # For actor check
                last_actor_id = latest_comment['created_by']
                
                # Check if any assigned user is one of our agents
                if last_actor_id in AGENTS:
                    print(f"        [!] Last comment was from an agent ({AGENTS[last_actor_id]['name']}). Skipping.")
                    continue
                
                # Build conversation history (Oldest First)
                history_items = []
                for c in reversed(comments):
                    c_text = c.get('comment_stripped', '')
                    # Skip internal pickup/lock messages
                    if c_text.startswith('[PICKUP]'):
                        continue
                        
                    author = AGENTS[c['created_by']]['name'] if c['created_by'] in AGENTS else "User"
                    history_items.append(f"{author}: {c_text}")
                
                history_text = "\n".join(history_items)
                print(f"        [+] Conversation history built ({len(history_items)} items)")
            else:
                print("        [+] No comments found. Initial pickup.")
                history_text = "Initial pickup of task."

            # 4. Prepare the Agent Prompt
            # Stripping HTML from description if any
            desc = issue.get('description_stripped', 'No description')
            context = f"Task: {issue['name']}\nDescription: {desc}\n\nConversation History:\n{history_text}\n\n{AGENT_SYSTEM_PROMPT}"
            
            # --- Concurrency Protection (Locking) ---
            job_id = os.environ.get('WM_JOB_ID', 'local')[:8]
            
            # Use the Plane Work Item ID as the persistent Conversation ID
            conv_id = issue['id']
            
            print(f"        [~] Locking task via pickup comment (Job: {job_id})...")
            pickup_text = f"<p><strong>[PICKUP]</strong> {agent_info['name']} (Job: {job_id}) | <strong>Conv:</strong> {conv_id[:8]} starting execution...</p>"
            pickup_resp = requests.post(comm_endpoint, headers=agent_headers, json={"comment_html": pickup_text})
            
            if not pickup_resp.ok:
                print(f"            [!] Failed to post pickup comment. Skipping.")
                continue
                
            # Short wait for API consistency
            time.sleep(1)
            
            # Re-fetch comments to verify we "won" the pickup
            verify_resp = requests.get(comm_endpoint, headers=agent_headers)
            if not verify_resp.ok:
                print(f"            [!] Failed to verify pickup. Skipping.")
                continue
                
            latest_comments = verify_resp.json().get("results", [])
            if not latest_comments or latest_comments[0].get('comment_stripped', '').find(f"(Job: {job_id})") == -1:
                print(f"            [!] Concurrency check failed: Another agent or user intervened. Aborting.")
                continue
            
            print(f"        [✓] Pickup verified for job {job_id}. Proceeding.")
            # ----------------------------------------

            # 5. Move to 'In Progress' if not already there
            if state_group != 'started' and project_name == "Home Lab":
                print(f"        [~] Moving task to In Progress...")
                patch_resp = requests.patch(
                    f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
                    headers=agent_headers,
                    json={"state": STATE_TRANSITIONS["started"]}
                )
                if not patch_resp.ok:
                    print(f"            [!] Failed to transition state: {patch_resp.text}")

            # --- Tag Detection (Safe/YOLO Mode) ---
            # Check if any of the issue labels are named 'yolo'
            # (Plane's API can return these in label_details or labels depending on expansion)
            label_list = issue.get('label_details', []) or issue.get('labels', [])
            is_yolo = any(isinstance(l, dict) and l.get('name', '').lower() == 'yolo' for l in label_list)
            
            # Form final CLI command
            final_cli = agent_info['base_cli']
            if is_yolo:
                print(f"        [!] 'yolo' tag detected. Enabling {agent_info['yolo_flags']}...")
                final_cli = f"{agent_info['base_cli']} {agent_info['yolo_flags']}"
            else:
                print(f"        [~] Running in safe mode (no yolo flags).")

            # 6. Route to Workstation via SSH
            print(f"        [>] Executing {final_cli} on {workstation_host} (Conv: {conv_id})...")
            
            # Run CLI with Conversation ID as environment variable.
            # We use shlex.quote for the context to ensure it's safely escaped for the remote shell.
            # We use a longer timeout for agent work.
            safe_context = shlex.quote(context)
            ssh_internal_cmd = f"export CONV_ID={conv_id} && {final_cli} {safe_context}"
            
            ssh_cmd = [
                "ssh", "-o", "StrictHostKeyChecking=no", f"claude@{workstation_host}",
                ssh_internal_cmd
            ]
            
            try:
                # We use shell=False for security
                process = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=agent_timeout)
                stdout = process.stdout
                stderr = process.stderr
                
                # Combine output
                output = stdout
                if stderr and process.returncode != 0:
                    output += f"\n\nERROR:\n{stderr}"
                
                if not output.strip():
                    output = "Agent executed but returned no output."

                # 7. Post Result back to Plane as HTML
                # Separate thought process from final answer
                final_answer_match = re.search(r'<final_answer>(.*?)</final_answer>', output, re.DOTALL)
                
                if final_answer_match:
                    final_content = final_answer_match.group(1).strip()
                    thought_process = output.replace(final_answer_match.group(0), "").strip()
                else:
                    final_content = output.strip()
                    thought_process = "Agent did not wrap its response in <final_answer> tags."

                # Pre-process final_content to fix 'sloppy' Markdown
                final_content = re.sub(r'([^\n])(#{1,6}\s)', r'\1\n\n\2', final_content)
                final_content = re.sub(r'([^\n])(\*\s)', r'\1\n\2', final_content)
                
                # Convert Markdown to HTML
                html_raw = markdown.markdown(final_content, extensions=['extra', 'sane_lists'])
                html_res = html_raw.replace("\n", "").replace("\r", "")
                
                # Format Thought Process inside a collapsible block
                escaped_thoughts = html.escape(thought_process)
                thought_html = f"<details><summary><b>Thought Process</b></summary><pre style='white-space: pre-wrap; font-size: 12px; background: #fdfdfd; padding: 10px; border-radius: 4px;'>{escaped_thoughts}</pre></details><br>"
                
                # Add an audit trail footer
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                footer = f"<hr><p><small><strong>Agent:</strong> {agent_info['name']} | <strong>Job:</strong> {job_id} | <strong>Conv:</strong> {conv_id} | <strong>Time:</strong> {timestamp} | <strong>Orchestrator:</strong> {VERSION}</small></p>"
                html_output = f"{thought_html}{html_res}{footer}"
                
                comment_payload = {
                    "comment_html": html_output
                }
                requests.post(comm_endpoint, headers=agent_headers, json=comment_payload)
                print("        [✓] Comment posted.")
                
                # 8. Move task to 'Review'
                print(f"        [~] Moving task to Review...")
                requests.patch(
                    f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
                    headers=agent_headers,
                    json={"state": STATE_TRANSITIONS["review"]}
                )
                print("        [✓] State transitioned to Review.")
                
                processed_count += 1
                
            except subprocess.TimeoutExpired as e:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"        [X] Execution timed out after {timeout_display}.")
                
                captured_out = str(e.stdout) if e.stdout else "No standard output captured."
                captured_err = str(e.stderr) if e.stderr else "No standard error captured."
                
                # 7. Post Timeout back to Plane as HTML
                timeout_msg = f"<p><strong>[TIMEOUT]</strong> Agent {agent_info['name']} timed out after {timeout_display}.</p>"
                
                escaped_out = html.escape(captured_out)
                escaped_err = html.escape(captured_err)
                logs_html = f"<details><summary><b>Partial Logs (Before Timeout)</b></summary><pre style='white-space: pre-wrap; font-size: 12px; background: #fff3f3; padding: 10px; border-radius: 4px;'><b>STDOUT:</b>\n{escaped_out}\n\n<b>STDERR:</b>\n{escaped_err}</pre></details><br>"
                
                footer = f"<hr><p><small><strong>Agent:</strong> {agent_info['name']} | <strong>Job:</strong> {job_id} | <strong>Conv:</strong> {conv_id} | <strong>Time:</strong> {timestamp} | <strong>Orchestrator:</strong> {VERSION}</small></p>"
                html_output = f"{timeout_msg}{logs_html}{footer}"
                
                comment_payload = {
                    "comment_html": html_output
                }
                requests.post(comm_endpoint, headers=agent_headers, json=comment_payload)
                
                # 8. Revert task to 'Todo' so it can be retried
                print(f"        [~] Reverting task to Todo...")
                requests.patch(
                    f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
                    headers=agent_headers,
                    json={"state": STATE_TRANSITIONS["todo"]}
                )
                print("        [✓] State reverted.")

            except Exception as e:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                print(f"        [X] Error during execution: {e}")
                
                 # 7. Post Error back to Plane as HTML
                error_msg = f"<p><strong>[ERROR]</strong> An unexpected orchestrator error occurred.</p>"
                
                escaped_e = html.escape(str(e))
                logs_html = f"<details><summary><b>Error Traceback</b></summary><pre style='white-space: pre-wrap; font-size: 12px; background: #fff3f3; padding: 10px; border-radius: 4px;'>{escaped_e}</pre></details><br>"
                
                footer = f"<hr><p><small><strong>Agent:</strong> {agent_info['name']} | <strong>Job:</strong> {job_id} | <strong>Conv:</strong> {conv_id} | <strong>Time:</strong> {timestamp} | <strong>Orchestrator:</strong> {VERSION}</small></p>"
                html_output = f"{error_msg}{logs_html}{footer}"
                
                comment_payload = {
                    "comment_html": html_output
                }
                requests.post(comm_endpoint, headers=agent_headers, json=comment_payload)

                # 8. Revert task to 'Todo' for manual review
                print(f"        [~] Reverting task to Todo...")
                requests.patch(
                    f"{base_url}/api/v1/workspaces/{workspace_slug}/projects/{project_id}/issues/{issue_id}/",
                    headers=agent_headers,
                    json={"state": STATE_TRANSITIONS["todo"]}
                )
                print("        [✓] State reverted.")

    return {"processed": processed_count}
