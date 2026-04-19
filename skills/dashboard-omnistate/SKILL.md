---
name: dashboard-omnistate
description: Generates or updates the interactive Visual Dashboard for the project.
---
# Dashboard Generator (v1.1.0)

**SKILL GOAL:** Extract project metrics and status to generate a premium-looking Visual Dashboard.

**ENFORCEMENT:**
- Add `/omnistate-dashboard.html` to `.gitignore` before writing the file.

**INSTRUCTIONS:**

1. **Information Extraction:**
   - Read `project-summary.md` -> Extract Project Name, Main Tech Stack, and Modules.
   - Read `tasks-history.json` -> Count total tasks and "todo" tasks.
   - Read `tasks-archive.json` -> Count total archived tasks.
   - List `chunks/` folder -> Count files and extract metadata (dates/labels) from the last 5 chunks.
   - Read `antigravity.config.json` -> Get current OmniState version.
2. **Data Processing:**
   - **Token Savings Estimate**: Calculate: `(Snapshots * 10) + (ArchivedTasks * 5)` (result in 'k').
   - **Chart Data**: Generate a synthetic growth array of savings based on the number of snapshots.
   - **Timeline**: Map the last 5 chunks to `{date, label, text}` objects.
3. **Template Injection:**
   - **Check Local Template**: If `.agent/templates/dashboard.html` exists, use it.
   - **Fallback**: Use `~/.gemini/antigravity/plugins/omnistate/templates/dashboard.html`.
   - Stringify the extracted data into a JSON object.
   - Replace the `{{DATA}}` placeholder in the template with the JSON.
4. **Output:**
   - Write the resulting file to `omnistate-dashboard.html` in the project root.
   - **Also generate a rich artifact** in the session showing the dashboard HTML content.
5. **Report:** "✅ Visual Dashboard updated. Open `omnistate-dashboard.html` (ignored by git) to view progress."
