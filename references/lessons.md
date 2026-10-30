# Lessons from the first build

The first build with this setup ran five agents and a planning conversation for about ten days. These are the failures it hit, or the ones its rules were written to prevent, each with what to do instead. Read this before setting up a new build, and again when something goes wrong.

## Seen in the first build

- **Mocks hid real bugs.** A front end passed every mocked test, then a recheck against the real server found seven bugs, all from data shapes the mock never sent. *Do:* before any release, run each piece against the real neighbours it talks to.
- **The gate flagged other agents' work.** Running the privacy gate over every file flagged teammates' uncommitted edits, which blocked an unrelated commit. *Do:* gate only what you're committing. Stage your own files, gate them, and commit with `--only` right away (`commit.sh` does all three).
- **The build was named after the wrong commit.** Between "which commit is this?" and "package it", another agent committed. *Do:* name the build by what the packager reports it exported.
- **A start-over script thought a dead server was running.** A server the test harness started but never reaped stayed as a zombie, and the stop step waited on it. *Do:* treat a zombie as stopped, and stop processes only by their own PID. (In earlier work, killing by name pattern took down unrelated servers.)
- **The owner ran the file on the wrong machine.** The download was on one Mac; they tried it on another. *Do:* every instruction names the machine and gives the exact command.
- **A live check failed on an expired login.** The check ran in a shell that used a different credential than the real install did. *Do:* run live checks with the same credentials path the owner's install uses, and never print the credential.
- **Messages sat in a hold.** Two agents ran in a different permission class from the planning conversation, so their incoming messages were held for approval. In the Desktop app, which can't show that dialog, a held message is dropped after five minutes. *Do:* set every conversation to the same permission class at the start, and don't resend into a hold.
- **Conversations had different titles than planned.** The app titled them itself, and only the real titles worked as addresses. *Do:* read the real titles with ListAgents and write them into the plan.
- **A question at 3 a.m. cost a day.** A yes-or-no the agent could have answered itself waited for the owner overnight. *Do:* make the reasonable call, write the default under "For [owner]", and keep going. Stop only for what's reserved.
- **A guide quoted a guessed number.** The setup guide gave a time the data didn't support. *Do:* every number given to the owner comes from a measurement, with its range.
- **Usage ran hot.** Five conversations at high effort, plus live model runs, pushed the weekly allowance past 80%. *Do:* keep a usage guard in the plan.

## Rules written to prevent a failure

- **One commit script, one hook.** All agents share one folder and one staging area, so `git add -A`, `commit -a`, stash or reset in one conversation can sweep up or erase another's work. The script stages and commits only the caller's paths, and the hook refuses anything else.
- **Times from the clock.** Agents otherwise write estimated or future times in their status boards, which makes the record useless for working out what happened when.
- **Proof with every Done.** A status entry without proof reads the same as one with it. The checks agent assumes broken until seen working, and the planning conversation checks again before the owner hears.
- **Messages and the author line count too.** The gate checks each commit's message as well as its files. Each repo sets its own git identity, because without one git builds an email from the Mac's user and host names and writes it into every commit.
- **The owner's data stays out.** Once the owner tests the product on their own life, their content can drift into fixtures, briefs and commit messages. Made-up people for every test, and the gate's fingerprints, keep the repo safe to share later.
- **One plan file, not chat.** Conversations get summarized as they grow, and a decision that lives only in chat gets lost. The plan is re-read at every work block.
- **Unreleased work lives in git.** Temp folders get cleaned up, and earlier work on the same Mac lost an unreleased bundle that way. Commit it, or park it as a patch outside temp folders.
