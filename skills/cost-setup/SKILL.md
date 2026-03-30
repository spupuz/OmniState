---
name: cost-setup
description: Sets the rules for auto-switching the intelligence level (model), saving credits, and ignoring files via git.
---
# Cost Setup and Model Switch

**SKILL GOAL:** Guide Antigravity and the user towards choosing the most economical but adequate AI model for the task, while ensuring local memory files do not clutter the repository.

**GLOBAL RULES:**
- All conversation, written files, outputs, and JSON tracking MUST ALWAYS be strictly in English.
- None of the persistent memory files should ever be pushed to Git or GitHub.

## Instructions for Antigravity:

1. When the user executes `/cost-setup`, you should generate or read the `antigravity.config.json` file in the project root.
2. **Mandatory Git Protection:** You MUST physically write to or append to the `.gitignore` file in the root of the project to ensure these files are never tracked. Add exactly these lines:
   ```text
   # OmniState Tracking
   antigravity.config.json
   project-summary.md
   tasks-history.json
   chunks/
   omnistate-plugin/
   ```
3. Check and load the base memory files using the provided templates if they are missing.
4. Ask the user to confirm the rules: "Do you want me to remind you to switch to a 'Lite' model when doing simple tasks like refactoring, generating comments, or writing small tests?"
5. From now on, when the user asks you for an exploratory or "routine" task, if the current model is very "expensive", you must point out:
   > 💡 **Cost Note:** You are using the most powerful model for a simple operation. To save money, you could change the model in the system settings to a faster/cheaper one.
6. Use your judgment based on task complexity for the model routing advice.
