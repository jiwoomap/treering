import { spawnSync } from "node:child_process"

const LOG = process.env.TREERING_LOG
const DENY = (process.env.TREERING_DENY ?? "").split(",").filter(Boolean)

function hook(event: Record<string, unknown>) {
  const args = ["hook", ...(LOG ? ["--log", LOG] : []), ...DENY.flatMap((d) => ["--deny", d])]
  const r = spawnSync("treering", args, { input: JSON.stringify(event), encoding: "utf8" })
  if (r.status !== 0 || !r.stdout.trim()) return null
  try {
    return JSON.parse(r.stdout)
  } catch {
    return null
  }
}

export const TreeRingPlugin = async () => ({
  "tool.execute.before": async (
    input: { tool: string; sessionID: string; callID: string },
    output: { args: unknown },
  ) => {
    const res = hook({
      agent: "opencode",
      hook_event_name: "PreToolUse",
      session_id: input.sessionID,
      tool_name: input.tool,
      tool_input: output.args,
      tool_use_id: input.callID,
      cwd: process.cwd(),
    })
    const d = res?.hookSpecificOutput
    if (d?.permissionDecision === "deny") throw new Error(d.permissionDecisionReason)
  },
  "tool.execute.after": async (
    input: { tool: string; sessionID: string; callID: string },
    output: { title: string; output: string },
  ) => {
    hook({
      agent: "opencode",
      hook_event_name: "PostToolUse",
      session_id: input.sessionID,
      tool_name: input.tool,
      tool_input: { title: output.title },
      tool_response: output.output,
      tool_use_id: input.callID,
      cwd: process.cwd(),
    })
  },
})
