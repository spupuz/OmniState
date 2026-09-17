#!/bin/bash
# OmniState Update & Sync Script
# Universal installer for opencode, Antigravity, Kilocode, and any AI coding tool
# Auto-detects installed platforms and syncs skills to all of them

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION=$(cat "$SCRIPT_DIR/VERSION.txt" 2>/dev/null | tr -d '[:space:]' || echo "1.5.0")
PLUGIN_NAME="omnistate"
REPO_URL="https://github.com/spupuz/OmniState.git"

# Memory files to protect from git
MEMORY_FILES=(
    "omnistate.config.json"
    "antigravity.config.json"
    "project-summary.md"
    "tasks-history.json"
    "tasks-archive.json"
    "AGENTS.md"
    "AI_POLICY.md"
    "CONTEXT.md"
    "omnistate-dashboard.html"
    "/omnistate-dashboard.html"
    "chunks/"
)

# IDE directories to protect
IDE_DIRS=(".opencode/" ".kilo/" ".agents/" ".omnistate/" ".roo/")

# ── Platform Detection ─────────────────────────────────────────────────────────
# Returns list of detected platform names
detect_platforms() {
    local platforms=()

    # opencode
    if [ -d "$HOME/.config/opencode" ] || command -v opencode &>/dev/null; then
        platforms+=("opencode")
    fi

    # Antigravity / Gemini
    if [ -d "$HOME/.gemini/antigravity" ]; then
        platforms+=("antigravity")
    fi

    # Kilocode
    if [ -d "$HOME/.kilo" ] || [ -d "$HOME/.kilocode" ]; then
        platforms+=("kilocode")
    fi

    # Roo Code
    if [ -d "$HOME/.roo" ]; then
        platforms+=("roo")
    fi

    # Claude Code / agents
    if [ -d "$HOME/.claude" ] || [ -d "$HOME/.agents" ]; then
        platforms+=("agents")
    fi

    echo "${platforms[@]}"
}

# Get skill install paths for a platform
get_skill_dirs() {
    local platform="$1"
    case "$platform" in
        opencode)
            echo "$HOME/.agents/skills" "$HOME/.config/opencode/skills"
            ;;
        antigravity)
            echo "$HOME/.gemini/antigravity/plugins/$PLUGIN_NAME/dist/skills"
            ;;
        kilocode)
            echo "$HOME/.kilo/commands"
            ;;
        roo)
            echo "$HOME/.roo/commands"
            ;;
        agents)
            echo "$HOME/.agents/skills" "$HOME/.claude/skills"
            ;;
    esac
}

# ── Logging ────────────────────────────────────────────────────────────────────
SILENT=false
log() { [ "$SILENT" = false ] && echo -e "$1" || true; }
info() { log "\033[0;36m$1\033[0m"; }
ok() { log "\033[0;32m$1\033[0m"; }
warn() { log "\033[0;33m$1\033[0m"; }
err() { log "\033[0;31m$1\033[0m"; }

# ── Helpers ────────────────────────────────────────────────────────────────────
inject_version() {
    local file="$1"
    local version="$2"
    if [ -f "$file" ]; then
        sed -i "s/{{VERSION}}/$version/g" "$file"
    fi
}

# Get source directory for a platform (skill format vs workflow format)
get_platform_source() {
    local platform="$1"
    case "$platform" in
        opencode|agents|claude)
            echo ".opencode/skills"
            ;;
        antigravity|kilocode|roo)
            echo "dist/workflows"
            ;;
    esac
}

# Get destination directory for a platform in a project
get_platform_dest() {
    local platform="$1"
    case "$platform" in
        opencode)
            echo ".opencode/skills"
            ;;
        agents|claude)
            echo ".agents/skills"
            ;;
        antigravity)
            echo ".agents/workflows"
            ;;
        kilocode)
            echo ".kilo/commands"
            ;;
        roo)
            echo ".roo/commands"
            ;;
    esac
}

# Detect which platforms a specific project uses
detect_project_platforms() {
    local target="$1"
    local platforms=()

    # opencode
    if [ -f "$target/opencode.json" ] || [ -d "$target/.opencode" ]; then
        platforms+=("opencode")
    fi

    # kilocode
    if [ -d "$target/.kilo" ] || [ -f "$target/.kilo/config.json" ]; then
        platforms+=("kilocode")
    fi

    # agents (Claude Code, Antigravity)
    if [ -d "$target/.agent" ] || [ -d "$target/.agents" ]; then
        platforms+=("agents")
        # Antigravity usa .agents/workflows
        if [ -d "$target/.agents/workflows" ]; then
            platforms+=("antigravity")
        fi
    fi

    # roo
    if [ -d "$target/.roo" ]; then
        platforms+=("roo")
    fi

    echo "${platforms[@]}"
}

