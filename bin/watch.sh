#!/bin/sh
# watch.sh: a blocking reader for a Watchkeeper log, for machines without Python.
#
#   bin/watch.sh [-d DIR] [-t TIMEOUT] [-i INTERVAL] [-s SILENT_MINUTES] READER
#   bin/watch.sh [-d DIR] -a READER
#
# The first form waits until someone other than READER has posted after
# READER's acknowledged position, prints those posts, and exits 0. After
# TIMEOUT seconds with nothing new it lists lanes that have been quiet for
# SILENT_MINUTES and exits 2. Errors exit 1.
#
# The second form acknowledges everything last shown to READER. Nothing is
# acknowledged by being printed, so a reader that is interrupted sees the same
# posts again next time.
#
# It shares cursor files with the Python tool (.watchkeeper/cursors/READER,
# holding "<acknowledged line> <delivered line>"). Portable: POSIX sh, awk,
# and date only. No GNU or BSD extensions.

set -u

dir=${WATCHKEEPER_DIR:-.}
timeout=1500
interval=5
silent=120
ack=0

usage() {
    echo "usage: watch.sh [-d DIR] [-t TIMEOUT] [-i INTERVAL] [-s SILENT_MINUTES] READER" >&2
    echo "       watch.sh [-d DIR] -a READER" >&2
    exit 1
}

while getopts "d:t:i:s:a" opt; do
    case $opt in
        d) dir=$OPTARG ;;
        t) timeout=$OPTARG ;;
        i) interval=$OPTARG ;;
        s) silent=$OPTARG ;;
        a) ack=1 ;;
        *) usage ;;
    esac
done
shift $((OPTIND - 1))
[ $# -eq 1 ] || usage
reader=$(printf '%s' "$1" | tr 'abcdefghijklmnopqrstuvwxyz' 'ABCDEFGHIJKLMNOPQRSTUVWXYZ')
case $reader in
    ''|[!A-Z]*|*[!A-Z0-9-]*) echo "watch.sh: reader must be COORDINATOR, OWNER, or a lane name" >&2; exit 1 ;;
esac

log="$dir/LOG.md"
lanes="$dir/.watchkeeper/lanes"
cursor="$dir/.watchkeeper/cursors/$reader"
[ -f "$log" ] || { echo "watch.sh: no log at $log" >&2; exit 1; }

acked=0
delivered=0
if [ -f "$cursor" ]; then
    read -r acked delivered < "$cursor" || { echo "watch.sh: cursor $cursor is damaged" >&2; exit 1; }
fi

save_cursor() {
    mkdir -p "$dir/.watchkeeper/cursors"
    printf '%s %s\n' "$1" "$2" > "$cursor.tmp" && mv "$cursor.tmp" "$cursor"
}

if [ "$ack" -eq 1 ]; then
    save_cursor "$delivered" "$delivered"
    echo "acknowledged up to line $delivered"
    exit 0
fi

# Print posts after line $acked by anyone except $reader. The last output line
# is "#WK <end line> <posts shown>".
scan() {
    LC_ALL=C awk -v acked="$acked" -v delivered="$delivered" -v reader="$reader" '
        function author(h,   a) { a = substr(h, 4); sub(/[: ].*/, "", a); return a }
        function flush(torn) {
            if (!inpost) return
            if (author(head) != reader) {
                if (start <= delivered) print "[REDELIVERED: shown before, not yet acknowledged]"
                if (torn) print "[TORN: this post was cut short; ask its author to read back and re-post]"
                print buf
                print ""
                shown++
            }
            inpost = 0
        }
        $0 == "<!-- watchkeeper: posts below this line are append-only -->" { foot = NR; next }
        !foot || NR <= acked { next }
        /^## / {
            if (inpost) flush(1)
            inpost = 1; start = NR; head = $0; buf = $0; next
        }
        $0 == "<!-- /post -->" {
            if (inpost) { flush(0); end = NR }
            next
        }
        inpost { buf = buf "\n" $0 }
        END { if (end == "") end = acked; print "#WK " end " " shown + 0 }
    ' "$log"
}

# Seconds since 1970 for YYYY-MM-DDTHH:MM:SSZ, by arithmetic, so no date flags are needed.
silent_report() {
    now=$(date -u +%Y-%m-%dT%H:%M:%SZ)
    LC_ALL=C awk -v now="$now" -v limit="$silent" -v lanesfile="$lanes" '
        function epoch(t,   y, m, d, era, yoe, doy, doe) {
            y = substr(t, 1, 4) + 0; m = substr(t, 6, 2) + 0; d = substr(t, 9, 2) + 0
            if (m <= 2) y--
            era = int(y / 400); yoe = y - era * 400
            doy = int((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1
            doe = yoe * 365 + int(yoe / 4) - int(yoe / 100) + doy
            return (era * 146097 + doe - 719468) * 86400 + substr(t, 12, 2) * 3600 + substr(t, 15, 2) * 60 + substr(t, 18, 2)
        }
        BEGIN { while ((getline l < lanesfile) > 0) if (l != "") { n++; lane[n] = l } }
        /^## / {
            a = substr($0, 4); sub(/[: ].*/, "", a)
            if (match($0, /[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]T[0-9][0-9]:[0-9][0-9]:[0-9][0-9]Z$/))
                last[a] = substr($0, RSTART, RLENGTH)
        }
        END {
            for (i = 1; i <= n; i++) {
                l = lane[i]
                if (!(l in last)) print "SILENT " l " never posted"
                else if (epoch(now) - epoch(last[l]) >= limit * 60) print "SILENT " l " since " last[l]
            }
        }
    ' "$log"
}

waited=0
while :; do
    out=$(scan) || exit 1
    info=$(printf '%s\n' "$out" | tail -n 1)
    end=$(echo "$info" | awk '{ print $2 }')
    shown=$(echo "$info" | awk '{ print $3 }')
    if [ "$shown" -gt 0 ]; then
        printf '%s\n' "$out" | sed '$d'
        echo "$shown post(s). When you have dealt with them, run: watch.sh -a $reader"
        [ "$end" -gt "$delivered" ] && save_cursor "$acked" "$end"
        exit 0
    fi
    [ "$waited" -ge "$timeout" ] && break
    sleep "$interval"
    waited=$((waited + interval))
done

echo "no new post in ${timeout}s"
silent_report
exit 2
