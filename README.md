# OmniState Plugin for Antigravity

This plugin installs a **Persistent Memory** and **Credit Savings / Model Optimization** system for your AI coding sessions.
Inspired by the **[Agora-Code](https://github.com/thebnbrkr/agora-code)** project, OmniState adapts and extends those concepts for use as a global Antigravity plugin.

It is designed to limit context window ingestion (saving thousands of tokens) by allowing the agent to track your tasks and progress through a dedicated summary.

## 🚀 How to Install (Automated)

Since OmniState is a global plugin, you only need to install it once to make it available in **ALL YOUR PROJECTS**.

1. **Clone or download** this repository folder into any location on your PC.
2. Run the automated installer:
   - **Windows:** Right-click **`update.ps1`** and select *Run with PowerShell*.
   - **Linux:** Execute **`bash update.sh`** from the terminal.
3. The script will automatically:
   - Synchronize the latest version from GitHub.
   - Install/Update the plugin into the global Antigravity directory (`~/.gemini/antigravity/plugins/omnistate`).

**Done!** Antigravity will now recognize the new skills and slash commands in any project you open.

## 🛠️ How to Use in Any Project

Once installed globally, you can interact with OmniState using **Slash Commands** (`/`) or by asking for the specific **Skills**.

### 1. Initialization (One-time per project)
Type this command in any workspace:
> **/cost-setup**
This will set up the minimum memory files and update your `.gitignore`:
- `project-summary.md` (Human-readable summary of the project state)
- `tasks-history.json` (Structured JSON of open/closed tasks)
- `chunks/` (Folder containing summarized logs of previous sessions)

### 2. At the beginning of a new session
Instead of letting Antigravity read the entire repo, type:
> **/start-session**
The agent will read only the summaries and open tasks. This ensures you start working instantly with minimal token usage.

### 3. At the end of a session
Before closing the IDE or changing tasks, type:
> **/snapshot-session**
The agent will:
- Summarize the work done.
- Create a new "chunk" log.
- Update `project-summary.md` and the task list.
- Keep your memory preserved for the next time!

### 4. Automatic Cost Savings
With the cost-setup active, the agent will monitor your model selection. If you are using an expensive model (like Gemini Pro) for routine tasks (refactoring, documentation), it will gently remind you to switch to a **Lite/Flash** model to save credits.

---
*OmniState - Persistent Memory and Efficiency for Antigravity.*
