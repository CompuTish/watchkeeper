#!/bin/sh
# Replay a fictional two-lane run in a fresh directory, in about a second.
#
#   examples/toy-project/replay.sh [DIRECTORY]
#
# Two lanes share one staging environment. ALPHA is fixing a checkout total.
# BETA is adding a report to a batch job. Nothing here touches a real system:
# the "deploys" and "checks" are sentences in post bodies. What is real is the
# log, the status files, and every refusal you see.

set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
wk=${WK:-"$here/../../bin/wk"}
dir=${1:-$(mktemp -d "${TMPDIR:-/tmp}/watchkeeper-toy.XXXXXX")}
mkdir -p "$dir"
cd "$dir"

step() { printf '\n=== %s\n' "$*"; }
refused() {
    # Run a command that must be refused. Fail the replay if it is not.
    if "$@" 2>refusal.txt; then
        echo "replay error: this should have been refused: $*" >&2
        exit 1
    fi
    sed 's/^/(refused as expected) /' refusal.txt
    rm -f refusal.txt
}

step "1. The owner sets up a log with two lanes"
"$wk" init --lanes ALPHA,BETA

step "2. Both lanes ask for the environment"
"$wk" post --as ALPHA --to COORDINATOR REQUEST OP-0001 "checkout total fix" \
    --body "Head 1111111. Will deploy to staging and place one test order. About 25 minutes. Rollback: staging revision 41."
"$wk" post --as BETA --to COORDINATOR REQUEST OP-0002 "batch job report" \
    --body "Head 2222222. Will deploy to staging and run the nightly batch once. About 15 minutes."

step "3. The coordinator reads both requests"
"$wk" read --as COORDINATOR
"$wk" read --as COORDINATOR --ack

step "4. The coordinator admits ALPHA first and queues BETA"
"$wk" post --as COORDINATOR --to ALPHA ADMITTED OP-0001 "queued 1" \
    --body "Predecessor: staging serving revision 41, zero test orders. Steps as requested. Wait for ENTRY OPEN."
"$wk" post --as COORDINATOR --to BETA WAIT OP-0002 "queued 2 behind ALPHA"

step "5. A housekeeping note to all lanes would replace ALPHA's binding post, so it is refused"
refused "$wk" post --as COORDINATOR --to "ALL LANES" NOTE "disk check at the top of the hour"

step "6. BETA cannot take the environment without its own ENTRY OPEN"
refused "$wk" status set BETA OP-0002

step "7. The coordinator opens entry for ALPHA, in the exact form lanes match"
"$wk" post --as COORDINATOR --to ALPHA "ENTRY OPEN" OP-0001 18:05Z-18:35Z \
    --body "Find staging on revision 41 with zero test orders before you deploy. If not, HOLD."

step "8. ALPHA checks its predecessor, takes the lock, and says so"
"$wk" status set ALPHA OP-0001
"$wk" post --as ALPHA --to COORDINATOR ENTERED OP-0001 --body "Predecessor confirmed: revision 41, zero test orders."
"$wk" status

step "9. ALPHA's confirmation check fails, so it holds and names the failing check"
"$wk" post --as ALPHA --to COORDINATOR HOLD OP-0001 "confirmation check matched two elements" \
    --body "Deploy worked (revision 42). The test looks for the confirmation text and finds it twice: once in the panel, once in the header. One test order exists. Proposal: narrow the check to the panel and re-run once. I will not retry without a disposition."

step "10. The coordinator classifies before ruling: a test-tooling fault, not a product fault"
"$wk" read --as COORDINATOR
"$wk" post --as COORDINATOR --to ALPHA GO OP-0001 "tooling only, narrow the check and re-run once" \
    --body "Screenshot shows the panel rendered once. The duplicate text is in the header. Same window, same rollback."
"$wk" read --as COORDINATOR --ack

step "11. ALPHA passes, cleans up, releases the lock, and reports"
"$wk" status set ALPHA NONE
"$wk" post --as ALPHA --to COORDINATOR RELEASED OP-0001 \
    --body "Re-run passed. Test order cancelled and deleted. Staging on revision 42. Nothing left behind."

step "12. The coordinator does its own read-only readback, then closes the case"
"$wk" read --as COORDINATOR
"$wk" post --as COORDINATOR --to ALPHA ACCEPTED+RELEASED OP-0001 \
    --body "Own checks: staging on revision 42, zero test orders, run passed on head 1111111. Card moved to done after the production check."
"$wk" read --as COORDINATOR --ack

step "13. BETA's turn: a fresh admission and an explicit entry"
"$wk" post --as COORDINATOR --to BETA ADMITTED OP-0002 "queued 1" \
    --body "Predecessor: staging on revision 42, the one ALPHA left. Your deploy will replace it."
"$wk" post --as COORDINATOR --to BETA "ENTRY OPEN" OP-0002 18:40Z-19:00Z
"$wk" status set BETA OP-0002
"$wk" post --as BETA --to COORDINATOR ENTERED OP-0002
"$wk" status set BETA NONE
"$wk" post --as BETA --to COORDINATOR RELEASED OP-0002 --body "Batch ran once. Report produced. Nothing left behind."
"$wk" post --as COORDINATOR --to BETA ACCEPTED+RELEASED OP-0002 --body "Own checks: report present, staging on revision 43."

step "14. Final state"
"$wk" status
"$wk" lint
echo
echo "The full log is in $dir/LOG.md"
