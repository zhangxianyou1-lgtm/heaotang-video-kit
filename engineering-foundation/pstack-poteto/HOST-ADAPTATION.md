# pstack (Poteto) Host Adaptation for Codex, Antigravity & Claude Code

Upstream source: `https://github.com/cursor/plugins/tree/main/pstack` by Lauren Tan (`@poteto`, MIT License).

This bundle packages `@poteto`'s core verification, adversarial review, architecture, and structural mistake-prevention skills without Cursor-only automation hooks or name collisions with Matt Pocock's `tdd` / `teach` / `prototype` skills.

## Tool & Path Mapping

- **Subagent dispatch (`Task`)**: Spawn native host subagents (read-only/research subagents for exploration and review; isolated git worktrees for parallel candidate builds or adversarial `interrogate` repro runs).
- **Model selection**: Omit Cursor-specific model slugs (`claude-fable-*`, `claude-opus-5-5-*`, `gemini-4-neon-*`); run on the host session's active model or valid host subagent model tiers. Never pass unsupported model strings to tool calls.
- **Project verification skill location**: Write generated `verify-<app>` skills to `.agents/skills/verify-<app>/` (portable across Codex, Antigravity, and workspace agents) unless the repository already standardizes on `.claude/skills/` or `.cursor/skills/`.
- **Swarm skill name**: Exposed as `pstack-swarm` to avoid colliding with built-in host `swarm` tools.
