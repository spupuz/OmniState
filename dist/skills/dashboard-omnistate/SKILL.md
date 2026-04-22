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
   - **Token Savings Estimate**: Calculate this realistically by estimating the length of the data preserved and avoided. For example, sum the word count of the `chunks/` and `tasks-archive.json`, and multiply by an average ratio (e.g., ~1.3 tokens per word), plus estimate the context overhead saved per interaction. Provide the final realistic result in 'k'.
   - **Chart Data**: Instead of synthetic growth, calculate the real cumulative token savings over time (array of integers) mapped to actual chronological snapshot (chunks) dates.
   - **Task Accuracy**: Ensure `totalTasks`, `activeTasks`, and `archivedTasks` accurately reflect the exact real count extracted from the JSON files.
   - **Timeline**: Map the last 5 chunks to `{date, label, text}` objects realistically using their actual filesystem timestamps and contents.
3. **Template Injection:**
   - **Check Local Template**: If `.agent/templates/dashboard.html` exists, use it.
   - **Fallback**: Use `~/.gemini/antigravity/plugins/omnistate/templates/dashboard.html`.
   - Stringify the extracted data into a JSON object.
   - Replace the `{{DATA}}` placeholder in the template with the JSON.
4. **Output:**
   - Write the resulting file to `omnistate-dashboard.html` in the project root.
   - **Also generate a rich artifact** in the session showing the dashboard HTML content.
5. **Report:** "✅ Visual Dashboard updated. Open `omnistate-dashboard.html` (ignored by git) to view progress."
