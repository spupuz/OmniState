---
name: start-session
description: At the beginning of the session, loads only the project summary and task history to start the context in economy mode.
---
# Start Session (Economy)

**SKILL GOAL:** Start the work session by minimizing the context window to save tokens and loading only the "persistent memory" of the project.

**GLOBAL RULES:**
- All interactions and outputs MUST ALWAYS be strictly in English.

## Instructions for Antigravity:

1. **Do not analyze the entire codebase!** Instead, check if the following files exist in the root of the current project:
   - `project-summary.md`
   - `tasks-history.json`
   - `antigravity.config.json`
2. If these files **do not exist**, suggest the user create them by executing `/cost-setup`.
3. If the files **exist**, review the content of `project-summary.md` and the last session chunk if available (in the `chunks/` folder).
4. Show the user a summary in ENGLISH:
   - "Welcome back! I have loaded your persistent memory."
   - Provide a list of **Open Tasks** (read from `tasks-history.json`).
5. Indicate to the user that you are ready to work on the current specifications. **Removal of unnecessary context approved**. From this moment on, you will only operate with the precise target indicated by the user, without blindly reading the entirety of the repo unless explicitly requested.
