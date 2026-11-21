---
name: poteto-principles
description: "Lauren Tan (@poteto)'s 24 high-trust engineering principles from pstack (Prove It Works, Subtract Before You Add, Laziness Protocol, Attack the Premise, Build the Lever, Encode Lessons in Structure, Test Behavior Not Implementation, etc.). Consult when steering architecture, verification, debugging, or scope."
---
# Poteto's 24 Engineering Principles (`pstack`)

When a task hits one of the triggers below, open [`references/all-24-principles.md`](references/all-24-principles.md) for the exact rule and state which decision the principle changed:

## Core (Scope & Design)
- **`laziness-protocol`**: Bias toward deletion and the smallest change that solves the problem.
- **`subtract-before-you-add`**: Remove dead weight, redundant validators, and obsolete stubs first, then build on the simpler base.
- **`foundational-thinking`**: Settle core types, data structures, and shared state before writing logic.
- **`redesign-from-first-principles`**: Integrate a new requirement as if it had been foundational from day one instead of bolting on patches.
- **`attack-the-premise`**: Two fixes sharing one premise failed the same gate → write the premise down and test it directly before writing fix #3.
- **`minimize-reader-load`**: Collapse single-caller wrappers and shrink mutable state a reader must hold in their head.
- **`outcome-oriented-execution`**: During planned migrations, converge on target design instead of preserving throwaway compatibility shims.
- **`experience-first`**: Prefer user-facing result quality over implementation convenience.
- **`exhaust-the-design-space`**: For novel problems with no precedent, build 2–3 small competing prototypes and compare side by side.
- **`build-the-lever`**: When doing or proving non-trivial work repeatedly, build a deterministic script/tool a reviewer can rerun instead of working by hand.

## Architecture
- **`model-the-domain`**: Encode domain rules in one structure/table/state-machine instead of scattered conditionals.
- **`boundary-discipline`**: Validate at system boundaries (CLI, HTTP, config, external APIs); keep internal business logic pure.
- **`type-system-discipline`**: Make illegal states unrepresentable; parse external data at boundaries.
- **`make-operations-idempotent`**: Converge retries and partial runs on the same end state.
- **`migrate-callers-then-delete-legacy-apis`**: Migrate callers and delete old internal APIs in one wave.
- **`separate-before-serializing-shared-state`**: Eliminate shared mutable files/branches (e.g. via worktrees) before adding locks.

## Verification & Delegation
- **`prove-it-works`**: Verify against the real artifact (run the CLI, drive the UI, read back stored rows), never proxies or "it compiles".
- **`fix-root-causes`**: Trace symptoms to the first place the system went wrong; guards are fixes only when the guarded state is legitimate.
- **`sequence-verifiable-units`**: Break multi-step work into small units that each end in a runnable check before starting the next.
- **`test-behavior-not-implementation`**: Assert observable user behavior so tests fail on real regressions and survive internal refactors.
- **`explain-the-number`**: Name the limiter and rule out measurement artifacts before trusting any benchmark number.
- **`guard-the-context-window`**: Delegate bulk reading/sweeps to subagents; keep concise findings in the main thread.
- **`never-block-on-the-human`**: Proceed on reversible engineering choices and report; pause only on irreversible external actions or genuine product ambiguity.
- **`encode-lessons-in-structure`**: Turn any mistake corrected twice into an architectural constraint, type error, lint/check script, or test — docs last.
