#!/bin/bash
# Stage and commit only your own files, safely beside the other agents.
#   <team folder>/commit.sh <agent> "what changed"
# Finds your changed, new and deleted files inside your paths (owners.txt beside this script), stages
# exactly those and commits only those, even while another agent has work staged. If another agent is
# mid-commit (.git/index.lock), it waits and tries again.

agent="$1"; msg="$2"
here="$(cd "$(dirname "$0")" && pwd -P)"
root="$(git -C "$here" rev-parse --show-toplevel 2>/dev/null)"
owners="$here/owners.txt"
tries="${TEAM_LOCK_TRIES:-24}"; wait_s="${TEAM_LOCK_WAIT:-5}"
owner="$(git -C "$here" config --get team.owner 2>/dev/null)"; owner="${owner:-the owner}"

usage() {
  echo "usage: $(basename "$here")/commit.sh <agent> \"what changed\"   agents: $(awk '!/^#/ && NF { print $1 }' "$owners" 2>/dev/null | sort -u | tr '\n' ' ')" >&2
  exit 2
}
[ -n "$agent" ] && [ -n "$msg" ] || usage
{ [ -n "$root" ] && cd "$root"; } || { echo "Not inside the shared project folder. Tell $owner." >&2; exit 3; }
branch="$(git config --get team.branch)"
if [ -n "$branch" ] && [ "$(git branch --show-current)" != "$branch" ]; then
  echo "Not on branch $branch. Don't switch branches; tell $owner." >&2; exit 3
fi

owned=()
while IFS= read -r p; do owned+=("$p"); done < <(awk -v a="$agent" '!/^#/ && $1 == a { print $2 }' "$owners")
[ "${#owned[@]}" -gt 0 ] || usage
case "$msg" in "$agent:"*) ;; *) msg="$agent: $msg" ;; esac

# your changed, deleted and new files, inside your paths only
files=()
while IFS= read -r -d '' f; do files+=("$f"); done < <(
  { git rev-parse -q --verify HEAD >/dev/null && git diff --name-only -z --no-renames HEAD -- "${owned[@]}"
    git diff --cached --name-only -z --no-renames -- "${owned[@]}"
    git ls-files --others --exclude-standard -z -- "${owned[@]}"; } | sort -zu)
if [ "${#files[@]}" -eq 0 ]; then echo "Nothing to commit in your paths."; exit 0; fi

run() { # a git command that waits out another agent's index.lock
  local i out
  for ((i = 1; i <= tries; i++)); do
    if out=$("$@" 2>&1); then [ -n "$out" ] && echo "$out"; return 0; fi
    case "$out" in *index.lock*) sleep "$wait_s" ;; *) echo "$out" >&2; return 1 ;; esac
  done
  echo "Gave up: .git/index.lock is still there. If no git process is running (pgrep -x git), it's stale: delete it and run this again." >&2
  return 1
}

export TEAM_AGENT="$agent"
run git add -- "${files[@]}" || exit 1
# a file staged by a refused commit and deleted since is known to git no more: leave it out
known=()
for f in "${files[@]}"; do
  if git ls-files --error-unmatch -- "$f" >/dev/null 2>&1 || git cat-file -e "HEAD:$f" 2>/dev/null; then known+=("$f"); fi
done
if [ "${#known[@]}" -eq 0 ]; then echo "Nothing to commit in your paths."; exit 0; fi
run git commit -q --only -m "$msg" -- "${known[@]}" || exit 1
echo "$(git log -1 --format='%h %s' | head -1) (${#known[@]} files)"
