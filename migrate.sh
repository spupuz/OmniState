#!/bin/bash
# OmniState Migration Script
# Migrates antigravity.config.json → omnistate.config.json
# Safe for git projects - backups stored in .omnistate/backups/

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION=$(cat "$SCRIPT_DIR/VERSION.txt" 2>/dev/null | tr -d '[:space:]' || echo "1.5.0")

# ── Logging ────────────────────────────────────────────────────────────────────
SILENT=false
log() { [ "$SILENT" = false ] && echo -e "$1" || true; }
info() { log "\033[0;36m$1\033[0m"; }
ok() { log "\033[0;32m$1\033[0m"; }
warn() { log "\033[0;33m$1\033[0m"; }
err() { log "\033[0;31m$1\033[0m"; }

# ── Migration Logic ────────────────────────────────────────────────────────────
migrate_project() {
    local target="${1:-.}"
    target="$(cd "$target" 2>/dev/null && pwd)" || return 1

    local old_config="$target/antigravity.config.json"
    local new_config="$target/omnistate.config.json"
    local backup_dir="$target/.omnistate/backups"

    # Skip if no old config exists
    if [ ! -f "$old_config" ]; then
        return 0
    fi

    info "Detected legacy config: antigravity.config.json"

    # If new config already exists, ask user
    if [ -f "$new_config" ]; then
        warn "omnistate.config.json already exists."
        if [ "$FORCE" != true ]; then
            read -p "Overwrite existing config? [y/N] " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                warn "Skipping migration. Old config preserved."
                return 0
            fi
        fi
    fi

    # Create backup directory
    mkdir -p "$backup_dir"

    # Create backup with timestamp
    local timestamp
    timestamp=$(date +%Y%m%d-%H%M)
    local backup_file="$backup_dir/antigravity.config.json.$timestamp.bak"
    # SECURITY: use mktemp and mv to prevent symlink traversal and ensure atomic updates
    local tmp_backup_dir
    tmp_backup_dir=$(mktemp -d "$(dirname "$backup_file")/.tmp.XXXXXX")
    cp -a "$old_config" "$tmp_backup_dir/backup"
    # Securely preserve original file attributes without following symlinks
    if chmod --help 2>&1 | grep -q "\-\-reference"; then
        chmod --reference="$old_config" "$tmp_backup_dir/backup" 2>/dev/null || true
        chown --reference="$old_config" "$tmp_backup_dir/backup" 2>/dev/null || true
    elif command -v stat &>/dev/null; then
        chmod "$(stat -f "%A" "$old_config" 2>/dev/null)" "$tmp_backup_dir/backup" 2>/dev/null || true
        chown "$(stat -f "%u:%g" "$old_config" 2>/dev/null)" "$tmp_backup_dir/backup" 2>/dev/null || true
    fi
    touch -r "$old_config" "$tmp_backup_dir/backup" 2>/dev/null || true
    mv "$tmp_backup_dir/backup" "$backup_file"
    rmdir "$tmp_backup_dir"
    ok "Backup created: $backup_file"

    # Migrate schema
    if command -v jq &>/dev/null; then
        # Use jq for proper JSON transformation
        # SECURITY: use mktemp and mv to prevent symlink traversal and ensure atomic updates
        tmp_file=$(mktemp "$(dirname "$new_config")/.tmp.XXXXXX")
        jq --arg version "$VERSION" '
            # Remove compression_level
            del(.optimization.compression_level) |
            # Add project_name if missing
            if has("project_name") then . else . + {"project_name": ""} end |
            # Empty hardcoded model values
            .models.preferred_lite = "" |
            .models.preferred_pro = "" |
            # Update version
            .omnistate_version = $version
        ' "$old_config" > "$tmp_file"
        if chmod --help 2>&1 | grep -q "\-\-reference"; then
            chmod --reference="$old_config" "$tmp_file" 2>/dev/null || true
            chown --reference="$old_config" "$tmp_file" 2>/dev/null || true
        elif command -v stat &>/dev/null; then
            chmod "$(stat -f "%A" "$old_config" 2>/dev/null)" "$tmp_file" 2>/dev/null || true
            chown "$(stat -f "%u:%g" "$old_config" 2>/dev/null)" "$tmp_file" 2>/dev/null || true
        fi
        touch -r "$old_config" "$tmp_file" 2>/dev/null || true
        mv "$tmp_file" "$new_config"
    else
        # Fallback: copy and warn about manual cleanup
        # SECURITY: use mktemp and mv to prevent symlink traversal and ensure atomic updates
        tmp_file=$(mktemp "$(dirname "$new_config")/.tmp.XXXXXX")
        cat "$old_config" > "$tmp_file"
        if chmod --help 2>&1 | grep -q "\-\-reference"; then
            chmod --reference="$old_config" "$tmp_file" 2>/dev/null || true
            chown --reference="$old_config" "$tmp_file" 2>/dev/null || true
        elif command -v stat &>/dev/null; then
            chmod "$(stat -f "%A" "$old_config" 2>/dev/null)" "$tmp_file" 2>/dev/null || true
            chown "$(stat -f "%u:%g" "$old_config" 2>/dev/null)" "$tmp_file" 2>/dev/null || true
        fi
        touch -r "$old_config" "$tmp_file" 2>/dev/null || true
        mv "$tmp_file" "$new_config"
        warn "jq not found - copied as-is. Manual cleanup needed:"
        warn "  - Remove 'compression_level' from optimization"
        warn "  - Add 'project_name' field"
        warn "  - Empty model values (preferred_lite, preferred_pro)"
    fi

    # Remove old config
    rm -f "$old_config"
    ok "Migrated: antigravity.config.json → omnistate.config.json"

    # Ensure old config is in .gitignore
    local gitignore="$target/.gitignore"
    if [ -f "$gitignore" ]; then
        if ! grep -q "antigravity.config.json" "$gitignore" 2>/dev/null; then
            echo "antigravity.config.json" >> "$gitignore"
            ok "Added antigravity.config.json to .gitignore"
        fi
    fi

    return 0
}

# ── Main ───────────────────────────────────────────────────────────────────────
FORCE=false
SILENT=false
TARGET="."

while [ $# -gt 0 ]; do
    case "$1" in
        --force)   FORCE=true; shift ;;
        --silent)  SILENT=true; shift ;;
        --help|-h)
            echo "Usage: migrate.sh [OPTIONS] [PROJECT_ROOT]"
            echo ""
            echo "Migrates antigravity.config.json to omnistate.config.json"
            echo ""
            echo "Options:"
            echo "  --force    Skip confirmation prompts"
            echo "  --silent   Suppress output"
            echo "  --help     Show this help"
            echo ""
            echo "Examples:"
            echo "  migrate.sh                  # Migrate current directory"
            echo "  migrate.sh /path/to/project # Migrate specific project"
            echo "  migrate.sh --force .        # Migrate without prompts"
            exit 0
            ;;
        *)         TARGET="$1"; shift ;;
    esac
done

migrate_project "$TARGET"
