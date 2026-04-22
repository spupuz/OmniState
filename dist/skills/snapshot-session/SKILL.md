---
name: snapshot-session
description: Snapshot creation with automatic task archiving and summary distillation.
---
# Snapshot Session (Economy v1.1.0)

**SKILL GOAL:** Persist work state and optimize memory for future sessions.

**INSTRUCTIONS:**

1. **State Sync:** Run `bash ~/.gemini/antigravity/plugins/omnistate/update.sh --auto .`
2. **Task Archiving:**
   - Scan `tasks-history.json` for `status: done`.
   - If `done` tasks count > 10 OR (archive_threshold from config met):
     - Append them to `tasks-archive.json` with timestamp.
     - Remove them from `tasks-history.json`.
3. **Summary Distillation:**
   - Detect session changes.
   - Update `project-summary.md` section "Latest Progress":
     - Write a max 3-line distilled summary (keywords + core result).
4. **Session Chunk:**
   - Create `chunks/session-YYYYMMDD-HHMM.md`.
   - Content: Bullet points of technical changes ONLY.
6. **Dashboard Update (Automatic):**
   - If `omnistate-dashboard.html` exists in the root, run the **dashboard-omnistate** skill immediately to refresh the data.
7. **Report:** "✅ Snapshot saved. [N] tasks archived. Memory optimized. ✅ Dashboard updated."
