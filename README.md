# OmniState Plugin for Antigravity

This plugin installs a **Persistent Memory** and **Credit Savings/Model Optimization** system.

It is designed to limit context window ingestion (reading the whole codebase at the start of a session) and allows you to track your tasks efficiently and affordably.

## How to Install (Globally on Antigravity)

Since you specified that this must be applicable to **ALL PROJECTS**, you must ensure Antigravity sees this plugin globally.

1. **Copy or move** this entire folder (`omnistate-plugin`) inside the Antigravity global plugins directory, generally:
   - `C:\Users\<YourUser>\.gemini\antigravity\plugins\` on Windows.
   *(If the plugins folder doesn't exist, you can create it and put it in there)*

2. Once placed, Antigravity will detect the new Skills for any workspace you open.

## How to Use in Any Project

Once installed, follow this basic workflow in your projects:

### 1. Initialization (One-time per project)
In your project run or ask Antigravity:
> "Execute the `/cost-setup` skill" or copy the files from the `templates/` folder of this plugin into the root of your new project.
This will set up the minimum memory files and update your `.gitignore`:
- `project-summary.md`
- `tasks-history.json`
- `chunks/` (folder)

### 2. At the beginning of a new session
As soon as you open a workspace in Antigravity to continue working, instead of having Antigravity read the entire repo, type or execute:
> "Execute `/start-session`"
This will ensure the agent reads **only** the summaries and the tasks left open. You will save thousands of tokens and Antigravity will get into the core of the context much faster.

### 3. At the end of a session
Before logging off or changing branches, execute:
> "Execute `/snapshot-session`"
The agent will summarize the actions taken in a chunk file in `chunks/` and update the `project-summary.md` and JSON tasks. This way, your memory will be preserved in the next session!

### 4. Automatic Model Switch / Cost Savings
With the cost-setup option enabled, the agent will try to warn you if you are wasting credits on trivial operations by reminding you to change the model in the IDE settings.
*(You can set up a Lite or Flash model for basic readings/refactoring)*
