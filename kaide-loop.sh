#!/usr/bin/env bash
# kaide-loop.sh — unattended build⇄review loop for the Kaide phased-PRD pipeline.
#
# Wraps Step 11 (build) and Step 12 (review) around the git-commit state machine you
# already use. The harness is the "while" loop and the copy-paste relay you do by hand.
#
# STAGE 1 (start here):  run with --supervised  — it pauses for Enter after each
#                         gate-verified phase, so you build trust one phase at a time.
# STAGE 2 (later):        drop --supervised     — fully unattended; it stops only on a
#                         HALT signal, a failed gate, or BUILD_COMPLETE.
#
# Assumes a Linux environment (your Docker container): git, jq, coreutils (timeout),
# and the `claude` CLI authenticated to your Max subscription
# (CLAUDE_CODE_OAUTH_TOKEN from `claude setup-token`, or a mounted ~/.claude).
#
# All real state lives in git + the PHASE_*_SPEC.md files + BUILD_COMPLETE.md, so the
# loop is safe to Ctrl-C and restart at any point: it re-derives where it is every pass.
#
# ---------------------------------------------------------------------------
# NOTE: this is intentionally set -u (undefined-var guard) but NOT set -e. We handle
# every failure explicitly so a single bad step halts cleanly instead of crashing.
set -uo pipefail

# ---- defaults (override via flags / env) -----------------------------------
REPO=""                                        # --repo <path>          (required)
BUILD_PROMPT=""                                # --build-prompt <file>  (Step 11, HALT-patched)
REVIEW_PROMPT=""                               # --review-prompt <file> (Step 12, HALT-patched)
MODEL="${CT_MODEL:-sonnet}"                     # alias tracks latest Sonnet; don't pin a stale string
MAX_TURNS="${CT_MAX_TURNS:-300}"               # runaway guard, not a tight bound
BUILD_TIMEOUT="${CT_BUILD_TIMEOUT:-45m}"       # a build phase can be long
REVIEW_TIMEOUT="${CT_REVIEW_TIMEOUT:-30m}"
MAX_PHASES="${CT_MAX_PHASES:-8}"               # backstop if BUILD_COMPLETE is never written
SUPERVISED=0                                   # --supervised — pause for Enter each phase
DRY_RUN=0                                      # --dry-run — print git_state() and exit
NOTIFY_WEBHOOK="${CT_NOTIFY_WEBHOOK:-}"        # optional: POST a summary on terminal states
PERMISSION_MODE="${CT_PERMISSION_MODE:-bypassPermissions}"  # container-safe; the box is the blast radius

# ---- audit tier (Tier 3: Opus audits the Sonnet review) --------------------
AUDIT_TIER="${CT_AUDIT_TIER:-off}"             # on|off — opt-in third tier
AUDIT_MODEL="${CT_AUDIT_MODEL:-opus}"          # alias tracks latest Opus
AUDIT_MAX_ROUNDS="${CT_AUDIT_MAX_ROUNDS:-2}"   # review<->audit rounds before HALT
AUDIT_TIMEOUT="${CT_AUDIT_TIMEOUT:-20m}"       # audit is cheap; tight timeout is fine
AUDIT_PROMPT=""                                # --audit-prompt <file> (Step 12.5); required only if AUDIT_TIER=on

usage() { grep '^#' "$0" | sed 's/^# \{0,1\}//'; exit 1; }

while [ $# -gt 0 ]; do
  case "$1" in
    --repo)          REPO="$2"; shift 2 ;;
    --build-prompt)  BUILD_PROMPT="$2"; shift 2 ;;
    --review-prompt) REVIEW_PROMPT="$2"; shift 2 ;;
    --audit-prompt)  AUDIT_PROMPT="$2"; shift 2 ;;
    --model)         MODEL="$2"; shift 2 ;;
    --supervised)    SUPERVISED=1; shift ;;
    --dry-run)       DRY_RUN=1; shift ;;
    -h|--help)       usage ;;
    *) echo "unknown flag: $1"; usage ;;
  esac
done

