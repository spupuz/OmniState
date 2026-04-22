---
description: Saves a snapshot of the current work and updates the persistent memory and task history.
---
## File Verification
- Check for README.md ($REPO_DIR/README.md)
- Check for AGENTS.md ($REPO_DIR/AGENTS.md)
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

if [ ! -f "$REPO_DIR/dist/scripts/skills.md" ]; then
  echo "Error: skills.md not found. Creating placeholder..."
  echo "# Skills Definition" > "$REPO_DIR/dist/scripts/skills.md"
fi

## Execute Session Skill
Execute the **snapshot-session** skill.
