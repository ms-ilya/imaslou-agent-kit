# Claude Code and Codex compatibility

All ten plugins share their workflow instructions between Claude Code and
Codex. Install whole plugins: skills use references, scripts and agent roles
elsewhere in their own package. See the [installation guide](../README.md#installation)
and [runtime conventions](runtime.md).

## Packaging and maintenance

The source files are:

- `.claude-plugin/marketplace.json`: plugin inventory and package locations.
- `plugins/*/.claude-plugin/plugin.json`: shared identity, description and version.
- `plugins/*/skills/*/SKILL.md`: shared workflow and Claude-specific frontmatter.
- `docs/runtime.md`: host mappings shipped inside every plugin.

Run `python3 scripts/sync_metadata.py` after changing those inputs. It generates
the Codex catalog at `.agents/plugins/marketplace.json`, each package's
`.codex-plugin/plugin.json`, each skill's `agents/openai.yaml` invocation policy,
and each package's `references/runtime.md`. Commit generated files with their
sources; an installed plugin cannot depend on this repository's root docs.
Use `--check` to detect drift without writing anything.

Claude's registered agent roles, effort settings and skill hooks remain in place.
Codex loads the same skill instructions, but its parent agent must supply a
bundled role's body and task inputs to its own subagent tools. Claude tool grants,
effort hints and turn budgets are not Codex configuration. Explicit-only
skills retain that policy through `agents/openai.yaml`.

## Model selection policy

The kit supplies no model field in skill or agent metadata and no model override
when dispatching, continuing or retrying workers. Both hosts resolve the user's
subagent settings and otherwise inherit the session's model. A user can still
explicitly request a supported model for a task. Built-in roles can have their
own host routing rules; the kit does not force every worker onto the parent model.

Omitting the model also preserves user defaults that an explicit inherit value
could bypass in Claude Code. Codex's configured subagent default can differ from
its main model. See [Claude model precedence](https://code.claude.com/docs/en/sub-agents#choose-a-model)
and [Codex subagent configuration](https://learn.chatgpt.com/docs/agent-configuration/subagents).

This policy preserves the existing four high-effort declarations, turn limits,
tool restrictions, validation gates and independent contexts. It makes no cost,
latency or output-quality promise across models. Model-specific routing needs
evidence from representative evaluations before becoming a kit default.

## Audit coverage

| Plugin | Skills | Portability work |
|---|---:|---|
| appstore-guideline-auditor | 1 | Resolve packaged catalog/schema paths; pass the schema to workers; adapt web retrieval, five-category dispatch, waits and retries; distinguish findings JSON from transcripts. |
| feature-spec | 2 | Resolve templates and scripts; run validators explicitly in Codex; adapt questions, instruction discovery and fact-finder retries; preserve independent critics; state the planning skill's actual context behavior. |
| grill-me | 1 | Resolve interview references; use the host's question limits and wait for asynchronous answers; retain explicit invocation. |
| humanizer | 1 | Resolve language and pattern references; supply the judge role in a fresh context; disclose self-scoring when independent review is unavailable. |
| ios-comprehensive-review | 6 | Replace automatic shell expansion with explicit context checks; parse arguments separately; dispatch within host capacity; adapt role loading and waits; preserve unverified findings. |
| ios-quick-review | 1 | Map file/search/question/delegation capabilities through the shared runtime while retaining scope confirmation and review phases. |
| memory-bank | 5 | Resolve shared verification guidance; replace OS-based tool assumptions with capability checks; preserve discovery and verification gates. |
| multi-agent-debate | 1 | Supply role text and round inputs to fresh workers; queue excess participants; retain round barriers; distinguish prompt restrictions from enforced tool access. |
| root-cause-analysis | 1 | Resolve investigation templates; adapt search and delegation; create report directories when the write tool requires it. |
| scratchpad | 1 | Resolve templates and hidden-file discovery; retain existing file and status transitions. |

All 11 READMEs provide both installation routes and the corresponding invocation
syntax. All 11 named agent roles state how their restrictions apply in each host.
The migration increments each plugin's minor version so hosts can recognize it
as an update.

## Reproducible checks

Run from the repository root with Python 3, Bash, Git and `jq` available. YAML
metadata checks reuse the existing parser: PyYAML when installed, otherwise Ruby
with its YAML library. These checks do not install dependencies or plugins.

```sh
python3 scripts/sync_metadata.py --check
python3 scripts/check_compatibility.py
python3 scripts/test_compatibility.py
python3 scripts/test_codex_smoke.py
python3 scripts/test_packaging.py
bash .dev/appstore-guideline-auditor/selftest.sh
git diff --check
```

- `check_compatibility.py` checks catalog parity, metadata, invocation policies,
  Claude script grants, packaged resources, relative plugin links, README
  commands, JSON validity and Bash/Python syntax. It rejects model fields and
  model assignments in bundled workflow instructions.
- `test_compatibility.py` exercises that policy with valid packages and
  intentionally reintroduced metadata and dispatch overrides, including an
  explicit inherit value. It also checks that effort and turn limits remain legal.
- `test_codex_smoke.py` runs ten offline regression tests for the live evidence
  verifier. Wrong models, failed or missing turns, replacement or extra workers,
  unsuccessful reads and invalid reports must fail. Previously observed,
  unchanged evidence can be reused on continuation; unseen lines cannot be
  cited. An assistant's model claim cannot substitute for host records.
- `test_packaging.py` copies packages into temporary paths containing spaces,
  removes Claude path variables, and runs helpers from a separate project
  directory. Its five integration tests include the feature-spec suite,
  auditor validation and project preservation, review extraction from existing
  Git history, and unverified/confirmed review findings. It creates no commits.
- The feature suite contains 237 assertions; the auditor self-test contains 51
  checks. Skipped checks are not evidence of compatibility.

For a plugin-capable Codex CLI, this read-only discovery check uses an ephemeral
configuration override rather than registering or installing the marketplace:

```sh
codex -c 'marketplaces.imaslou-agent-kit.source_type="local"' \
  -c "marketplaces.imaslou-agent-kit.source=\"${PWD}\"" \
  plugin list --marketplace imaslou-agent-kit --available --json
```

### Migration verification, 2026-10-21

On macOS, metadata/syntax checks, all five relocation tests, the 237 feature
assertions and the 51 auditor checks passed. Codex CLI
`0.163.0-alpha.11` discovered all ten plugins from the local catalog. Its
app-server `plugin/read` loader also returned all 20 expected skills with
nonempty descriptions. The discovery and loader checks did not install plugins
or modify the user's Codex configuration.

The model-policy follow-up passed all seven regression tests and the package
integration suite. A before/after metadata comparison confirmed that all 11
roles changed only by removing their model field and all 20 skills retained
their frontmatter. The native Codex loader accepted all 20 skills after the change.

The generic skill-creator `quick_validate.py` could not run because its PyYAML
dependency is absent. Its fixed frontmatter allowlist also omits Claude's
`hooks`, `context` and `disable-model-invocation` fields, so it is not the
compatibility authority for this shared format. The repository checker parses
those fields with the existing Ruby fallback, and the native Codex loader
accepted the shared skills.

Claude Code's CLI was not available for a live loading test. Its manifests,
frontmatter, agent files and hook contracts were checked statically, and the
feature suite exercises hook validation. The live Codex tests below exercise a
bounded fact-finder delegation and continuation, not a complete feature-spec
interview or every plugin's workflow. Loading, helper and routing tests do not
establish the quality of every interview, rewrite, audit or debate. The existing
feature-spec eval cases describe how to run representative scenarios in both hosts.

### Live Codex model-routing verification, 2026-10-21

Codex CLI `0.163.0-alpha.11` passed these cases with the actual bundled
fact-finder role and runtime instructions. The parent used `gpt-6-astra` from
the current user configuration. Each child read a temporary two-line fixture,
answered one question, then answered a second question through a continuation
of the same child. All six reports returned correct facts and line citations
in the role's required schema.

| Case | Configured subagent default | Explicit worker request | Host's resolved model | Model after continuation |
|---|---|---|---|---|
| Session inheritance | None | None | `gpt-6-astra` | `gpt-6-astra` |
| Configured default | `gpt-6-luna` | None | `gpt-6-luna` | `gpt-6-luna` |
| Explicit override | `gpt-6-luna` | `gpt-6.1-sol` | `gpt-6.1-sol` | `gpt-6.1-sol` |

The verifier reads Codex's `subAgentActivity.model` at creation, the completed
child-turn events, and `thread/read` model metadata after continuation. It does
not use model self-reports. Ephemeral threads do not support `includeTurns`, so
the event stream supplies their completed items. The test requests fresh contexts
and checks that no thread fork was recorded; it does not evaluate an independent
critic's quality or prove isolation against adversarial prompts.

Parent and children were ephemeral and read-only. The fixture remained unchanged.
The runs made no commits, installed no plugins and changed no permanent host
configuration. Model defaults were process-local command-line overrides. This is
evidence for the tested Codex version and models, not every host release or model.

To repeat the live suite, use an authenticated Codex CLI and choose three supported
models available in your account. This command sends `docs/runtime.md` and
`plugins/feature-spec/agents/fact-finder.md` to the configured Codex service and
consumes model usage. It is separate from the offline checks:

```sh
python3 scripts/smoke_codex_models.py \
  --default-model gpt-6-luna \
  --explicit-model gpt-6.1-sol
```

The parent uses your current configuration unless `--parent-model` is supplied.
The three models must differ so routing mistakes are observable. The inheritance
case requires no existing `agents.default_subagent_model`; the runner fails
clearly if one is present instead of editing it. Use `--case configured` or
`--case explicit` to run those cases separately. A temporary evidence directory
contains local event logs and `result.json` files with the instruction hashes,
resolved models and checked replies. These logs are not committed.

The corresponding live Claude checks remain open: load the plugin, verify
inheritance without a subagent override, then test `CLAUDE_CODE_SUBAGENT_MODEL`
and an explicit supported per-invocation override. Check host records and actual
role outputs; static frontmatter checks cannot replace these runs.

## Host limits

- Script-backed workflows need macOS, Linux or WSL with their documented tools.
  Native Windows shell execution was not tested. PR review also needs an
  authenticated GitHub CLI; live guideline verification needs web access.
- Independent critics and debate participants need isolated subagent contexts.
  A host without those capabilities uses the documented degraded behavior and
  reports the missing independence or coverage.
- Codex does not run this kit's skill-scoped Claude `PostToolUse` hooks. The
  feature skills explicitly require the same checks after writes and at gates.
- Claude forks the planning skill. Codex runs it in the current session and
  treats the recorded spec and design record as its only design inputs.
- Compatibility with a custom marketplace does not imply publication in
  OpenAI's public plugin directory. Desktop and CLI marketplace interfaces can
  differ by version.

## References

- [OpenAI plugin structure and metadata](https://developers.openai.com/plugins/build/plugins)
- [Bringing Claude plugins to Codex](https://developers.openai.com/plugins/guides/submit-claude-plugin)
- [Codex skill metadata](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code plugin reference](https://code.claude.com/docs/en/plugins-reference)
- [Claude Code subagent configuration](https://code.claude.com/docs/en/sub-agents)
