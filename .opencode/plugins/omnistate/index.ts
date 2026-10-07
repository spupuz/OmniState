/**
 * OmniState OpenCode plugin — automatic memory, zero cooperation required.
 *
 * The agent never reads instructions and never calls an MCP tool for this to
 * happen: the plugin receives the lifecycle itself and talks to the server
 * over fire-and-forget REST (`POST /api/hooks/*`).
 *
 *   session "context" hook  -> recall is injected into the system prompt
 *                              BEFORE the model runs (the whole point)
 *   session "prompt" hook   -> user prompts are remembered
 *   session "compaction"    -> snapshot before the transcript is compressed
 *   tool "execute.after"    -> edited files feed the snapshot summary
 *   event stream            -> snapshot on session.idle / session.deleted
 *
 * Config via environment (no `plugins` entry needed: `.opencode/plugins/` and
 * `~/.config/opencode/plugins/` are discovered automatically, so an explicit
 * entry would register the plugin twice):
 *
 *   OMNISTATE_URL     default http://localhost:8347
 *   OMNISTATE_TOKEN   default read from ~/.config/opencode/omnistate_token
 *   OMNISTATE_PROJECT default basename(ctx.location.project.canonical)
 *   OMNISTATE_TIMEOUT per-request timeout in ms (default 2000)
 */

import { Plugin } from "@opencode/plugin"
import { readFileSync } from "node:fs"
import { homedir, tmpdir } from "node:os"
import { basename, join } from "node:path"

const DEFAULT_URL = "http://localhost:8347"
const DEFAULT_TIMEOUT_MS = 2000
/** Below this a prompt is noise ("ok", "sì", "fai"). */
const MIN_PROMPT_CHARS = 25
/** Don't snapshot the same session more often than this; idle fires often. */
const IDLE_SNAPSHOT_COOLDOWN_MS = 10 * 60 * 1000
/** Recall is refetched at most once per session per window (context runs on
 *  every model call, including tool-driven continuations). */
const RECALL_CACHE_MS = 60 * 1000
const SYSTEM_MARK = "## OmniState memory"

function readToken(): string {
  if (process.env.OMNISTATE_TOKEN) return process.env.OMNISTATE_TOKEN.trim()
  const base = process.env.XDG_CONFIG_HOME || join(homedir(), ".config")
  for (const p of [join(base, "opencode", "omnistate_token"), join(tmpdir(), "opencode", "omnistate_token")]) {
    try {
      const v = readFileSync(p, "utf8").trim()
      if (v) return v
    } catch {
      // try next location
    }
  }
  return ""
}

type Recall = {
  open_tasks?: Array<{ id: number; title: string; status: string }>
  recent_memory?: Array<{ title: string; content: string }>
  recall?: Array<{ title: string; content: string }>
}

