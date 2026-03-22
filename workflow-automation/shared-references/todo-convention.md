# TODO File Convention

Deferred and out-of-scope items are tracked in a TODO file in the
project's development docs directory. Check CLAUDE.md for the project's
convention on dev docs location and TODO file name (common patterns:
`dev/todos.md`, `docs/TODO.md`, `TODO.md`). If no convention exists,
default to `dev/todos.md`. Create the file if it doesn't exist.

**Format** — each entry is an H3 with metadata and context:

```markdown
# TODOs

### {short description}
- **Source**: {plan name or phase that deferred this}
- **Reason**: {why it was deferred — out of scope, dependency, time, etc.}
- **Context**: {enough detail to act on this later without re-reading the
  plan — what needs to happen, which files/APIs are involved, and any
  constraints or decisions already made}
```

**When to add entries:**
- Feature-plan skill (Step 2): out-of-scope items that still need doing
- Implement skill (Step 3): unlisted files deferred by user decision
- Implement skill (Step 5): review suggestions deferred to Notes
- Auto-implement (Completion): deferred suggestions from reviews
  across all phases

**Maintenance**: When a TODO is completed (by a later plan or ad-hoc
work), delete the entry rather than marking it done — the git history
preserves the record.
