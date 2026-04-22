# OmniState Plugin for Antigravity (v1.1.1)

This plugin installs a **Persistent Memory** and **Credit Savings / Model Optimization** system for your AI coding sessions.
Inspired by the **[Agora-Code](https://github.com/thebnbrkr/agora-code)** project, OmniState adapts and extends those concepts for use as a global Antigravity plugin.

It is designed to limit context window ingestion (saving thousands of tokens) by allowing the agent to track your tasks and progress through a dedicated summary and automated background optimizations.

## 🚀 Key Features (v1.1.1 Evolution)

- **Automatic Background Sync**: OmniState now self-updates from GitHub and synchronizes workflows across all your projects automatically.
- **Visual Dashboard (UI)**: An elegant, high-fidelity local dashboard (`/dashboard-omnistate`) to visualize project state and token savings.
- **Intelligent Memory Archiving**: Automatically moves completed tasks to an archive to keep your active context as lean as possible.
- **Context Purge**: Forcefully cleans the AI's context window on startup to prevent "hallucinations" or distractions from previous files.
- **Dense Instructions**: Optimized skill logic to minimize token overhead during every interaction.

## 📦 How to Install (Automated)

Since OmniState is a global plugin, you only need to install it once to make it available in **ALL YOUR PROJECTS**.

1. **Clone or download** this repository folder into any location on your PC.
2. Run the automated installer:
   - **Windows:** Right-click **`update.ps1`** and select *Run with PowerShell*.
   - **Linux:** Execute **`bash update.sh`** from the terminal.
3. The script will automatically:
   - Synchronize the latest version from GitHub.
   - Install/Update the plugin into the global Antigravity directory (`~/.gemini/antigravity/plugins/omnistate`).

## 🛠️ How to Use in Any Project

Once installed globally, you can interact with OmniState using **Slash Commands** (`/`) or by asking for the specific **Skills**.

### 1. Initialization
Run:
> **/cost-setup**

This will set up the memory files and update your `.gitignore` to protect them from GitHub:
- `project-summary.md` (Architecture & State Index)
- `tasks-history.json` (Active tasks)
- `tasks-archive.json` (Legacy tasks - **New in v1.1.1**)
- `antigravity.config.json` (Configuration - **New in v1.1.1**)

### 2. At the start of a session
> **/start-session**

The agent performs a **Context Purge** and loads only the essential summaries. It also checks for updates in the background.

### 3. During or at the end of a session
> **/snapshot-session**

The agent:
- Creates a compacted "session chunk".
- **Auto-Archives** older completed tasks.
- Updates the **Distilled Summary** in your project summary file.
- Triggers a **Dashboard Refresh**.

### 4. Visual Dashboard
> **/dashboard-omnistate**

Generates a premium HTML dashboard (`omnistate-dashboard.html`) in your project root. Open it in a browser to see:
- Real-time task progress.
- Visual timeline of snapshots.
- **Estimated Token Savings** counter.

## 🌐 Universal Discovery (KI)
OmniState is integrated with Antigravity's **Knowledge Item (KI)** system. If slash commands are not visible, type **"OmniState activation"** to force initialization.

## 💻 SSH / Remote Host One-Liner
```bash
export REPO_DIR=~/OmniState; [ -d $REPO_DIR ] || git clone https://github.com/spupuz/OmniState.git $REPO_DIR; cd $REPO_DIR && git pull && bash update.sh
```

---
*OmniState - Engineered for Persistent Memory and Token-Efficient Development.*
# Estensioni di compatibilità multi-IDEA
1. VSCode - Supporto per Kilocode
1.1. Supporto per i workflow Kilocode in Vscode
1.2. Comandi condivisi tra Antigravity e Kilocode