export default Plugin.define({
  id: "omnistate",
  async setup(ctx) {
    const url = (process.env.OMNISTATE_URL || DEFAULT_URL).replace(/\/+$/, "")
    const token = readToken()
    const timeoutMs = Number(process.env.OMNISTATE_TIMEOUT) || DEFAULT_TIMEOUT_MS

    const loc = ctx.location as unknown as {
      directory?: string
      project?: { canonical?: string }
    }
    const project =
      process.env.OMNISTATE_PROJECT || basename(loc?.project?.canonical || loc?.directory || "")

    const headers: Record<string, string> = { "Content-Type": "application/json" }
    if (token) headers["Authorization"] = `Bearer ${token}`

    /** Fire-and-forget. Never throws, never blocks the agent, returns
     *  `undefined` on any transport/auth error so callers can just skip. */
    async function post(path: string, body: Record<string, unknown>): Promise<any> {
      try {
        const res = await fetch(`${url}${path}`, {
          method: "POST",
          headers,
          body: JSON.stringify(body),
          signal: AbortSignal.timeout(timeoutMs),
        })
        if (!res.ok) return undefined
        const data = await res.json()
        // Tolerate a body that arrives as a JSON string (legacy double-encode).
        if (typeof data === "string") {
          try {
            return JSON.parse(data)
          } catch {
            return undefined
          }
        }
        return data
      } catch {
        return undefined
      }
    }

    /** Register the project on first sight so memory works in new checkouts
     *  without anyone asking. Best-effort. */
    async function ensureProject(): Promise<void> {
      const hostPath = loc?.project?.canonical || loc?.directory
      if (!hostPath) return
      await post("/api/register", { path: hostPath })
    }

    const recallCache = new Map<string, { at: number; block: string }>()
    const seenPrompts = new Set<string>()
    const filesBySession = new Map<string, Set<string>>()
    const lastSnapshot = new Map<string, number>()

    function formatRecall(ctx: Recall): string {
      const lines: string[] = []
      const tasks = (ctx.open_tasks ?? []).slice(0, 5)
      if (tasks.length) {
        lines.push("Open tasks:")
        for (const t of tasks) lines.push(`  - [${t.status}] ${t.title}`)
      }
      const recall = (ctx.recall ?? []).slice(0, 5)
      if (recall.length) {
        lines.push("", "Relevant memory from previous sessions:")
        for (const m of recall) lines.push(`  - ${m.title}: ${(m.content || "").slice(0, 300)}`)
      }
      const recent = (ctx.recent_memory ?? []).slice(0, 2)
      if (recent.length) {
        lines.push("", "Recent session state:")
        for (const m of recent) lines.push(`  - ${m.title}: ${(m.content || "").slice(0, 300)}`)
      }
      return lines.join("\n")
    }

    async function snapshot(sessionID: string, why: string): Promise<void> {
      if (!project) return
      const now = Date.now()
      if (now - (lastSnapshot.get(sessionID) ?? 0) < IDLE_SNAPSHOT_COOLDOWN_MS) return
      const files = [...(filesBySession.get(sessionID) ?? [])]
      if (!files.length) return

      const summary =
        `Auto-snapshot (${why}) for ${project}.\n` +
        `Files touched: ${files.slice(0, 25).join(", ")}` +
        (files.length > 25 ? ` (+${files.length - 25} more)` : "")

      const res = await post("/api/hooks/session/snapshot", { project, summary })
      if (res) {
        lastSnapshot.set(sessionID, now)
        filesBySession.set(sessionID, new Set())
      }
    }

    type Registration = { readonly dispose: () => Promise<void> }
    const registrations: Registration[] = []

    // ---------------------------------------------------------------- recall
    // The memory is already in the system prompt when the model runs: the
    // agent is never asked to fetch anything.
    registrations.push(
      await ctx.session.hook("context", async (event) => {
        if (!project) return
        if (event.system.some((p) => p.type === "text" && p.text.startsWith(SYSTEM_MARK))) return
        const sessionID = String(event.sessionID)
        const cached = recallCache.get(sessionID)
        const block = cached && Date.now() - cached.at < RECALL_CACHE_MS ? cached.block : undefined
        if (block === undefined) {
          let ctxRecall = await post("/api/hooks/session/start", { project })
          if (!ctxRecall) await ensureProject()
          if (!ctxRecall) ctxRecall = await post("/api/hooks/session/start", { project })
          const fresh = ctxRecall ? formatRecall(ctxRecall as Recall) : ""
          recallCache.set(sessionID, { at: Date.now(), block: fresh })
          if (fresh) event.system.push({ type: "text", text: `${SYSTEM_MARK} (project: ${project})\n${fresh}` })
          return
        }
        if (block) event.system.push({ type: "text", text: `${SYSTEM_MARK} (project: ${project})\n${block}` })
      }),
    )

    // --------------------------------------------------------------- prompts
    registrations.push(
      await ctx.session.hook("prompt", (event) => {
        if (!project) return
        const text = String(event.prompt?.text ?? "").trim()
        if (text.length < MIN_PROMPT_CHARS) return
        if (text.startsWith("<")) return
        // Hooks can run more than once per admission (retries/concurrency).
        const key = `${String(event.sessionID)}:${text.slice(0, 200)}`
        if (seenPrompts.has(key)) return
        seenPrompts.add(key)
        if (seenPrompts.size > 500) seenPrompts.clear()
        void post("/api/hooks/remember", {
          text,
          scope: "project",
          tags: ["opencode-prompt"],
          source: "opencode-plugin",
          project,
        })
      }),
    )

    // -------------------------------------------------------- edited files
    registrations.push(
      await ctx.tool.hook("execute.after", (event) => {
        if (event.status !== "completed") return
        if (event.tool !== "edit" && event.tool !== "write" && event.tool !== "patch") return
        const input = event.input as { filePath?: string } | null
        const file = input?.filePath
        if (!file) return
        const sessionID = String(event.sessionID)
        let set = filesBySession.get(sessionID)
        if (!set) filesBySession.set(sessionID, (set = new Set()))
        set.add(basename(file))
      }),
    )

    // ------------------------------------------------- before compaction
    registrations.push(
      await ctx.session.hook("compaction", (event) => {
        void snapshot(String(event.sessionID), "compaction")
      }),
    )

    // ------------------------------------------------------- lifecycle events
    const controller = new AbortController()
    void (async () => {
      try {
        for await (const ev of ctx.event.subscribe({ signal: controller.signal })) {
          const type = (ev as { type?: string }).type
          if (type !== "session.idle" && type !== "session.deleted") continue
          const sessionID = (ev as { properties?: { sessionID?: string } }).properties?.sessionID
          if (sessionID) void snapshot(sessionID, type)
        }
      } catch {
        // stream aborted / server down
      }
    })()

    return () => {
      controller.abort()
      recallCache.clear()
      seenPrompts.clear()
      filesBySession.clear()
      lastSnapshot.clear()
      void Promise.allSettled(registrations.map((r) => r.dispose()))
    }
  },
})
