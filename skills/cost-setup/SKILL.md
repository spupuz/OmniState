---
name: cost-setup
description: Optimized setup for persistent memory, auto-archiving, and cost-routing rules.
---
# Cost Setup (Economy v1.1.1)

**SKILL GOAL:** Initialize project memory with token-saving configurations and enforce total git protection.

**GLOBAL RULES:**
- Output MUST be strictly in English.
- No memory files, templates, or workflows to Git.

## Instructions:

1. **Automatic Sync:** 
   - Identify global OmniState path: `~/.gemini/antigravity/plugins/omnistate`.
   - Action: Run `bash [path]/update.sh --auto .` (or powershell equivalent on Windows) to align workflows.
2. **Memory Setup:**
   - Create `antigravity.config.json`, `project-summary.md`, and `tasks-history.json` from templates if missing.
   - Initialize `tasks-archive.json`.
3. **Total Git Protection:**
   - Ensure the following are in `.gitignore`: 
     ```
     antigravity.config.json
     project-summary.md
     tasks-history.json
     tasks-archive.json
     omnistate-dashboard.html
     /omnistate-dashboard.html
     chunks/
     .agent/
     .agents/
     ```
4. **Cost Routing:**
   - Inform user: "Cost routing active. I will suggest switching to 'Lite' models (e.g., Gemini Flash) for routine tasks."
   - Ask: "Activate model-switch reminders? (Y/N)"
5. **Completion:** Show status: "✅ Memory initialized. ✅ Workflows synchronized. ✅ Total Git Protection enforced."
