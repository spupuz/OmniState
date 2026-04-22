---
description: Saves a snapshot of the current work and updates the persistent memory and task history.
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

## Documentation Update
Review the changes made during this session.
Update `CONTEXT.md` (architecture), `AGENTS.md` (roles), and `AI_POLICY.md` (rules) if the work performed has impacted these areas.

## Execute Session Skill
Execute the **snapshot-session** skill.
