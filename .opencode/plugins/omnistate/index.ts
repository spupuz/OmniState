import { Plugin } from "@opencode/plugin"

const OMNISTATE_URL = "http://localhost:8347"

interface RememberBody {
  text: string
  scope?: string
  tags?: string[]
  source?: string
  project?: string
}

interface SessionStartBody {
  project: string
}

interface SessionSnapshotBody {
  project: string
  summary?: string
}

interface TaskAddBody {
  project: string
  title: string
}

interface TaskUpdateBody {
  project: string
  task_id: number
  status: string
}

async function remember(url: string, body: RememberBody): Promise<void> {
  try {
    await fetch(`${url}/api/hooks/remember`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    })
  } catch {
    // OmniState server not reachable — silently skip
  }
}

export default Plugin.define({
  id: "omnistate",
  async setup(ctx) {
    const url = ctx.options?.url || OMNISTATE_URL
    const defaultProject = ctx.options?.project || ""

    // ---------- Prompt hook: auto-remember user messages ----------
    await ctx.session.hook("prompt", (event) => {
      const text = event.prompt?.text?.trim()
      if (!text) return
      // Skip very short prompts (noise): commands, confirmations, single words
      if (text.length < 10) return
      // Skip system-like prompts that are just tool results
      if (text.startsWith("<")) return

      void remember(url, {
        text,
        scope: "shared",
        tags: ["opencode-prompt"],
        source: "opencode-session",
        project: defaultProject,
      })
    })

    // ---------- Context hook: track tool usage ----------
    await ctx.session.hook("context", (event) => {
      const tools = event.tools
      if (!tools) return
      const used = Object.entries(tools)
        .filter(([, v]) => v)
        .map(([k]) => k)
      if (used.length === 0) return
      // Batch tool-usage as a single memory entry per session
      void remember(url, {
        text: `Tools used this session: ${used.join(", ")}`,
        scope: "shared",
        tags: ["opencode-tools"],
        source: "opencode-session",
      })
    })

    // ---------- Compaction hook: auto-snapshot ----------
    await ctx.session.hook("compaction", async (event) => {
      const summary = event.result?.summary
      if (!summary || summary.length < 20) return
      if (!defaultProject) return // need a project to snapshot into

      try {
        await fetch(`${url}/api/hooks/session/snapshot`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ project: defaultProject, summary } satisfies SessionSnapshotBody),
        })
      } catch {
        // silently skip
      }
    })

    // ---------- Event subscription: session lifecycle ----------
    const controller = new AbortController()
    void (async () => {
      for await (const event of ctx.event.subscribe({ signal: controller.signal })) {
        const type = (event as { type?: string }).type
        if (type === "session.create") {
          // Session started — could call session/start endpoint here
          // For now, just log (no console in production plugins)
        }
        if (type === "session.remove") {
          // Session ended — auto-snapshot if project is configured
          if (!defaultProject) continue
          try {
            await fetch(`${url}/api/hooks/session/snapshot`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ project: defaultProject } satisfies SessionSnapshotBody),
            })
          } catch {
            // silently skip
          }
        }
      }
    })()

    return () => controller.abort()
  },
})
