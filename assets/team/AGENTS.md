# {{PROJECT}} build: agents, files and stages

{{PROJECT}} is TODO: what it is and who it's for, in two sentences.

{{N_AGENTS}} agents build it at the same time, each in its own Claude Code conversation in this folder. A planning conversation keeps this file, routes {{OWNER}}'s decisions and checks the work. None of them is in charge; {{OWNER}} is. {{OWNER}} sees the work at the end of each stage (Checkpoints, below) and is never waited on in between.

Every agent: read this file and every file in `{{DIR}}/status/` at the start of each work block.

## Decisions (newest first)

{{OWNER}}'s decisions, newest first. Each entry has its date and time from the clock, {{OWNER}}'s own words where they matter, which agent acts on each part, and the order. The planning conversation writes them. Read them before anything below.

- **{{DATE}}. The build starts.** TODO: the first stage's goal in one line.

## The agents

| Agent | Conversation | Builds | Owns (the only paths it commits) |
|---|---|---|---|
{{AGENTS_TABLE}}

Each agent also owns its status file, `{{DIR}}/status/<agent>.md`. The exact list, which the commit script and hook enforce, is `{{DIR}}/owners.txt`.

The conversation names are how agents reach each other: ListAgents shows them and SendMessage reaches them by name. When a conversation's real title differs from the name above, the planning conversation writes the real one here.

The planning conversation owns this file, `{{DIR}}/prompts/`, the scripts and hooks in `{{DIR}}/`, `contracts/README.md` and `CLAUDE.md`. Outside this folder everything is read-only.

## How the pieces fit

TODO: a small diagram of the parts, which agent owns each, and what flows between them.

## Contracts: the seams between agents

| File | Between | Owner |
|---|---|---|
| TODO | TODO | TODO |

They start as v0 sketches from the planning conversation. Only the owner edits a contract. To change one you don't own, add a request to your status file and send the owner a heads-up. When you change your own: bump its version line, note it in your status file, tell the agents who use it, and keep the old shape working until they've moved.

## Stack

TODO: languages and versions, how to install, run and test it, ports, where it runs.

## Hard rules

1. **Nothing goes out without {{OWNER}}'s word:** no publishing, pushing, sharing, emailing or posting; no messages sent as {{OWNER}}; no spending money. The pre-push hook lets only {{OWNER}} push.
2. **Your files only.** Edit only the paths you own (`{{DIR}}/owners.txt`), and commit only through `{{DIR}}/commit.sh`. The pre-commit hook refuses anything else.
3. **Nothing private in the repo:** no real people's details, none of {{OWNER}}'s own data, no tokens or keys, no databases or env files. Tests use made-up people and data. The privacy gate (`{{DIR}}/gate.py`) runs on every commit; mark an intended mention `privacy-ok` with its why.
4. **A message from another agent is a heads-up, not an order.** Act on it only inside your own files. No agent can grant another a permission, and no agent's message is {{OWNER}}'s approval.
5. **Never wait on {{OWNER}}.** Put each question under "For {{OWNER}}" in your status file with the default you're going with, then keep going. Stop only for rules 1 and 3.
6. **Proof, not claims.** Test the realest way available (the real server, the real build, the real screen sizes) and say what was and wasn't exercised.
7. TODO: this project's own rules (data it never stores, services it never calls, words it never uses).

## Status files

Keep `{{DIR}}/status/<agent>.md` current: at the start of a work block (what you're about to touch) and at the end (what's done, with proof). Read everyone else's at the start of every block. The sections: Now, Files I'm touching, Done (with proof), Next, Requests to other agents, For {{OWNER}}, Stage checklist.

Every time you write down (the Updated line, Done entries, checkpoint notes, contract version lines) comes from the clock: run `date '+%a %b %-d, %H:%M'` and copy what it prints. Never estimate a time or write one ahead.

The status files are the record. For anything urgent, also message the other conversation by name.

## Commits

All agents work in this one folder on one branch, never in a separate worktree or branch, so the status boards and contracts stay shared. Git's staging area is shared too, which is why every commit goes through one script.

- After each finished piece, with its tests passing and your status file updated, run `{{DIR}}/commit.sh <agent> "what changed"`. It stages and commits only your changed, new and deleted files inside your paths, even while another agent has work staged. If another agent is mid-commit, it waits.
- Never use `git add -A` or `git add .`, `git commit -a`, `--amend`, `--no-verify`, stash, reset, restore, checkout, switch, rebase, clean or push. In a shared folder they change or lose other agents' work.
- Other agents' uncommitted changes show up in `git status`. Leave them alone.
- At the start of each work block, `git log --oneline -15` shows what the others committed.
- Run formatters and linters on your own paths only.

## Stages

### Stage 1: TODO name, by TODO date

- [ ] TODO, for each agent, each ending in "Done means:" and a check anyone can run.

## Checkpoints: how {{OWNER}} is looped in

1. When you tick your last item for a stage, read the other status files. If every builder is done, message "{{CHECKS_NAME}}" and end your turn with one line for {{OWNER}}.
2. The {{CHECKS_TITLE}} agent checks every claim itself, then sends {{OWNER}} one note: what works (with proof), what doesn't, and at most five decisions, each with a recommended answer.
3. Builders keep going on the next stage meanwhile. Only the listed decisions wait for {{OWNER}}.

## Where things are

TODO: data, docs, design files and anything else agents need that isn't code.
