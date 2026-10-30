#!/bin/bash
# Tests the kit's scaffold, commit script, hooks and privacy gate on throwaway repos in a temp folder.
#   bash tests/test_kit.sh
set -u
KIT="$(cd "$(dirname "$0")/.." && pwd -P)"
T="$(cd "$(mktemp -d "${TMPDIR:-/tmp}/kit-test.XXXXXX")" && pwd -P)"
trap 'rm -rf "$T"' EXIT
mkdir -p "$T/repo"
export AGENT_TEAM_CONFIG="$T/config"
pass=0; fail=0
ok() { echo "PASS $1"; pass=$((pass + 1)); }
no() { echo "FAIL $1"; fail=$((fail + 1)); }
check() { if eval "$2"; then ok "$1"; else no "$1"; fi; }

cd "$T/repo" && git init -q -b main && git config user.name "Kit Test" && git config user.email "kit@test.invalid"
printf '# Existing\n\nKeep me.\n' > CLAUDE.md; echo "readme" > README.md
git add -A && git commit -qm "baseline"

out=$(python3 "$KIT/scripts/scaffold.py" "$T/repo" --project "Recipe box" --owner "Sam" \
  --lane "web|Web app|web/" --lane "api|API server|server/,scripts/,contracts/api.md" 2>&1); rc=$?
echo "$out" | sed 's/^/    /'
check "scaffold runs" "[ $rc -eq 0 ]"
check "no placeholders left" "! grep -rn '{{' team CLAUDE.md contracts"
check "existing CLAUDE.md kept, block added" "grep -q 'Keep me.' CLAUDE.md && grep -q 'agent-team:start' CLAUDE.md"
check "hooks path set" "[ \"\$(git config --get core.hooksPath)\" = team/hooks ]"
check "gate config outside the repo" "[ -f \"\$(git config --get team.gate)\" ] && case \"\$(git config --get team.gate)\" in $T/config/*) true;; *) false;; esac"
check "owners.txt lists every agent" "grep -q '^planning ' team/owners.txt && grep -q '^web ' team/owners.txt && grep -q '^api ' team/owners.txt && grep -q '^checks ' team/owners.txt"
check "prompts and boards for each" "[ -f team/prompts/web.md ] && [ -f team/prompts/api.md ] && [ -f team/prompts/checks.md ] && [ -f team/status/checks.md ]"

git add CLAUDE.md team contracts/README.md && TEAM_AGENT=owner git commit -qm "Set up the multi-agent build" 2>/dev/null
check "owner's first commit" "[ \"\$(git log -1 --format=%s)\" = 'Set up the multi-agent build' ]"

echo x > notes.txt && git add notes.txt
git commit -qm "plain" 2>"$T/e1"; rc=$?
check "plain commit refused" "[ $rc -ne 0 ] && grep -q 'Commit refused' $T/e1"
git rm -q --cached notes.txt

mkdir -p web server && echo "app" > web/app.js && echo "srv" > server/main.py
team/commit.sh web "add the app" >"$T/o2" 2>&1; rc=$?
check "web commits its own file only" "[ $rc -eq 0 ] && git show --name-only --format= HEAD | grep -qx web/app.js && ! git show --name-only --format= HEAD | grep -q server/"
check "message prefixed with the agent" "git log -1 --format=%s | grep -q '^web: add the app'"
check "server file left for its owner" "git status --porcelain | grep -q '?? server/'"

git add server/main.py
TEAM_AGENT=web git commit -qm "sneak" 2>"$T/e3"; rc=$?
check "hook refuses another agent's path" "[ $rc -ne 0 ] && grep -q \"server/main.py isn't web's\" $T/e3"
git rm -q --cached server/main.py

team/commit.sh api "add the server" >/dev/null 2>&1
check "api commits its file" "git log -1 --format=%s | grep -q '^api: add the server'"

python3 team/gate.py add "Jane Example" --kind "a person's name" >/dev/null
echo "const who = 'JANE EXAMPLE';" > web/names.js
team/commit.sh web "names" >"$T/o4" 2>&1; rc=$?
check "gate refuses a private name (any case)" "[ $rc -ne 0 ] && grep -q \"web/names.js:1: a person's name\" $T/o4"
check "gate output doesn't name the term" "! grep -qi 'jane' $T/o4"
echo "const who = 'Jane Example''s'; // privacy-ok: a made-up test name" > web/names.js
team/commit.sh web "names, marked" >/dev/null 2>&1; rc=$?
check "privacy-ok line passes" "[ $rc -eq 0 ]"

