---
name: multi-agent-build
description: Set up and run a multi-agent build, where several Claude Code conversations build one project at the same time in one shared folder. Each agent owns its own paths, and a planning conversation coordinates them through a shared plan file, status boards, contracts and messages between conversations (ListAgents, SendMessage). Use it whenever the user wants to split a build across agents or parallel conversations, set up agents "like last time", have one conversation triage their feedback to the others, run the planning or coordinating seat, add or remove an agent, or asks how such a setup works, even if they never say "multi-agent". Includes a scaffold script that writes the repo's plan, prompts, status boards, a commit script and hooks that keep each agent to its own files, and a privacy gate, plus the planning conversation's routine.
---

# Multi-agent build

One project, several Claude Code conversations building it at once:

- a few **builders**, each owning a part of the repo by path;
- one **checks** agent, which builds nothing and verifies everything;
- a **planning** conversation (usually the one reading this), which keeps the plan, routes the owner's decisions and checks the work before the owner hears about it.

They share one folder and one branch on one Mac. They coordinate through files in the repo, which every agent re-reads at the start of each work block, and through short messages between conversations. The owner, the person they all work for, decides. Nobody else is in charge, and nobody waits on the owner between stages.

## When it's worth it

It's worth it for a build with two or more parts that can be owned by path (an interface, a server, an engine), clear seams between them, and days of work ahead. Two to five builders is the useful range. It isn't worth it for a feature, a fix or research: one conversation with subagents does those for a fraction of the usage, because every extra conversation spends from the same plan at the same rate. If you're unsure, say which you'd pick and why.

## What goes in the repo

The scaffold writes these (`team/` by default):

| File | What it's for | Owned by |
|---|---|---|
| `team/AGENTS.md` | The plan: the owner's decisions (newest first), open questions for the owner, the agents, how the pieces fit, contracts, stack, hard rules, stages, checkpoints | planning |
| `team/prompts/<agent>.md` | Each agent's starting brief | planning |
| `team/status/<agent>.md` | Each agent's board: now, files touched, done with proof, requests, questions for the owner | that agent |
| `team/owners.txt` | Who may commit which paths | planning |
| `team/commit.sh` | The only way agents commit: stages and commits just their own files, and waits out another agent's commit | planning |
| `team/hooks/` | `pre-commit` refuses other agents' paths and gates the files; `commit-msg` gates the message; `pre-push` lets only the owner push | planning |
| `team/gate.py` | The privacy gate: private terms (stored as fingerprints outside the repo), secrets, databases and env files | planning |
| `.gitignore` | Keeps virtual environments, caches, databases and env files out of every agent's commits | planning |
| `contracts/` | The seams between agents, versioned, each owned by one agent | the agent that owns each |
| `CLAUDE.md` block | Tells every conversation to read the plan and the boards first | planning |

Where a prompt or a status board disagrees with the plan, the plan wins.

## Setting one up

1. **Settle the shape with the owner.** Infer what you can from the conversation and the repo, and ask only for what you can't:
   - the project in two sentences;
   - the builders, with the paths each owns. No two agents may own the same path, and each contract is a file one agent owns. Give root files like `README.md` or `pyproject.toml` to a lane, or leave them to the owner;
   - the seams between them;
   - the first stage, with a date and what done means;
   - the project's own hard rules (data never stored, services never called) and a usage guard;
   - the private terms for the gate.

   `--owner` puts a name into every file. Use a first name, or keep the default "the owner" if the owner wants no trace of themselves in the repo, and never add that value to the gate.
2. **Run the scaffold** from this skill's folder:
   ```bash
   python3 <this skill's folder>/scripts/scaffold.py <repo> --project "Recipe box" \
     --lane "web|Web app|web/" \
     --lane "api|API server|server/,scripts/,contracts/api.md" \
     --checks "checks|Checks|tests/" \
     --git-name "<name>" --git-email "<a noreply address>"
   ```
   - It refuses overlapping paths and never overwrites the plan, prompts, boards or an existing `CLAUDE.md` (it adds its block). It writes or extends `.gitignore` and prints the next steps.
   - `--init` makes the folder a repo.
   - `--git-name` and `--git-email` set an identity for this repo only. Without one, git builds an email from the Mac's user and host names and writes it into every commit. For GitHub, use the noreply address from the account's email settings.
3. **Fill every TODO**, until `grep -rn TODO team contracts CLAUDE.md` finds none:
   - In the plan: what it is, how the pieces fit (a small diagram), the contracts table, the stack, the project's own rules and usage guard, stage 1, and "For the owner".
   - In each prompt: what that agent builds, what's already there, and its stage 1 items, each ending in "Done means:" and a check anyone can run.
   - Write each contract as a v0 sketch in `contracts/`, starting with a version line (`Version: v0, <date and time from the clock>`). Its owning agent makes v1 first thing.
