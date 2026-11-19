# Prompt Enhancer state machines

Living source of truth for the November 7, 2026 audit and repairs. Scope: the
shipped Alfred graph, `workflow/enhance.zsh`, all seven templates, and `build.sh`.
There is no database, server, or persistent conversation. Most original states
were implicit in shell control flow. The repairs add `latest` ownership and a
terminal `completed` marker. No account or native clipboard was used for tests.

Task: [Spindle #152](https://github.com/panoptican/spindle/issues/152).

## Confirmed defects, ordered by impact

These are observations from isolated process reproductions, not reports of
incidents on Jason's machine. Original-source references describe the pre-fix
code; named functions and regression names remain useful after line movement.
All listed defects are repaired locally.

| Priority / issue | Reachable invalid state or transition before repair | Evidence and regression | Repair |
| --- | --- | --- | --- |
| P1 [#154](https://github.com/panoptican/spindle/issues/154) | Older job A finishes after B, overwriting B's clipboard result and issuing success. Alfred's `concurrently=false` covers only the short foreground script; `nohup … &!` workers overlap. | Gate A, launch B, finish B, release A: clipboard was `older`. `test_latest_accepted_job_owns_clipboard`. | Shared kernel lock around acceptance and publication; latest accepted job alone can publish. Older results become `superseded`. |
| P1 #154 | Running or retrying job becomes deleted. Original `old_jobs=(job-*(N/om))` removed everything beyond 20 regardless of liveness. Subsequent file opens fail, often silently. | Seed 20 terminal directories and an older active directory, then launch: active disappeared. Strengthened regression now holds a real worker at a gate: `test_running_jobs_survive_retention`. | Prune only directories with terminal markers, under the shared lock, at registration and completion. |
| P2 [#155](https://github.com/panoptican/spindle/issues/155) | Claude stdout `API Error: 529 overloaded` with exit zero goes directly to failure rather than retry. | `test_zero_status_busy_retry` failed before repair; fake CLI returns zero twice with that body, then valid text. | Classify body before breaking out of the attempt loop. |
| P2 #155 | Whitespace-only output replaces the clipboard and announces success. | `test_blank_is_not_copied`: original copied spaces/newline/tab. | Require a non-whitespace character. |
| P2 #155 | Valid output discussing `API Error:` mid-sentence becomes failed. | `test_quoted_error_is_valid_output`: `Explain the string API Error: in this log.` was rejected. | Match the error prefix at a line boundary rather than any substring. |
| P2 #155 | Failed clipboard command exits via `set -e` with no terminal notification. All other normal worker failures originally exited zero. | `test_copy_failure_notifies`: fake `pbcopy` exits 1, no final notification arrived. | Explicit copy-failure branch; terminal marker and nonzero worker exit on failure; exit trap catches unexpected worker exits. |
| P2 [#156](https://github.com/panoptican/spindle/issues/156) | Known unauthenticated Claude request is accepted. With `pipefail`, an auth command that prints `loggedIn:false` and exits 1 makes the whole `if … \| grep` condition false. | `test_auth_failure_rejected`: original foreground returned zero and created a job. | Capture auth status/output separately; require successful command and affirmative login field. |
| P2 #156 | Selected text exactly `--run` enters internal dispatch and reads missing `$2`, rather than enhancing the text. | `test_internal_flag_as_selected_text`: original exited 1. | Internal dispatch requires exactly two arguments. Alfred supplies selected text as one argument. |
| P2 #156 | Relative cache path becomes relative to itself after worker `cd`; request/output opens fail. | `test_relative_cache`: foreground accepts `cache`, but no output reaches clipboard. | Normalize cache/job paths before changing directory. Validate executable overrides and normalize them too, preserving symlinks so sibling Node remains discoverable. |
| P2 [#157](https://github.com/panoptican/spindle/issues/157) | Build declares a mode valid when its Alfred action is missing; an orphan template also packages successfully. These are reachable **configuration mutation** defects, not broken states in the current seven-mode graph. | Remove Sonnet's mode-setting object, or add `templates/unknown.md`: original build exits zero. `test_build_rejects_missing_action`, `test_build_rejects_orphan_template`. | Check equality of script, action-variable and template mode sets in both directions. |

Baseline: 13 runtime test methods, nine failures. Both subsequent build mutation
tests failed against the original builder. Related normal paths (all modes,
nonzero busy retries, exhausted retries, failed partial output) already passed.
Tests were written and run before the corresponding repairs.

## State inventory and invariants

The following machines compose. A foreground exit zero means handoff was
requested, not that enhancement succeeded. Notifications are best effort and
are not durable state. `completed` contains `succeeded`, `failed`, or `superseded`;
its absence means unfinished or interrupted without a recorded terminal state.

1. **Alfred routing / mode registry.** Seven Universal Actions accept text,
   each routes through a variable-setting object into the shared script.
   That script executes `enhance.zsh "$1"`. A separate external `notify` trigger
   routes to the notification output. The script/action/template mode sets must
   agree. Provider/model selection is immutable within an accepted job.
2. **Foreground validation and acceptance.** Nonempty input, known mode,
   readable template, executable CLI, and successful authentication precede
   acceptance. Effort is always low, medium or high; invalid values use medium.
   Request text and rendered settings are snapshotted before `latest` changes.
3. **Template/configuration resolution.** A readable exact custom filename
   overrides the bundled file; missing custom files fall back. Empty personal
   settings remove placeholder lines. Settings cannot add modes. Selected text
   remains data inside the request wrapper; model compliance is not guaranteed
   by the wrapper itself.
4. **Worker and provider attempts.** Only a zero-status invocation with a
   nonblank, non-error body is eligible for publication. Claude has at most
   three attempts and only busy failures retry; Codex has one invocation.
   Failed/partial results never publish. A worker starts with empty output.
5. **Clipboard ownership.** `latest` changes only under the cache lock after
   the request is complete. A valid result can copy only while holding the
   same lock and matching `latest`. A newer *accepted* request supersedes
   older work even if it later fails. Validation failures do not supersede.
   This prevents an old success from masquerading as the newer request's result.
6. **Cache lifecycle.** Every job gets a unique private directory. No unfinished
   job is eligible for retention deletion. At most 20 terminal job directories
   remain after successful cleanup, plus unfinished jobs. Completion, pruning,
   and registration are serialized. The lock file is never unlinked.
7. **Feedback.** Success is announced only after copy succeeds; superseded
   results get a distinct message. Failure exits nonzero in the worker.
   Notification or sound delivery failure does not undo an already copied result.
8. **Packaging.** Validation precedes archive creation. Only workflow contents
   ship; specs and tests stay outside the archive. Packaging does not install
   or publish a release.

## Transition tables (current behavior)

### Alfred routing, registry and packaging

| From | Event / guard | To / action |
| --- | --- | --- |
| Idle | Text Universal Action | Set its `ENHANCER_MODE`, pass query to shared script |
| Shared script | Execution | One foreground invocation; detached workers may overlap |
| Notification trigger | `notify` argument | Alfred notification output |
| Build requested | Invalid plist, shell syntax, missing/unknown action or template mode | Build failed; no new archive built |
| Build requested | All validations pass | Archive workflow contents to versioned dist file |
| Archive written | Script exits zero | Built; installation/release are outside this machine |

The build checks mode *sets*, not full graph reachability, duplicate action
uniqueness, CLI model availability, or semantic template quality. Source inspection
confirmed the current plist's seven action → variable → script paths are connected.
A separately malformed future plist can still require graph validation.

### Input, configuration, authentication and handoff

| From | Event / guard | To / action |
| --- | --- | --- |
| Entry | Exactly two arguments, first `--run` | Internal worker path (expects PE environment and existing job) |
| Entry | Otherwise | Read selected text from `$1`, or stdin when argument empty and input not a TTY |
| Input read | Empty / unknown mode | Rejected, notify and exit 1; no accepted job |
| Input read | Known mode | Resolve provider/model and normalized effort |
| Resolve template | Readable exact custom file | Custom template chosen |
| Resolve template | Custom file absent/unreadable | Bundled template chosen |
| Template chosen | Chosen template unreadable | Rejected |
| Template chosen | CLI override or discovered executable exists | Normalize executable path, check authentication |
| Authenticate Claude | Status zero and affirmative `loggedIn:true` | Ready to prepare |
| Authenticate Codex | `login status` exits zero | Ready to prepare |
| Authenticate | Missing executable, negative/unknown auth or failed command | Rejected; no acceptance |
| Prepare | Cache and unique job creation succeed | Write selected text, rendered request and metadata |
| Prepared | Acquire lock, write `latest` | Accepted; prune terminal jobs, release lock |
| Accepted | Notify start, launch `nohup` worker | Foreground exits; worker owns execution |
| Preparation/locking | Filesystem/lock failure | Exit failure; no promise of a result; partial directory can remain |

### Provider execution and retries

| From | Event / guard | To / action |
| --- | --- | --- |
| Worker entry | Existing job and PE environment | Install exit/signal traps, change directory, clear old output |
| Claude attempt 1/2/3 | Invocation completes | Capture stdout, stderr and exit status for this attempt |
| Claude attempt | Exit zero and no line starting `API Error:` | Validate result (no retry for empty success) |
| Claude attempt 1/2 | Failed status or API error body; output/stderr matches busy markers | Notify busy; wait 10s / 20s, then next attempt |
| Claude attempt | Non-busy failure or third failed attempt | Failed; preserve final attempt output/error |
| Codex running | Invocation completes | Validate its last-message file and exit status; no workflow retry |
| Validate | Nonzero status, error body, empty/whitespace body | Failed; notify, terminal marker, exit 1 |
| Validate | Zero status and usable body | Await publication lock |
| Worker | Unexpected exit or catchable HUP/INT/TERM | Exit trap records failure and attempts failure notification/cleanup |

Busy markers retain the original heuristic: `API Error: 529`, `overloaded`, or
`too many requests`, case insensitive. Each Claude attempt truncates output and
stderr; an earlier attempt cannot become the next attempt's success. Only final
attempt diagnostics persist. Backoff may coexist with newer jobs and never
reserves the clipboard. Providers may also retry internally; these are opaque.

### Publication, terminal state and retention

| From | Event / guard | To / action |
| --- | --- | --- |
| Valid result | Lock acquired, `latest` is another job | Superseded; preserve result, notify, no copy |
| Valid result | Lock acquired, owns `latest`, copy succeeds | Succeeded; announce words/mode, best-effort sound |
| Valid result | Owns `latest`, copy fails | Failed; notify saved-result location, no success announcement |
| Any worker terminal state | EXIT trap acquires lock | Write terminal value to `completed`, prune terminal jobs, unlock |
| Terminal jobs >20 | Cleanup holds lock | Delete oldest terminal directories by directory mtime |
| Unfinished job | Any retention pass | Retain, including while provider is running or sleeping |
| Process holds cache lock | Process dies | Kernel releases lock; `.lock` file remains reusable |
| Older result | Newer request fails after acceptance | Still superseded; no automatic resurrection of old clipboard ownership |

Clipboard ownership is per cache directory. It does not protect against unrelated
apps changing the system clipboard after publication, or two installations using
different cache directories. No workflow worker is automatically rerun; `--run`
is a private handoff, not a supported resume/replay API.

### Notification fallback

| From | Event / guard | To / action |
| --- | --- | --- |
| Message requested | Alfred external trigger succeeds | Notification request delivered |
| Alfred trigger failed | macOS notification succeeds | Fallback requested |
| Both delivery methods fail | Shell suppresses failures | Continue; durable job outcome remains authoritative |
| Success sound requested | Playback fails | Continue; result already copied |

## Verification and limits

Run the durable regression artifact:

```sh
python3 -m unittest discover -s tests -v
./build.sh
```

`tests/test_state_machines.py` copies the shipped workflow into a temporary
fixture, preserves shell logic, and replaces only PATH and absolute macOS
notification/sound calls with stubs. Fake Claude/Codex processes consume the
request, emit controlled output/status and use file gates for reproducible
interleavings. Clipboard writes are isolated files. Tests cover all seven modes,
auth rejection, dispatch, relative cache/CLI paths, custom settings snapshots,
invalid input, empty/blank/partial/error outputs, retries and exhaustion, copy
failure, real active-job retention, newer failure supersession, reversed completion,
six simultaneous registrations, and both build mutations.

Final result: 21 test methods pass (including subcases for seven modes and both
providers); build succeeds with seven modes and seven actions. The local sandbox
prints a `nice(5) failed: operation not permitted` warning during zsh's background
syntax check; build exits zero and the process tests execute successfully.

Unverified boundaries and deliberate limits:

- Real provider authentication/output contracts, model access, native Alfred
  notifications, native clipboard behavior and sound were not exercised. Tests
  demonstrate the shell's response to those interfaces, not provider availability.
- Auth and error classification use text matching. A model response with a literal
  line beginning `API Error:` is ambiguous and conservatively fails. Semantic
  prompt quality and compliance with no-tools instructions are not state guarantees.
- No provider timeout exists. A hung provider stays unfinished. SIGKILL, system
  shutdown, a failed pre-handoff preparation, or failure to start a detached
  process may leave an unmarked directory. Retention deliberately preserves such
  directories rather than guessing that an old job is safe to delete. The limit
  is 20 terminal jobs, not a bound on all cache usage.
- Catchable signal traps and lock/filesystem failure recovery are source-reviewed,
  not fault-injected in this suite. A failed completion write or cleanup can leave
  incomplete bookkeeping. A publication interrupted during `pbcopy` cannot promise
  an unchanged system clipboard; success requires a successful exit from `pbcopy`.
- The fixes cover cooperating workers from this version using one cache. Already
  running workers from an older installed workflow do not follow the new lock or
  terminal-marker protocol. The built artifact has not been installed or published.
