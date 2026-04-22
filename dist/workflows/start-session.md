---
description: Starts the session by loading only the project summary to save context window tokens.
---
## File Verification
- Check for README.md ($REPO_DIR/README.md)
- Check for AGENTS.md ($REPO_DIR/AGENTS.md)
- Check for AI_POLICY.md ($REPO_DIR/AI_POLICY.md)
- Check for CONTEXT.md ($REPO_DIR/CONTEXT.md)
- Check for skills.md ($REPO_DIR/dist/scripts/skills.md)

# Verify file existence
if [ ! -f "$REPO_DIR/README.md" ]; then
  echo "Error: README.md not found. Creating placeholder..."
  echo "# Project Documentation" > "$REPO_DIR/README.md"
fi

if [ ! -f "$REPO_DIR/AGENTS.md" ]; then
  echo "Error: AGENTS.md not found. Creating placeholder..."
  echo "# Agent Definitions" > "$REPO_DIR/AGENTS.md"
fi

if [ ! -f "$REPO_DIR/AI_POLICY.md" ]; then
  echo "Error: AI_POLICY.md not found. Creating placeholder..."
  echo "# AI Interaction Policy" > "$REPO_DIR/AI_POLICY.md"
fi

if [ ! -f "$REPO_DIR/CONTEXT.md" ]; then
  echo "Error: CONTEXT.md not found. Creating placeholder..."
  echo "# Project Context" > "$REPO_DIR/CONTEXT.md"
fi

if [ ! -f "$REPO_DIR/dist/scripts/skills.md" ]; then
  echo "Error: skills.md not found. Creating placeholder..."
  echo "# Skills Definition" > "$REPO_DIR/dist/scripts/skills.md"
fi

## Proactive Documentation
Analyze the project structure, technology stack, and existing documentation.
Populate `CONTEXT.md`, `AGENTS.md`, and `AI_POLICY.md` with relevant information if they are new or contain placeholders.
Ensure they reflect the current state of the repository.

## Execute Session Skill
Execute the **start-session** skill.