[ -n "$REPO" ] && [ -d "$REPO/.git" ] || { echo "FATAL: --repo must point at a git repo"; exit 2; }
if [ "$DRY_RUN" -eq 0 ]; then
  [ -f "$BUILD_PROMPT" ]  || { echo "FATAL: --build-prompt file not found"; exit 2; }
  [ -f "$REVIEW_PROMPT" ] || { echo "FATAL: --review-prompt file not found"; exit 2; }
  if [ "$AUDIT_TIER" = on ]; then
    [ -f "$AUDIT_PROMPT" ] || { echo "FATAL: CT_AUDIT_TIER=on but --audit-prompt file not found"; exit 2; }
  fi
  command -v claude >/dev/null || { echo "FATAL: claude CLI not on PATH"; exit 2; }
fi
command -v jq >/dev/null     || { echo "FATAL: jq not on PATH"; exit 2; }

REPO="$(cd "$REPO" && pwd)"
LOG_DIR="$REPO/.loop-logs"
mkdir -p "$LOG_DIR"
RUN_ID="$(date +%Y%m%d-%H%M%S)"
AUDIT="$LOG_DIR/audit-$RUN_ID.log"

log() { printf '%s  %s\n' "$(date +%H:%M:%S)" "$*" | tee -a "$AUDIT"; }

notify() {  # $1=title  $2=body — writes a file always; POSTs if a webhook is set
  local title="$1" body="$2"
  printf '%s\n\n%s\n' "$title" "$body" > "$REPO/LOOP_LAST_EXIT.txt"
  if [ -n "$NOTIFY_WEBHOOK" ]; then
    curl -fsS -m 15 -X POST -H 'Content-Type: application/json' \
      --data "$(jq -n --arg t "$title" --arg b "$body" '{text: ($t + "\n" + $b)}')" \
      "$NOTIFY_WEBHOOK" >/dev/null 2>&1 || log "notify: webhook POST failed (non-fatal)"
  fi
}

has_marker() {  # $1=grep-safe commit-message fragment — 0 if present in git log
  git -C "$REPO" log --oneline --format='%s' | grep -qF "$1"
}

count_marker() {  # $1=commit-message fragment → prints how many times it appears in git log
  git -C "$REPO" log --oneline --format='%s' | grep -cF "$1" || true
}

# --- gates: ground-truth verification the harness runs itself (never trust the agent) ---
# Per-repo override: drop a loop.gates.sh in the repo root defining run_gates().
# Default gate set = exactly what ran clean and non-interactive in your CuratedTube runs.
run_gates() {
  ( cd "$REPO"
    echo "[gates] tsc"    && npx tsc --noEmit                       || exit 11
    echo "[gates] vitest" && npx vitest run --coverage              || exit 12
    echo "[gates] build"  && npx next build                         || exit 13
    echo "[gates] secret scan"
    if git -C "$REPO" ls-files | grep -qxE '\.env'; then exit 14; fi
    if grep -rIn --exclude-dir=node_modules --exclude-dir=.next \
         -E 'AIza[0-9A-Za-z_-]{20,}|NEXT_PUBLIC_[A-Z_]*KEY' "$REPO/src" 2>/dev/null; then exit 14; fi
  )
}
[ -f "$REPO/loop.gates.sh" ] && . "$REPO/loop.gates.sh"   # optional per-repo override

# --- state machine: derive the next action purely from git + the filesystem ---
git_state() {  # echoes: DONE | BUILD:N | REVIEW:N | AUDIT:N | STUCK
  [ -f "$REPO/BUILD_COMPLETE.md" ] && { echo "DONE"; return; }
  local specs highest n
  specs=$(ls -1 "$REPO"/PHASE_*_SPEC.md 2>/dev/null | sed -E 's/.*PHASE_([0-9]+)_SPEC\.md/\1/' | sort -n)
  [ -z "$specs" ] && { echo "STUCK"; return; }   # Step 10 must produce PHASE_1_SPEC first
  highest=$(echo "$specs" | tail -1)
  # Built-but-unapproved phase (highest first) — REVIEW (or AUDIT in three-tier mode).
  for n in $(echo "$specs" | sort -rn); do
    if has_marker "feat: Phase $n implementation" && ! has_marker "chore: Phase $n review approved"; then
      if [ "$AUDIT_TIER" = on ]; then
        # --- three-tier discovery ---
        local rc kc
        rc="$(count_marker "chore: Phase $n review complete")"
        kc="$(count_marker "chore: Phase $n audit kickback")"
        if [ "$rc" -eq 0 ]; then echo "REVIEW:$n"; return; fi    # first review, not yet complete
        if [ "$rc" -gt "$kc" ]; then echo "AUDIT:$n"; return; fi # newest review is un-audited
        echo "REVIEW:$n"; return                                 # last kickback awaits a re-review
      fi
      echo "REVIEW:$n"; return
    fi
  done
  # Specced-but-unbuilt phase (highest first) — BUILD.
  for n in $(echo "$specs" | sort -rn); do
    if [ -f "$REPO/PHASE_${n}_SPEC.md" ] && ! has_marker "feat: Phase $n implementation"; then
      echo "BUILD:$n"; return
    fi
  done
  # All specs built + approved, no new spec, no BUILD_COMPLETE = review didn't advance.
  echo "STUCK"
}

