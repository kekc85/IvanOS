# Resume protocol - state save + resume after crash

> v1.0 fix L4.3. Защита от потери прогресса при crash во время review-heavy iterations или при interrupted сессии. Применяется во всех phases pipeline.

## Когда применяется

- Любой `/longform` запуск без `--no-state` флага
- При commande `/longform --resume` или `/longform --resume <session-id>`
- При crash на любом phase (`03-write` или `04-review` Pass 2 чаще всего)

## State file location

```
/tmp/longform-state-<session-hash>.yaml
```

Где `<session-hash>` = первые 8 chars sha256(timestamp + raw_input + subject_name).

## State file schema

```yaml
session_id: <uuid>                              # генерится один раз в 01-router.md
timestamp_started: <iso8601>
timestamp_last_updated: <iso8601>

# from router
mode: A | B1 | B2 | C
platform: blog | newsletter | linkedin
subject_name: <from config>
language: ru | en | both
raw_input: <original user input>
flags_applied: [<list>]

# phase tracking
phase_completed: "router | mode | finalize | structure | write | review | publish"
phase_outputs:
  router_output: <yaml block>
  mode_output: <yaml block>           # mode_a_brief / mode_b1_brief / mode_b2_brief / mode_c_brief
  finalized_brief: <yaml block>
  structure_output: <yaml block>
  draft_v1: <yaml block>              # may be large; trimmed if > 10K chars
  review_output: <yaml block>

# review iteration counter (защита от infinite loop)
review_iterations: <int>
max_review_iterations: 3

# TTL
expires_at: <iso8601>                  # default = timestamp_started + 24h
```

## Phase write protocol

Каждый workflow file после успешного завершения своей работы:

```python
# pseudo-code
def update_state(state_file_path, phase_name, phase_output):
    state = read_yaml(state_file_path)
    state['phase_completed'] = phase_name
    state['phase_outputs'][f'{phase_name}_output'] = phase_output
    state['timestamp_last_updated'] = now_iso8601()
    write_yaml(state_file_path, state)
```

Phase mapping:

| Workflow file | phase_name | Key output |
|---|---|---|
| `01-router.md` | router | router_output |
| `01a-plan.md` / `01b-spark.md` / `01c-transcript.md` | mode | mode_<x>_brief |
| `01-finalize.md` | finalize | finalized_brief |
| `02-structure.md` | structure | structure_output |
| `03-write.md` | write | draft_v1 |
| `04-review.md` | review | review_output |
| `05-publish.md` | publish | final_publish_package |

## Resume flow

### `/longform --resume <session-id>`

1. Read `/tmp/longform-state-<session-id>.yaml`
2. Check `expires_at` - если истёк → fail с подсказкой «session expired, run fresh»
3. Skip всех phases ≤ `phase_completed`
4. Resume с следующего phase, используя `phase_outputs[<previous_phase>_output]` как input

### `/longform --resume` (без id)

1. Find latest state file в `/tmp/longform-state-*.yaml` (by timestamp_last_updated)
2. Если есть active session (< 24h) - предложить resume с показом mode/topic
3. Если нет - fail с подсказкой «no active session, run fresh /longform»

### `/longform` (новый запуск) при наличии state file

1. Найти state files с тем же `subject_name` + `raw_input` matching (≥80% similarity)
2. Если найден active session - warn пользователю «есть незавершённая session с этим input, --resume?»
3. НЕ block, пользователь решает start fresh или resume

## Cleanup

State file удаляется в одном из cases:

1. **Success:** `05-publish.md` завершён → delete state file
2. **TTL expire:** state file существует > 24h → delete (cron-like check в 01-router.md Step 1)
3. **Manual:** `/longform --clear-state` удаляет все state files (с подтверждением если их >1)

## Edge cases

### Crash во время review iteration

Если `04-review.md` Pass 2 fail на iteration 3+ → revision request → возврат в `03-write.md` → опять `04-review.md` Pass 2. После 3 iterations без PASS - escalate пользователю.

State file сохраняет `review_iterations` counter. При resume - продолжается с того же count, не сбрасывается.

### Crash во время write Pass 2 (voice injection)

Pass 1 skeleton draft уже записан в state file. Resume идёт с Pass 2, использует Pass 1 draft как starting point.

### Конфликт sessions (одновременно запущены 2 /longform)

Каждая имеет свой `session_id` (UUID). State files не конфликтуют. Но если user случайно запустит second `/longform` с тем же raw_input - warning в шаге «новый запуск при наличии state file».

### Disk full / state file write fail

`01-router.md` Step 8 пробует write. Если fail - warn пользователю «state save disabled, no resume protection» и продолжает без state.

## Memory cross-refs

- - resume = systemic fix для crash class issues
- - resume protocol = system rule, не ad-hoc workaround
- - после implementation resume - provoke crash в test чтобы validate