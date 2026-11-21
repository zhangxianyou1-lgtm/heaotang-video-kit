# Host Adaptation (Codex / Antigravity / Claude Code)

Upstream source: `https://github.com/mattpocock/skills` (`v1.3.2`, MIT License).

- Resolve sibling skills from the active host skill catalog rather than assuming a Claude-only `Skill` tool name.
- Map subagent dispatches (e.g. parallel `Standards` + `Spec` reviewers in `code-review`, or frontier implementers in `implement-spec`) to the host's real subagent and git worktree primitives.
- Preserve decisions and authorizations already established in the session; do not force full interviews or remote issue-tracker mutations on small, explicit local tasks.