if [ "$DRY_RUN" -eq 1 ]; then
  git_state
  exit 0
fi

# --- run one agent turn headlessly; returns claude's exit code ---
run_agent() {  # $1=prompt_file  $2=timeout  $3=logtag  [$4=model, default $MODEL]
  local prompt_file="$1" tmo="$2" tag="$3" model="${4:-$MODEL}" out rc
  rm -f "$REPO/LOOP_STATUS.json"                 # clear any stale signal before the run
  out=$( cd "$REPO" && timeout "$tmo" claude -p "$(cat "$prompt_file")" \
           --model "$model" --max-turns "$MAX_TURNS" \
           --permission-mode "$PERMISSION_MODE" \
           --output-format json 2>>"$LOG_DIR/$tag-$RUN_ID.stderr" )
  rc=$?
  echo "$out" > "$LOG_DIR/$tag-$RUN_ID.json"
  local cost session
  cost=$(echo "$out"    | jq -r '.total_cost_usd // "?"' 2>/dev/null)
  session=$(echo "$out" | jq -r '.session_id // "?"'     2>/dev/null)
  log "agent[$tag] rc=$rc cost=\$$cost session=$session (timeout was $tmo)"
  return $rc
}

read_status() {  # echoes the status field of LOOP_STATUS.json, or MISSING
  [ -f "$REPO/LOOP_STATUS.json" ] || { echo "MISSING"; return; }
  jq -r '.status // "MISSING"' "$REPO/LOOP_STATUS.json" 2>/dev/null || echo "MISSING"
}
status_reason() { jq -r '.reason // "unspecified"' "$REPO/LOOP_STATUS.json" 2>/dev/null; }

halt() {  # $1=short-code  $2=detail  — notify + exit
  log "HALT [$1] $2"
  notify "kaide-loop HALT: $1" "$2"$'\n'"repo: $REPO"$'\n'"HEAD: $(git -C "$REPO" rev-parse --short HEAD)"
  exit 3
}

# --- one attempt at an action, with a single transient retry ---
do_action() {  # $1=BUILD|REVIEW  $2=N
  local kind="$1" n="$2" prompt tmo marker tag attempt=1
  if [ "$kind" = BUILD ]; then
    prompt="$BUILD_PROMPT"; tmo="$BUILD_TIMEOUT"; marker="feat: Phase $n implementation"; tag="build-p$n"
  else
    prompt="$REVIEW_PROMPT"; tmo="$REVIEW_TIMEOUT"; tag="review-p$n"
    if [ "$AUDIT_TIER" = on ]; then
      marker="chore: Phase $n review complete"
    else
      marker="chore: Phase $n review approved"
    fi
  fi

  while [ "$attempt" -le 2 ]; do
    log ">>> $kind Phase $n (attempt $attempt)"
    run_agent "$prompt" "$tmo" "$tag"; local rc=$?

    local st; st="$(read_status)"
    if [ "$st" = HALT ]; then halt "AGENT_HALT" "$kind Phase $n: $(status_reason)"; fi

    if [ "$rc" -ne 0 ] && [ "$st" != DONE ] && [ "$st" != BUILD_COMPLETE ] && [ "$st" != REVIEW_COMPLETE ]; then
      log "  non-zero exit ($rc) and no clean status — treating as transient"
      [ "$attempt" -eq 1 ] && { attempt=2; sleep 30; continue; }
      halt "INFRA_OR_RATELIMIT" "$kind Phase $n failed twice (rc=$rc). Check $LOG_DIR/$tag-$RUN_ID.stderr"
    fi

    # Ground truth: did the expected marker (or BUILD_COMPLETE, two-tier only) actually land?
    if has_marker "$marker" \
       || { [ "$kind" = REVIEW ] && [ "$AUDIT_TIER" != on ] && [ -f "$REPO/BUILD_COMPLETE.md" ]; }; then
      log "  verified: '$marker'${kind:+ }$( [ -f "$REPO/BUILD_COMPLETE.md" ] && echo '(+BUILD_COMPLETE)')"
      return 0
    fi

    log "  INDETERMINATE: agent returned but '$marker' is absent (status=$st)"
    [ "$attempt" -eq 1 ] && { attempt=2; sleep 5; continue; }
    halt "INDETERMINATE" "$kind Phase $n produced no '$marker' after 2 attempts. Inspect $LOG_DIR/$tag-$RUN_ID.json"
  done
}

