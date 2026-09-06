#!/usr/bin/env python3
"""collect-dashboard-data.py — Collects real project data for OmniState dashboard
Reads: tasks-history.json, tasks-archive.json, chunks/, project-summary.md, omni_cost.json
Writes: dashboard-data.json (used by dashboard.html)
"""
import json
import os
import sys
import re
from pathlib import Path
from datetime import datetime, timezone

def collect(project_dir: str = ".", output_file: str = "dashboard-data.json"):
    project = Path(project_dir).resolve()
    tasks_history = project / "tasks-history.json"
    tasks_archive = project / "tasks-archive.json"
    project_summary = project / "project-summary.md"
    omni_cost = project / "omni_cost.json"
    chunks_dir = project / "chunks"
    config_file = project / "omnistate.config.json"

    def load_json(path):
        try:
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                return json.load(f)
        except Exception:
            return {}

    def count_words(path):
        try:
            count = 0
            with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    count += len(line.split())
            return count
        except Exception:
            return 0

    # BOLT OPTIMIZATION: Cache config JSON load to prevent redundant disk reads later in script
    cfg = load_json(config_file)

    # 1. Project name
    project_name = "Unknown Project"
    if project_summary.exists():
        try:
            with open(project_summary, 'r', encoding='utf-8', errors='ignore') as f:
                for i, line in enumerate(f):
                    if i >= 5: break
                    m = re.match(r'^#\s+(.+)', line)
                    if m:
                        project_name = m.group(1).strip()
                        break
        except Exception:
            pass
    if project_name == "Unknown Project":
        project_name = cfg.get("project_name", "") or project.name

    # 2. Task counts
    history = load_json(tasks_history)
    tasks = history.get("tasks", [])
    total_tasks = len(tasks)

    active_tasks = 0
    done_tasks = 0
    for t in tasks:
        s = t.get("status")
        if s == "todo":
            active_tasks += 1
        elif s == "done":
            done_tasks += 1

    archive = load_json(tasks_archive)
    archived_tasks = len(archive.get("tasks", []))

    # 3. Snapshots
    chunks = []
    if chunks_dir.exists():
        chunks = sorted(chunks_dir.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
    snapshots = len(chunks)

    # 4. Token savings
    # Cache word counts per chunk to avoid redundant disk reads when building chart data in section 5
    chunk_word_counts = {f: count_words(f) for f in chunks}
    total_words = sum(chunk_word_counts.values())
    total_words += count_words(tasks_archive)
    token_saved = int(total_words * 1.3) + (snapshots * 4000)
    token_saved_k = max(token_saved // 1000, 1 if token_saved > 0 else 0)

    # 5. Chart data (cumulative, oldest first)
    chart_data = []
    cumulative = 0
    for f in reversed(chunks[:5]):
        words = chunk_word_counts.get(f)
        if words is None:
            words = count_words(f)
        cumulative += int(words * 1.3) + 4000
        chart_data.append(cumulative // 1000)

    # 6. Timeline
    timeline = []
    for f in chunks[:5]:
        mtime = datetime.fromtimestamp(f.stat().st_mtime)
        date_str = mtime.strftime("%b %d")
        label = "Session"
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as file_obj:
                for i, line in enumerate(file_obj):
                    if i >= 3: break
                    m = re.match(r'^#\s+(.+)', line)
                    if m:
                        label = m.group(1).strip()[:40]
                        break
        except Exception:
            pass
        timeline.append({"date": date_str, "label": label, "text": "Session chunk captured"})

    # 7. Cost data
    cost = load_json(omni_cost)
    cost_total = cost.get("total_cost", "0.00")
    cost_by_model = cost.get("by_model", {})

    # 8. Architecture
    architecture = []
    if project_summary.exists():
        in_modules = False
        try:
            with open(project_summary, 'r', encoding='utf-8', errors='ignore') as f:
                for line in f:
                    if "odule" in line:
                        in_modules = True
                        continue
                    if in_modules:
                        m = re.match(r'^\s*-\s*`([^`]+)`\s*:\s*(.*)', line.strip())
                        if m:
                            architecture.append({
                                "role": m.group(1).split("/")[-1][:20],
                                "text": m.group(2).strip()[:80]
                            })
                        elif line.strip() and not line.startswith(" ") and not line.startswith("-"):
                            break
        except Exception:
            pass
    if not architecture:
        architecture = [{"role": "Project", "text": "See project-summary.md"}]

    # Build output
    data = {
        "projectName": project_name,
        "version": cfg.get("omnistate_version", "1.5.0"),
        "activeTasks": active_tasks,
        "totalTasks": total_tasks + archived_tasks,
        "archivedTasks": archived_tasks,
        "doneTasks": done_tasks,
        "snapshots": snapshots,
        "tokenSavings": f"{token_saved_k}k",
        "tokenSavingsRaw": token_saved,
        "costTotal": str(cost_total),
        "costByModel": cost_by_model,
        "lastUpdate": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "timeline": timeline,
        "architecture": architecture[:6],
        "chartData": chart_data,
    }

    # SECURE: escape '<' and '>' to prevent XSS vulnerability when injected into an HTML script block
    json_output = json.dumps(data, indent=2).replace("<", "\\u003c").replace(">", "\\u003e")
    Path(output_file).write_text(json_output)
    print(f"Dashboard data collected → {output_file}")
    print(f"  Project: {project_name}")
    print(f"  Active: {active_tasks} | Archived: {archived_tasks} | Snapshots: {snapshots}")
    print(f"  Token savings: ~{token_saved_k}k")

if __name__ == "__main__":
    project_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    output_file = sys.argv[2] if len(sys.argv) > 2 else "dashboard-data.json"
    collect(project_dir, output_file)