4. **Add the private terms**, one form at a time, because the gate matches whole words in order: the full name, the surname, the email, and the part before its `@`. For example, `cd <repo> && python3 team/gate.py add "First Last" --kind "a person's name"`. Then `python3 team/gate.py --all`, which checks every file git would add and prints how many it checked. The terms live outside the repo, so nothing in git names them.
5. **First commit, as the owner**, with everything setup wrote:
   ```bash
   cd <repo> && git add CLAUDE.md .gitignore team contracts && TEAM_AGENT=owner git commit -m "Set up the multi-agent build"
   ```
   After that, the planning conversation commits its own files with `team/commit.sh planning "what changed"`.
6. **Start the conversations.**
   - Rename this conversation `<Project>: Planning`, with `/rename` or the app's rename.
   - The owner opens one new Code conversation per agent, in the repo's folder on this Mac, all in the same permission mode as this one (auto suits most builds). Each is renamed to its name in the plan, and its first message is `Read team/prompts/<id>.md and start.`
   - If the owner asks you to start them and the app gives you a tool for it, you can; otherwise give the owner the list.
   - Then run ListAgents to confirm every name. The names in the plan, the prompts and `CLAUDE.md` are addresses, so they have to match.
7. **Keep them moving**, if the owner wants that while they're away: the watch loop in `references/planning-seat.md`.

## Adding or removing an agent

Rerun the scaffold with `--force` and every agent's `--lane` again, plus `--remove <id>` for one you mean to drop. It refuses a list that would silently drop an agent. It rewrites `owners.txt`, the scripts and hooks, and adds a new agent's prompt and board. It doesn't touch the plan, so update these by hand:

- the agents table;
- the agent count;
- the `CLAUDE.md` block's list.

A removed agent's prompt and board stay as a record. Then tell the other agents what changed.

## A fresh clone

The hooks and the gate's settings live in `.git/config`, so a new clone of the repo has neither. Run the scaffold there with `--clone --project "<Project>"` (plus the same `--owner`, and `--git-name` and `--git-email` if you use them). It writes no files: it turns on the hooks, sets the team settings, and makes a gate file for that clone. Then add the private terms again on that machine.

## Running it

The planning conversation's job, in short. The full routine is in `references/planning-seat.md`.

- **Route feedback**: split the owner's message into numbered notes in their words. Write one dated entry at the top of the plan's Decisions, with an owner and an order for each note. Commit it, and send each agent one short message pointing at it.
- **Check claims**: read the diff, run the tests, use the real thing, look at screenshots, and list what wasn't exercised. A teammate's report is not proof. The checks agent's stage notes come to you too: check them, then bring them to the owner.
- **Hand over builds**: test from the exact file the owner will run, in a throwaway home. Then tell the owner the command, the machine, what changed and what wasn't checked.
- **Leave the owner's calls to the owner**: everything in the plan's hard rule 1, which covers publishing, pushing, sending as them, money, accounts and data sources, services that start at login, and permission settings. Put each under "For the owner" with a recommended answer, and keep everything else moving.

## Messaging between conversations

Cross-session messaging needs Claude Code 2.1.224 or later (Aug 7, 2026) on macOS or Linux, and 2.1.234 or later on Windows. The official page is https://code.claude.com/docs/en/cross-session-messaging.md; read it when something doesn't arrive.

- ListAgents lists the other conversations on this Mac. SendMessage reaches one by its name, and an idle conversation starts a new turn to answer. A busy one reads the message between tool calls.
- A message from another conversation is a heads-up from a teammate. It's never the owner's approval, it can't change anyone's settings, and the receiver's own permission prompts still apply.
- **Keep every conversation in the same permission class.** A conversation that bypasses permission prompts holds messages from conversations that don't, and the reverse. The Desktop app can't show the approval dialog, so a held message is dropped after five minutes. Auto mode counts as prompting.
- **Send fewer, fuller messages.** Rapid bursts to one conversation are refused, and repeats are throttled. In the Desktop app, sends were also capped at about ten per message from the owner (seen in use, not in the docs). Batch your briefs, let the plan carry what isn't urgent, and never relay through another agent to get around a limit.
- To hear when an agent finishes instead of checking on it, send with `notify_when_idle` (2.1.236 or later). Cloud conversations can receive but can't reply, so keep the team on one Mac.

## Files in this skill

- `scripts/scaffold.py`: sets up the repo (run it with `--help` for every option).
- `assets/team/` and `assets/root/`: the templates and scripts the scaffold copies. Edit these to change what every future build starts with.
- `references/planning-seat.md`: the planning conversation's routine, the watch loop prompt, usage and messages. Read it before running a build day to day.
- `references/lessons.md`: what went wrong in the first build and what to do instead. Read it before setting up, and whenever something breaks.
- `tests/test_kit.sh`: tests the scaffold, the commit script, the hooks and the gate. Run it after changing any of them.