# --- audit tier: Opus audits the review's OUTPUT, owns approval on APPROVE ---
do_audit() {  # $1=N
  local n="$1"
  local review_out="$REPO/.loop-logs/review-output-p$n.md"
  local round; round="$(count_marker "chore: Phase $n review complete")"
  log ">>> AUDIT Phase $n (round $round/$AUDIT_MAX_ROUNDS, model=$AUDIT_MODEL)"

  # the review output the audit consumes must exist, else we cannot audit
  if [ ! -f "$review_out" ]; then
    printf '{ "step":"audit","phase":%s,"status":"HALT","reason":"AUDIT_INPUT_MISSING","detail":"review output p%s absent","commit_sha":"%s" }\n' \
      "$n" "$n" "$(git -C "$REPO" rev-parse HEAD)" > "$REPO/LOOP_STATUS.json"
    halt "AUDIT_INPUT_MISSING" "Audit Phase $n: $review_out not found. Cannot audit the review."
  fi

  run_agent "$AUDIT_PROMPT" "$AUDIT_TIMEOUT" "audit-p$n" "$AUDIT_MODEL"; local rc=$?
  local st; st="$(read_status)"   # APPROVE | KICK_BACK | HALT

  # a genuine infra/ratelimit failure with no clean status = transient (one retry)
  if [ "$rc" -ne 0 ] && [ "$st" != APPROVE ] && [ "$st" != KICK_BACK ] && [ "$st" != HALT ]; then
    log "  audit non-zero exit ($rc), no clean status — retrying once"
    sleep 30
    run_agent "$AUDIT_PROMPT" "$AUDIT_TIMEOUT" "audit-p$n" "$AUDIT_MODEL"; rc=$?
    st="$(read_status)"
  fi

  case "$st" in
    HALT)
      halt "AUDIT_HALT" "Audit Phase $n: $(status_reason)" ;;

    APPROVE)
      # ground truth: the approval marker (or BUILD_COMPLETE on the final phase) must have landed
      if has_marker "chore: Phase $n review approved" || [ -f "$REPO/BUILD_COMPLETE.md" ]; then
        log "  audit APPROVE verified for Phase $n"
        rm -f "$REPO/.loop-logs/audit-kickback-p$n.md"
        # Opus may have direct-patched a boundary breach. Run OUR gates regardless — same
        # ground-truth check the two-tier flow runs after a review approval.
        log "  running independent gates on the audit-approved Phase $n tree..."
        if run_gates >>"$AUDIT" 2>&1; then
          log "  gates PASSED — audit approval stands."
        else
          local gc=$?
          printf '{ "step":"audit","phase":%s,"status":"HALT","reason":"GATE_FAILURE","detail":"harness gate exit %s","commit_sha":"%s" }\n' \
            "$n" "$gc" "$(git -C "$REPO" rev-parse HEAD)" > "$REPO/LOOP_STATUS.json"
          halt "GATE_FAILURE" "Audit approved Phase $n but harness gates failed (exit $gc). See $AUDIT. Approval is NOT trustworthy."
        fi
      else
        halt "INDETERMINATE" "Audit Phase $n claimed APPROVE but no 'review approved' marker landed. Inspect $LOG_DIR/audit-p$n-$RUN_ID.json"
      fi ;;

    KICK_BACK)
      # ceiling: round is the count of review-complete markers, i.e. audits so far including this one
      if [ "$round" -ge "$AUDIT_MAX_ROUNDS" ]; then
        halt "AUDIT_MAX_ROUNDS" "Audit Phase $n still not APPROVE after $round round(s). Gaps: $(status_reason). See $REPO/.loop-logs/audit-kickback-p$n.md"
      fi
      # the audit wrote .loop-logs/audit-kickback-p$n.md (gaps) + a 'chore: Phase N audit kickback'
      # commit. git_state now returns REVIEW:$n (rc == kc) so the next pass runs a FOCUSED re-review
      # that reads the gap list. Nothing else to do here.
      log "  audit KICK_BACK Phase $n (round $round) — routing focused re-review" ;;

    *)
      halt "AUDIT_INDETERMINATE" "Audit Phase $n returned unrecognized status '$st'. Inspect $REPO/LOOP_STATUS.json" ;;
  esac
}