echo "const k = 'sk-ant-api03-abcdefghijklmnopqrstuvwxyz0123';" > web/key.js
team/commit.sh web "key" >"$T/o5" 2>&1; rc=$?
check "gate refuses an API key" "[ $rc -ne 0 ] && grep -q 'an Anthropic key' $T/o5"
rm web/key.js

touch web/local.db; echo "KEY=" > web/.env.example
team/commit.sh web "db" >"$T/o6" 2>&1; rc=$?
check "gate refuses a database file" "[ $rc -ne 0 ] && grep -q 'web/local.db: a file kind' $T/o6"
rm web/local.db
team/commit.sh web "env example" >/dev/null 2>&1; rc=$?
check "an .env.example passes" "[ $rc -eq 0 ] && git ls-files | grep -q web/.env.example"

rm web/app.js
team/commit.sh web "remove the app" >/dev/null 2>&1
check "a deleted file is committed" "! git ls-files | grep -q web/app.js"

python3 team/gate.py --all 2>"$T/e7"; rc=$?
check "gate --all is clean" "[ $rc -eq 0 ]"

git init -q --bare "$T/remote.git" && git remote add origin "$T/remote.git"
git push -q origin main 2>"$T/e8"; rc=$?
check "an agent's push is refused" "[ $rc -ne 0 ] && grep -q 'Push refused' $T/e8"
TEAM_AGENT=owner git push -q origin main 2>/dev/null; rc=$?
check "the owner's push goes" "[ $rc -eq 0 ]"

touch .git/index.lock; echo "more" > web/more.js
TEAM_LOCK_TRIES=2 TEAM_LOCK_WAIT=1 team/commit.sh web "while locked" 2>"$T/e9"; rc=$?
check "a stuck lock gives up with a hint" "[ $rc -ne 0 ] && grep -q 'Gave up' $T/e9"
rm -f .git/index.lock; git restore --staged web/more.js 2>/dev/null; rm web/more.js

git switch -q -c side; echo "s" > web/side.js
team/commit.sh web "side" 2>"$T/e10"; rc=$?
check "the wrong branch is refused" "[ $rc -eq 3 ] && grep -q 'Not on branch main' $T/e10"
rm web/side.js; git switch -q main

echo "KEEP-THIS-LINE" >> team/AGENTS.md
python3 "$KIT/scripts/scaffold.py" "$T/repo" --project "Recipe box" --owner "Sam" --lane "web|Web app|web/" \
  --lane "api|API server|server/,scripts/,contracts/api.md" >/dev/null 2>"$T/e11"; rc=$?
check "a second run without --force stops" "[ $rc -ne 0 ] && grep -q 'already there' $T/e11"
python3 "$KIT/scripts/scaffold.py" "$T/repo" --project "Recipe box" --owner "Sam" --lane "web|Web app|web/" \
  --lane "api|API server|server/,scripts/,contracts/api.md" --lane "engine|Engine|engine/" --force >"$T/o12" 2>&1; rc=$?
check "--force adds a lane and keeps the plan" "[ $rc -eq 0 ] && grep -q '^engine ' team/owners.txt && [ -f team/prompts/engine.md ] && grep -q KEEP-THIS-LINE team/AGENTS.md"
check "--force leaves CLAUDE.md's block alone" "[ \$(grep -c 'agent-team:start' CLAUDE.md) -eq 1 ]"

mkdir -p "$T/repo2" && git -C "$T/repo2" init -q
python3 "$KIT/scripts/scaffold.py" "$T/repo2" --project "X" --lane "web|Web|web/" --lane "ui|UI|web/components/" >/dev/null 2>"$T/e13"; rc=$?
check "overlapping paths are refused" "[ $rc -ne 0 ] && grep -q 'overlap' $T/e13"
python3 "$KIT/scripts/scaffold.py" "$T/repo2" --project "X" --lane "web|Web|team/" >/dev/null 2>"$T/e14"; rc=$?
check "a lane can't claim the team folder" "[ $rc -ne 0 ] && grep -q 'overlap' $T/e14"

echo; echo "$pass passed, $fail failed"
[ "$fail" -eq 0 ]
