---
name: start-session
description: Optimized session startup with context purge and state restoration.
---
# Start Session (Economy v1.1.1)

**SKILL GOAL:** Restore session state while minimizing the context window to maximize performance and save tokens.

**INSTRUCTIONS:**

1. **Context Purge:** Ignore all files/history not explicitly listed below. Start fresh.
2. **Integrity Check:** Run global OmniState update script: `bash ~/.gemini/antigravity/plugins/omnistate/update.sh --auto .`
3. **State Loading:**
   - Read `antigravity.config.json` (settings).
   - Read `project-summary.md` (architecture).
   - Read `tasks-history.json` (active tasks).
4. **Summary (Strictly English & Concise):**
   - Display: "✅ OmniState v[version] active."
   - Display: "📂 Core architecture loaded."
   - List only "todo" tasks from `tasks-history.json`.
5. **Enforcement:** Do not read full repository files until explicitly requested for a specific task.