# --- main loop -------------------------------------------------------------
log "kaide-loop start | repo=$REPO | model=$MODEL | supervised=$SUPERVISED"
[ "$SUPERVISED" -eq 1 ] || log "UNATTENDED MODE — will run to HALT / BUILD_COMPLETE without pausing"

# Single-flight lock so two loops can't race the same repo (degrades if flock absent).
LOCK="$LOG_DIR/.lock"
if command -v flock >/dev/null; then exec 9>"$LOCK"; flock -n 9 || { echo "another loop holds the lock"; exit 4; }; fi

iters=0; cap=$(( MAX_PHASES * 2 + 4 ))
while [ "$iters" -lt "$cap" ]; do
  iters=$(( iters + 1 ))
  state="$(git_state)"
  log "iteration $iters | state=$state"

  case "$state" in
    DONE)
      log "BUILD_COMPLETE.md present — sprint finished."
      notify "kaide-loop DONE ✅" "Build complete at $(git -C "$REPO" rev-parse --short HEAD). repo: $REPO"
      exit 0 ;;

    STUCK)
      halt "APPROVED_BUT_NO_ADVANCE" \
        "No buildable/reviewable phase and no BUILD_COMPLETE. A review likely approved a phase but crashed before writing the next spec. Inspect the repo." ;;

    BUILD:*)
      n="${state#BUILD:}"
      do_action BUILD "$n" ;;

    REVIEW:*)
      n="${state#REVIEW:}"
      if [ "$AUDIT_TIER" = on ]; then
        # three-tier: review only writes 'review complete'; no approval, no gates yet.
        do_action REVIEW "$n"
      else
        # ---- two-tier: unchanged ----
        do_action REVIEW "$n"
        # The reviewer just claimed approval. Trust nothing — run the gates ourselves.
        log "  running independent gates on the approved Phase $n tree..."
        if run_gates >>"$AUDIT" 2>&1; then
          log "  gates PASSED — approval stands."
        else
          gc=$?
          # Override the rubber stamp: the harness's own gate run is ground truth.
          printf '{ "step":"review","phase":%s,"status":"HALT","reason":"GATE_FAILURE","detail":"harness gate exit %s","commit_sha":"%s" }\n' \
            "$n" "$gc" "$(git -C "$REPO" rev-parse HEAD)" > "$REPO/LOOP_STATUS.json"
          halt "GATE_FAILURE" "Reviewer approved Phase $n but harness gates failed (exit $gc). See $AUDIT. Approval is NOT trustworthy."
        fi
      fi ;;

    AUDIT:*)
      n="${state#AUDIT:}"
      do_audit "$n" ;;
  esac

  # Supervised checkpoint: one phase done + gate-verified, wait for a human nod.
  if [ "$SUPERVISED" -eq 1 ]; then
    ns="$(git_state)"
    [ "$ns" = DONE ] && continue   # let the top of the loop emit the DONE notify
    printf '\n--- Phase step complete. Next state: %s. Press Enter to continue, Ctrl-C to stop. ---\n' "$ns"
    read -r _ </dev/tty || true
  fi
done

halt "MAX_PHASES_EXCEEDED" "Loop ran $iters iterations (cap $cap) without reaching BUILD_COMPLETE. Raise CT_MAX_PHASES or inspect for a stall."
