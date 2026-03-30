---
name: snapshot-session
description: At the end of a session, creates a chunk summary, updates project-summary.md, and updates tasks for future sessions.
---
# Snapshot Session

**SKILL GOAL:** Save the work done in long-term memory to avoid having to recalculate or re-contextualize it in future sessions.

**GLOBAL RULES:**
- All written files, chunks and JSON tracking MUST ALWAYS be strictly in English.

## Instructions for Antigravity:

1. **Analyze the delta of changes:** Look at the files that have been modified during the session.
2. **Update project-summary.md:**
   - Append/update the current state of the architecture if there have been significant changes.
   - Do not replace it entirely, but update any changelog or list of decisions made. All in English.
3. **Update tasks-history.json:**
   - Mark completed tasks as "done".
   - Add any new tasks generated during the conversation as "open" or "todo". All notes in English.
4. **Create a Session Chunk:**
   - Create a file in the `chunks/` folder (make sure it exists). E.g. `chunks/session-YYYYMMDD-HHMM.md`.
   - Inside the chunk, write compactly what has been added/modified in English.
5. **Communicate completion:**
   - "Snapshot saved successfully. Summary and Tasks updated. You are ready to close or switch branches!"
