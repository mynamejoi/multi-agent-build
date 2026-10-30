## How {{PROJECT}} is built

{{N_AGENTS}} agents build {{PROJECT}} at the same time, each in its own Claude Code conversation: {{CONVERSATIONS}}. "{{PLANNING_NAME}}" keeps the plan and routes {{OWNER}}'s decisions. None is in charge; {{OWNER}} is.

Before any work, read `{{DIR}}/AGENTS.md` (the decisions, who owns which files, the contracts, the stages, the hard rules) and every file in `{{DIR}}/status/`. Edit only the paths your agent owns (`{{DIR}}/owners.txt`), and commit only with `{{DIR}}/commit.sh <agent> "what changed"`. Nothing is published, pushed or sent without {{OWNER}}'s word.
