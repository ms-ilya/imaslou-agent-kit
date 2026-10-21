# Post-Debate Options — Detailed Instructions

After delivering the verdict, offer these options to the user.

---

## Option 1: "Go deeper"

Spawn agents again with the Dissent Log's unresolved tensions as new sub-issues:

1. Extract 1-3 unresolved tensions from the Dissent Log
2. Frame each as a focused sub-issue
3. Dispatch all agents in parallel for one cross-examination round on the sub-issues (150-200 words each)
4. Collect responses, then the Judge produces an addendum to the original verdict

---

## Option 2: "Challenge the verdict"

User introduces a new constraint or objection:

1. Send the user's challenge to all agents in parallel as a mini-round
2. Each agent responds in 100-150 words: does this change their position? How?
3. Collect responses, then the Judge assesses how the constraint affects the verdict
4. Produce an updated verdict section (not a full re-judgment — just the delta)

---

## Option 3: "Add an agent"

Define a new agent persona to fill a gap:

1. Build the new agent's profile (Name, Role, Emoji, Lens, Core assumption, Blind spot). Check `<skill-dir>/references/archetypes.md` — if an archetype fits the new agent's intended role and does not duplicate an archetype already in the panel, assign it.
2. The new agent receives: the original issue + Round 3 rebuttals + the Judge's verdict
3. The new agent produces a "late entry" statement (200-250 words)
4. Dispatch existing agents in parallel for a mini cross-examination of the new agent (100-150 words each)
5. The Judge produces a brief addendum on whether the new perspective changes the verdict

---

## Option 4: "Export"

Read the export template from `<skill-dir>/references/export-template.md` and use the Write tool to generate the debate transcript as a structured markdown file. Save as `debate-[topic-slug].md` in the current working directory.