# Install skills for a specific platform with correct format
install_for_platform() {
    local platform="$1"
    local target="$2"
    local source_dir dest_dir

    source_dir=$(get_platform_source "$platform")
    dest_dir=$(get_platform_dest "$platform")

    if [ -z "$source_dir" ] || [ -z "$dest_dir" ]; then
        return
    fi

    local full_dest="$target/$dest_dir"
    mkdir -p "$full_dest"

    if [ -d "$SCRIPT_DIR/$source_dir" ]; then
        if [ "$platform" = "opencode" ] || [ "$platform" = "agents" ] || [ "$platform" = "claude" ]; then
            # Formato skill: copia sottodirectory con SKILL.md
            cp -a "$SCRIPT_DIR/$source_dir/"* "$full_dest/"
        else
            # Formato workflow: copia solo file .md piatti
            local files=("$SCRIPT_DIR/$source_dir/"*.md)
            if [ -f "${files[0]}" ]; then
                cp "${files[@]}" "$full_dest/"
            fi
        fi
    fi
}

# ── Actions ────────────────────────────────────────────────────────────────────

sync_to_project() {
    local target="$1"
    [ ! -d "$target" ] && return

    # Migrate legacy config if present
    if [ -f "$SCRIPT_DIR/migrate.sh" ] && [ -f "$target/antigravity.config.json" ]; then
        bash "$SCRIPT_DIR/migrate.sh" --silent "$target"
    fi

    info "Syncing OmniState to $target ..."

    # Detect platforms from project
    local project_platforms
    project_platforms=$(detect_project_platforms "$target")

    # Detect global platforms
    local global_platforms
    global_platforms=$(detect_platforms)

    # Combine (project has priority)
    local all_platforms
    all_platforms=$(echo "$project_platforms $global_platforms" | tr ' ' '\n' | sort -u)

    # Install skills for each detected platform with correct format
    for platform in $all_platforms; do
        install_for_platform "$platform" "$target"
    done

    # Sync templates locally
    if [ -d "$SCRIPT_DIR/dist/templates" ]; then
        for dir in ".agents" ".agent" ".opencode"; do
            mkdir -p "$target/$dir/templates"
            cp -a "$SCRIPT_DIR/dist/templates/"* "$target/$dir/templates/"
        done
        # Inject version into templates
        for dir in ".agents" ".agent" ".opencode"; do
            if [ -f "$target/$dir/templates/omnistate.config.json" ]; then
                inject_version "$target/$dir/templates/omnistate.config.json" "$VERSION"
            fi
            if [ -f "$target/$dir/templates/dashboard.html" ]; then
                inject_version "$target/$dir/templates/dashboard.html" "$VERSION"
            fi
        done
    fi

    # Copy omnistate.config.json to project root if not present
    if [ ! -f "$target/omnistate.config.json" ] && [ -f "$SCRIPT_DIR/dist/templates/omnistate.config.json" ]; then
        cp "$SCRIPT_DIR/dist/templates/omnistate.config.json" "$target/omnistate.config.json"
        inject_version "$target/omnistate.config.json" "$VERSION"
    fi

    # Enforce git protection
    if [ -f "$target/.gitignore" ]; then
        local content
        content=$(<"$target/.gitignore")
        local content_with_newline=$'\n'"$content"
        local additions=()

        for pattern in "${MEMORY_FILES[@]}" "${IDE_DIRS[@]}"; do
            if [[ ! "$content_with_newline" == *$'\n'"$pattern"* ]]; then
                additions+=("$pattern")
            fi
        done

        if [ ${#additions[@]} -gt 0 ]; then
            if [ -L "$target/.gitignore" ]; then
                warn "Symlink detected for .gitignore. Skipping git protection to prevent arbitrary file read."
                return 0
            fi
            # SECURITY: use mktemp and mv to prevent symlink traversal and ensure atomic updates
            local tmp_file
            tmp_file=$(mktemp "$(dirname "$target/.gitignore")/.tmp.XXXXXX")
            if [ -f "$target/.gitignore" ]; then
                cat "$target/.gitignore" > "$tmp_file"
            fi
            printf "\n%s\n" "${additions[@]}" >> "$tmp_file"
            chmod 644 "$tmp_file"
            mv "$tmp_file" "$target/.gitignore"
        fi
    fi

    ok "Synced to $target"
}

auto_update() {
    # Check for updates (24h throttle)
    local state_dir="$SCRIPT_DIR/.omnistate"
    mkdir -p "$state_dir"
    local check_file="$state_dir/.last_update_check"
    local now
    now=$(date +%s)
    local last_check=0
    [ -f "$check_file" ] && last_check=$(<"$check_file")
    last_check=${last_check//[!0-9]/}
    last_check=${last_check:-0}

    if (( now - last_check > 86400 )); then
        warn "Checking for OmniState updates ..."
        if [ -d "$SCRIPT_DIR/.git" ] && command -v git &>/dev/null; then
            cd "$SCRIPT_DIR"
            local remote_hash local_hash
            remote_hash=$(git ls-remote origin -h refs/heads/main 2>/dev/null | awk '{print $1}')
            local_hash=$(git rev-parse HEAD 2>/dev/null)

            if [ -n "$remote_hash" ] && [ "$remote_hash" != "$local_hash" ]; then
                info "New version available! Updating ..."
                git pull origin main --quiet
                ok "Updated to $(cat "$SCRIPT_DIR/VERSION.txt" | tr -d '[:space:]')"
            fi
        fi
        # SECURITY: use mktemp and mv to prevent symlink traversal and ensure atomic updates
        local tmp_file
        tmp_file=$(mktemp "$(dirname "$check_file")/.tmp.XXXXXX")
        echo "$now" > "$tmp_file"
        chmod 644 "$tmp_file"
        mv "$tmp_file" "$check_file"
    fi
}

install_global() {
    info "Installing OmniState v$VERSION ..."

    # Auto-update first
    auto_update

    # Detect platforms
    local platforms
    platforms=$(detect_platforms)

    if [ -z "$platforms" ]; then
        warn "No supported AI coding tools detected."
        warn "Skills are available locally in: $SCRIPT_DIR/.opencode/skills/"
        warn "Add this path to your AI tool's skill directory."
    else
        for platform in $platforms; do
            info "Installing for $platform ..."
            local source_dir
            source_dir=$(get_platform_source "$platform")
            local dirs
            dirs=$(get_skill_dirs "$platform")
            for dir in $dirs; do
                if [ -n "$dir" ]; then
                    mkdir -p "$dir"
                    if [ "$platform" = "opencode" ] || [ "$platform" = "agents" ] || [ "$platform" = "claude" ]; then
                        # Formato skill: copia sottodirectory
                        cp -a "$SCRIPT_DIR/$source_dir/"* "$dir/"
                    else
                        # Formato workflow: copia solo file .md piatti
                        local files=("$SCRIPT_DIR/$source_dir/"*.md)
                        if [ -f "${files[0]}" ]; then
                            cp "${files[@]}" "$dir/"
                        fi
                    fi
                    ok "  -> $dir"
                fi
            done
        done
    fi

    # Always ensure local .opencode/skills is populated
    mkdir -p "$SCRIPT_DIR/.opencode/skills"
    # Optimization: Batch array copy to prevent N+1 process spawning overhead
    local skill_dirs=("$SCRIPT_DIR/dist/skills"/*/)
    if [ -d "${skill_dirs[0]}" ]; then
        local safe_dirs=()
        for dir in "${skill_dirs[@]}"; do
            safe_dirs+=("${dir%/}")
        done
        cp -a "${safe_dirs[@]}" "$SCRIPT_DIR/.opencode/skills/"
    fi

    ok "OmniState v$VERSION installed successfully!"
    echo ""
    echo "  Skills installed to: ~/.agents/skills/"
    echo "  To use in a project: run 'bash update.sh <project-path>'"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────────
ACTION="install"
PROJECT_ROOT=""

while [ $# -gt 0 ]; do
    case "$1" in
        --auto)    ACTION="auto"; shift; PROJECT_ROOT="${1:-}"; shift ;;
        --sync)    ACTION="sync"; shift; PROJECT_ROOT="${1:-}"; shift ;;
        --check)   ACTION="check"; shift ;;
        --silent)  SILENT=true; shift ;;
        --help|-h)
            echo "Usage: update.sh [--auto <project>] [--sync <project>] [--check] [--silent]"
            echo "  --auto   Auto-update + sync to project"
            echo "  --sync   Sync skills to project only"
            echo "  --check  Check for updates (exit 1 if available)"
            echo "  --silent Suppress output"
            exit 0
            ;;
        *)         PROJECT_ROOT="$1"; shift ;;
    esac
done

case "$ACTION" in
    install) install_global ;;
    auto)
        auto_update
        [ -n "$PROJECT_ROOT" ] && sync_to_project "$PROJECT_ROOT"
        ;;
    sync)
        [ -n "$PROJECT_ROOT" ] && sync_to_project "$PROJECT_ROOT"
        ;;
    check)
        if [ -d "$SCRIPT_DIR/.git" ]; then
            cd "$SCRIPT_DIR"
            remote_hash=$(git ls-remote origin -h refs/heads/main 2>/dev/null | awk '{print $1}')
            local_hash=$(git rev-parse HEAD 2>/dev/null)
            [ "$remote_hash" != "$local_hash" ] && exit 1 || exit 0
        fi
        exit 0
        ;;
esac
