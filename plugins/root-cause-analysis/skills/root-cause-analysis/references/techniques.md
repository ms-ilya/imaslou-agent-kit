# RCA Techniques

Read this file during Phase 1 (Gather Evidence) for Full scope investigations.

## Quick Investigation Checklist (Standard Scope)

Before moving to Phase 2, mentally verify you've considered factors beyond code:

- **Code:** Is the bug in the code itself, or in what calls it?
- **Data:** Could data format, schema, or content cause this?
- **Infrastructure:** Could config, environment, or resources cause this?
- **Process:** Is this code path tested? Is there CI/monitoring coverage?
- **People:** Is there a documentation gap that allowed this?

Skip categories that clearly don't apply. This is a mental check — no output needed.

---

## Fishbone Diagram Categories (Full Scope)

When investigating contributing factors, search across these categories systematically. Not all categories apply to every issue — skip irrelevant ones.

```
Main Problem: [The symptom being investigated]

Code:
  - Algorithm correctness
  - Missing validation / error handling
  - Race conditions / thread safety
  - Missing edge case coverage
  - Incorrect assumptions about input

Data:
  - Missing or stale data
  - Schema mismatch
  - Missing index / slow queries
  - Data corruption or inconsistency
  - Encoding / format issues

Infrastructure:
  - Resource exhaustion (CPU, memory, disk, connections)
  - Network latency / timeouts
  - Configuration drift between environments
  - Dependency failures (external services, databases)
  - Scaling limits

Process:
  - Missing or insufficient tests
  - No monitoring / alerting for this failure mode
  - Deployment without adequate review
  - Missing documentation
  - No environment parity (staging vs production)

People:
  - Knowledge gap (not individual blame — systemic gap)
  - Missing onboarding / documentation
  - Unclear ownership
```

### Grep Patterns per Category

**Priority:** Always grep the actual error message text first — it's the highest-signal search. Then use these category patterns.

Use these patterns when investigating each fishbone category:

| Category | Grep Patterns |
|----------|--------------|
| **Code** | Function/class name from symptom, error message text, `throw`, `raise`, `catch`, `except`, `panic`, `async`, `await`, `Promise`, `race`, `mutex`, `lock`, `concurrent`, `deadlock`, `goroutine`, `thread` |
| **Data** | `schema`, `migration`, `query`, `SELECT`, `INSERT`, `index`, `serialize`, `encode`, `decode` |
| **Infrastructure** | `config`, `env`, `timeout`, `connection`, `pool`, `limit`, `resource`, `memory`, `cpu`, `docker`, `container`, `k8s`, `kubernetes`, `port`, `host`, `ssl`, `tls`, `cert` |
| **Process** | `test`, `spec`, `ci`, `deploy`, `monitor`, `alert`, `coverage`, `.github/workflows` |
| **Logging** | `log`, `logger`, `console.`, `print`, `debug`, `trace`, `span`, `metric`, `error`, `warn` |
| **State** | `state`, `store`, `cache`, `session`, `global`, `singleton`, `shared`, `mutable` |

### How to use in Claude Code or Codex

For each relevant category, use the appropriate tools:
- **Code:** Grep for the function/module involved, trace call chain with Read
- **Data:** Check schema files, migration history, query patterns
- **Infrastructure:** Check config files, resource limits, connection pool settings
- **Process:** Glob for test files, check CI config, monitoring config
- **People:** Check CONTRIBUTING.md, README, code comments for knowledge gaps
- **Logging:** Grep for logging patterns to find existing instrumentation or gaps in observability
- **State:** Grep for state patterns to identify shared mutable state, cache issues, or session problems

---

## Systemic vs Individual Causes

When determining root cause, always prefer the systemic interpretation:

| Individual framing | Systemic framing | Why systemic is better |
|-------------------|------------------|----------------------|
| "Developer wrote a slow query" | "No query performance testing in CI" | Prevents recurrence by anyone |
| "Wrong config was deployed" | "No config validation in deploy pipeline" | Catches all config errors |
| "Edge case wasn't handled" | "No property-based or fuzz testing" | Catches classes of edge cases |
| "Dependency wasn't updated" | "No automated dependency monitoring" | Catches all stale deps |

The root cause should point to a **process, system, or structural gap** — something that can be fixed once to prevent a class of failures, not just this specific instance.
