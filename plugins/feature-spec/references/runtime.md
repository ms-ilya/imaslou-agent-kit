# Runtime conventions for Claude Code and Codex

This file ships with each plugin. Follow the workflow in the skill using the
capabilities of the current host; tool names in examples are not portable APIs.

## Paths and inputs

- `<skill-dir>` means the absolute directory containing the loaded `SKILL.md`.
  `<plugin-root>` is two directories above it. Resolve them from the skill path
  supplied by the host, never from the working directory or a guessed cache path.
- Replace those placeholders with actual absolute paths before reading files or
  running commands. Quote script paths and each path argument separately. They
  are notation, not environment variables. Keep the shell's working directory in
  the user's project, since scripts resolve project files there.
- In references, `<skill-dir>` continues to mean the entrypoint's directory.
  A delegated agent receives resolved resource paths from its parent.
- `$ARGUMENTS` in Claude examples means the user's invocation text. In Codex,
  take that text from the message that invoked the skill; do not expect a shell
  variable or literal substitution. Parse flags as data, never execute raw input.
- `/plugin:skill` is Claude Code invocation syntax. In Codex use `$skill-name`
  or select the installed skill. References to `/skill` elsewhere are shorthand
  for that workflow, not commands to run in a terminal. To route to another
  bundled skill, read its `SKILL.md` if the host has no skill invocation tool.

## Tools and questions

| Capability | Claude Code | Codex |
|---|---|---|
| Read/search files | Read, Grep, Glob | Available file tools or shell: `rg`, `rg --files`, `sed` |
| Write/edit files | Write, Edit | Available file tools or `apply_patch`; create parent directories when needed |
| Run scripts | Bash | Available shell/exec tool |
| Search/fetch the web | WebSearch, WebFetch | Available web search/open tools; inspect actual retrieved text |
| Ask for a decision | AskUserQuestion | Available user-input tool; otherwise a question in chat |
| Delegate | Agent | Available subagent tools, such as `spawn_agent` |
| Continue/wait | Agent resume, SendMessage, completion notifications | Available follow-up/send-input and wait tools |

Inspect the actual tool schema. Do not send Claude-specific fields to Codex.
Question count, options, previews and multi-select support differ. Fit one round
into the available tool's limits, or ask it as one numbered message. With an
asynchronous question, wait for the user's reply before dependent work; an empty
result or elapsed time is not a decision. Host permission and sandbox rules
still apply; Claude `allowed-tools` does not grant Codex permissions.

## Subagents

Claude Code registers `agents/*.md` as named agents. Codex does not register
those Markdown files as agent types: for `plugin-name:role`, read
`<plugin-root>/agents/role.md` and include its body in a fresh subagent's prompt,
followed by the task inputs. Translate its tool restrictions into explicit task
boundaries (read-only, output-file-only, or no tools). Supply this file's path
and tool conventions when the agent needs file access. Do not treat a prompt
restriction as a sandbox guarantee.

### Model selection

The kit does not select models. Omit model overrides when starting, continuing
or retrying a worker in either host. Let the host apply the user's configured
subagent default, or inherit the active session's model when no override applies.
Only pass a model when the user explicitly requests one for that work and the
host supports it. Do not infer a cheaper or stronger model from the role, and
do not change host settings to force a match with the parent session.

Keep model fields absent from skill and agent metadata, including an explicit
inherit value: omission preserves the host's precedence and the user's subagent
settings. Built-in agent types also follow their host's own routing rules; this
policy does not promise every worker uses the exact same model as the parent.

Model selection is separate from reasoning effort, turn limits and context
isolation. Existing effort declarations continue to apply in their own host;
omitting a model does not remove them. `maxTurns`, `effort`, `subagent_type` and
`run_in_background` in Claude examples/frontmatter are not Codex parameters.
Preserve the role's bounded scope and required final output without inventing a
turn-limit API. General-purpose/Explore examples mean a normal worker with the
specified task or a read-only investigator.

### Independent work and completion

For independent critics, verifiers and debate participants, start with a fresh
context (disable history inheritance if supported), passing only the role and
its specified inputs. Never pass the author's reasoning to its independent
judge. For tool-free roles, the parent supplies the role text inline; the child
must not read the role file itself. If the host cannot isolate context, disclose
that independence was unavailable and use the skill's degraded mode.

Dispatch up to the available concurrency limit, queue the rest, and use the
host's completion/wait mechanism. Finish an entire stage or debate round before
consuming its results. Release completed workers when the host supports it.
Never assume a fixed host limit or that a tool call returning an ID means the
work finished. A retry must use a continuation tool that actually starts a turn,
or a fresh worker with the original inputs and the failure to correct.

If delegation is unavailable, use the skill's stated fallback. Otherwise perform
analysis roles sequentially and disclose the limitation. A self-check is never
an independent verification: keep findings unverified when independence was
required and report missing coverage explicitly.

## Host-specific metadata

Claude frontmatter retains its tool declarations, effort hints and hooks. Codex
invocation policy is in each skill's `agents/openai.yaml`; do not assume Claude's
`disable-model-invocation` or `context: fork` has the same effect there. Run the
skill in the current session unless it explicitly delegates a role.

Skill-scoped Claude `PostToolUse` hooks do not run through this kit's Codex
metadata. In Codex, execute the validation commands the feature-spec skills
require after writes and at phase gates. Do not claim automatic hook enforcement.
