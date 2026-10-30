---
name: multi-agent-build
description: Set up and run a multi-agent build, where several Claude Code conversations build one project at the same time in one shared folder. Each agent owns its own paths, and a planning conversation coordinates them through a shared plan file, status boards, contracts and messages between conversations (ListAgents, SendMessage). Use it whenever the user wants to split a build across agents or parallel conversations, set up agents "like last time", have one conversation triage their feedback to the others, run the planning or coordinating seat, add or remove an agent, or asks how such a setup works, even if they never say "multi-agent". Includes a scaffold script that writes the repo's plan, prompts, status boards, a commit script and hooks that keep each agent to its own files, and a privacy gate, plus the planning conversation's routine.
---

# Multi-agent build

One project, several Claude Code conversations building it at once:

- a few **builders**, each owning a part of the repo by path;
- one **checks** agent, which builds nothing and verifies everything;
- a **planning** conversation (usually the one reading this), which keeps the plan, routes the owner's decisions and checks the work before the owner hears about it.

They share one folder and one branch on one Mac. They coordinate through files in the repo, which every agent re-reads at the start of each work block, and through short messages between conversations. The owner, the person they all work for, decides; nobody else is in charge, and nobody waits on the owner between stages.

## When it's worth it

Worth it for a build with three or more parts that can be owned by path (an interface, a server, an engine), clear seams between them, and days of work ahead. Not worth it for a feature, a fix or research: one conversation with subagents does those for a fraction of the usage, because every extra conversation spends from the same plan at the same rate. If you're unsure, say which you'd pick and why.

## What goes in the repo

The scaffold writes these (`team/` by default):

| File | What it's for | Owner |
|---|---|---|
| `team/AGENTS.md` | The plan: the owner's decisions (newest first), the agents, how the pieces fit, contracts, stack, hard rules, stages, checkpoints | planning |
| `team/prompts/<agent>.md` | Each agent's starting brief | planning |
| `team/status/<agent>.md` | Each agent's board: now, files touched, done with proof, requests, questions for the owner | that agent |
| `team/owners.txt` | Who may commit which paths | planning |
| `team/commit.sh` | The only way agents commit: stages and commits just their own files, waits out another agent's commit | planning |
| `team/hooks/` | pre-commit refuses other agents' paths and runs the gate; pre-push lets only the owner push | planning |
| `team/gate.py` | The privacy gate: private terms (stored as fingerprints outside the repo), secrets, databases and env files | planning |
| `contracts/` | The seams between agents, versioned, each with one owner | each contract's owner |
| `CLAUDE.md` block | Tells every conversation to read the plan and the boards first | planning |

## Setting one up

1. **Settle the shape with the owner.** Infer what you can from the conversation and the repo, and ask only for what you can't: the project in two sentences, who the owner is, the builders (two to five) with the paths each owns, the seams between them, the first stage with a date and what done means, the hard rules (data never stored, services never called), and the private terms for the gate (people's names, the owner's email or address, a client's name). No two agents may own the same path; contracts are files, so each has one owner.
2. **Run the scaffold** from this skill's folder:
   ```bash
   python3 <this skill's folder>/scripts/scaffold.py <repo> --project "Recipe box" --owner "Sam" \
     --lane "web|Web app|web/" \
     --lane "api|API server|server/,scripts/,contracts/api.md" \
     --checks "checks|Checks|tests/"
   ```
   It refuses overlapping paths, never overwrites the plan, prompts, boards or an existing `CLAUDE.md` (it adds its block), and prints the next steps. `--init` makes the folder a repo; `--force` later refreshes the scripts, hooks and `owners.txt` for a changed lane list.
3. **Fill the TODOs.** In the plan: what it is, how the pieces fit (a small diagram), the contracts table, the stack, the project's own hard rules, stage 1. In each prompt: what that agent builds, what's already there, its stage 1 items, each ending in "Done means:" and a check anyone can run. Write each contract as a v0 sketch; its owner makes v1 first thing.
4. **Add the private terms**: `python3 team/gate.py add "Jane Doe" --kind "a person's name"` for each, then `python3 team/gate.py --all` to check the repo as it stands. The terms live outside the repo, so nothing in git names them.
5. **First commit, as the owner**: `git add CLAUDE.md team contracts/README.md && TEAM_AGENT=owner git commit -m "Set up the multi-agent build"`. After that, the planning conversation commits its own files with `team/commit.sh planning "what changed"`.
6. **Start the conversations.** The owner opens one new Code conversation per agent, in this folder on this Mac, all in the same permission mode, each titled `<Project>: <Title>`. Its first message is `Read team/prompts/<id>.md and start.` If the owner asks you to start them and the app gives you a tool for it, you can; otherwise give the owner the list. Then run ListAgents and write each conversation's real title into the plan's agents table, because the real title is its address.
7. **Keep them moving**, if the owner wants that while they're away: the watch loop in `references/planning-seat.md`.

## Running it

The planning conversation's job, in short (the full routine is in `references/planning-seat.md`):

- **Route feedback**: split the owner's message into numbered notes in their words, write one dated entry at the top of the plan's Decisions with an owner and an order for each note, commit it, and send each agent one short message pointing at it.
- **Check claims**: read the diff, run the tests, use the real thing, look at screenshots, and list what wasn't exercised. A teammate's report is not proof.
- **Hand over builds**: test from the exact file the owner will run, in a throwaway home, then tell the owner the command, the machine, what changed and what wasn't checked.
- **Leave the owner's calls to the owner**: publishing, pushing, sending as them, money, permission modes, accounts and data sources. Ask with a recommended answer, and keep everything else moving.

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
