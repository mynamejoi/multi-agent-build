#!/usr/bin/env python3
"""Sets up a multi-agent build in a git repo: the plan every agent reads (<dir>/AGENTS.md), one prompt and one status
board per agent, owners.txt, the commit script, the hooks (lanes, the privacy gate on files and messages, pushes by the
owner only), a .gitignore, contracts/README.md and the CLAUDE.md block every conversation reads first.

    python3 scaffold.py REPO --project "Recipe box" \\
        --lane "web|Web app|web/,contracts/api-client.md" \\
        --lane "api|API server|server/,scripts/,contracts/api.md" \\
        [--checks "checks|Checks|tests/"] [--owner "Sam"] [--git-name NAME --git-email EMAIL] \\
        [--dir team] [--init] [--force [--remove ID]]

A lane is "id|Title|path,path". The id is what that agent passes to commit.sh, the title names its conversation
("<Project>: <Title>"), and the paths are the only ones it may commit; a path ending in / covers everything under it.
No two agents may claim the same path. The planning conversation ("<Project>: Planning") owns the plan, the prompts,
the scripts and hooks, .gitignore, contracts/README.md and CLAUDE.md.

--owner names the person whose word the agents wait for. It goes into every file, so leave it at "the owner" if that
person wants no trace of themselves in the repo, and never add it to the gate as a private term.

It never overwrites the plan, a prompt, a status board, contracts/README.md or an existing CLAUDE.md (it adds its
block to one), and it only adds lines to an existing .gitignore. --force refreshes the scripts, hooks and owners.txt
and adds what's missing, for a changed list of agents or a newer kit; pass every agent again, and --remove ID for one
you mean to drop. The gate's private terms live outside the repo, in ~/.config/agent-team/ (AGENT_TEAM_CONFIG
overrides).
"""
import argparse
import datetime
import hashlib
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys

KIT = pathlib.Path(__file__).resolve().parent.parent
TEAM_T, ROOT_T = KIT / "assets" / "team", KIT / "assets" / "root"
ID_RE = re.compile(r"^[a-z][a-z0-9-]{0,30}$")
MARK_START, MARK_END = "<!-- agent-team:start -->", "<!-- agent-team:end -->"
GITIGNORE = [".DS_Store", "__pycache__/", "*.pyc", ".venv/", "venv/", "node_modules/", ".env", ".env.*",
             "!.env.example", "*.db", "*.db-wal", "*.db-shm", "*.sqlite", "*.sqlite3", "*.log"]
TEMP = ("/tmp/", "/private/tmp/", "/var/folders/", "/private/var/folders/")


def die(msg: str) -> None:
    print(f"scaffold: {msg}", file=sys.stderr)
    sys.exit(2)


def git(repo: pathlib.Path, *args: str, check: bool = True) -> str:
    r = subprocess.run(["git", "-C", str(repo), *args], capture_output=True, text=True)
    if check and r.returncode:
        die(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout.strip() if r.returncode == 0 else ""


def lane(spec: str, flag: str) -> dict:
    parts = spec.split("|")
    if len(parts) != 3:
        die(f'{flag} "{spec}" needs three parts: "id|Title|path,path"')
    lid, title, paths = (p.strip() for p in parts)
    if not ID_RE.match(lid) or lid in ("owner", "planning"):
        die(f'{flag} id "{lid}": lowercase letters, digits and dashes, starting with a letter; not "owner" or "planning"')
    if not title:
        die(f'{flag} "{lid}" needs a title')
    ps = [p.strip() for p in paths.split(",") if p.strip()]
    for p in ps:
        if p.startswith(("/", "./")) or ".." in p.split("/") or p in (".", "*"):
            die(f'{flag} "{lid}": "{p}" must be a path inside the repo, like web/ or contracts/api.md')
    return {"id": lid, "title": title, "paths": ps}


def overlaps(p: str, q: str) -> bool:
    return p == q or (p.endswith("/") and q.startswith(p)) or (q.endswith("/") and p.startswith(q))


def render(text: str, values: dict) -> str:
    return re.sub(r"\{\{([A-Z_]+)\}\}", lambda m: values[m.group(1)], text)


def configure(repo: pathlib.Path, d: str, a: argparse.Namespace, notes: list) -> pathlib.Path:
    """The parts that live outside the repo's files: the gate's terms file, the hooks path, the team settings and
    the repo's git identity. Returns the gate file's path."""
    home = pathlib.Path(os.environ.get("AGENT_TEAM_CONFIG", pathlib.Path.home() / ".config" / "agent-team"))
    slug = re.sub(r"[^a-z0-9]+", "-", repo.name.lower()).strip("-") or "project"
    gate = home / f"{slug}-{hashlib.sha1(str(repo).encode()).hexdigest()[:6]}" / "gate.json"
    if not gate.exists():
        gate.parent.mkdir(parents=True, exist_ok=True)
        gate.write_text(json.dumps({"salt": secrets.token_hex(16), "terms": []}, indent=1) + "\n")
        gate.chmod(0o600)

    hooks_now = git(repo, "config", "--get", "core.hooksPath", check=False)
    if hooks_now and hooks_now != f"{d}/hooks" and not a.force:
        notes.append(f"core.hooksPath is already {hooks_now}, so the kit's hooks are NOT on. Merge them by hand, "
                     "or rerun with --force to point it at the kit's.")
    else:
        git(repo, "config", "core.hooksPath", f"{d}/hooks")
        old = [h.name for h in (repo / ".git" / "hooks").glob("*") if h.is_file() and not h.name.endswith(".sample")]
        if old:
            notes.append(f"The kit's hooks replace .git/hooks ({', '.join(sorted(old))} no longer run).")
    branch = git(repo, "branch", "--show-current", check=False) or git(repo, "symbolic-ref", "--short", "HEAD", check=False)
    for key, value in (("team.owner", a.owner), ("team.project", a.project), ("team.branch", branch or "main"),
                       ("team.gate", str(gate))):
        git(repo, "config", key, value)
    if a.git_name:
        git(repo, "config", "user.name", a.git_name)
    if a.git_email:
        git(repo, "config", "user.email", a.git_email)
    if not git(repo, "config", "user.email", check=False):
        notes.append("No git email is set for this repo or globally, so git will make one from this Mac's user and "
                     "host names and put it in every commit. Set one for this repo only with --git-name and "
                     "--git-email (for GitHub, the noreply address in your email settings).")
    if str(repo).startswith(TEMP):
        notes.append("This repo is in a temp folder, which the system cleans up. Move it somewhere lasting before real work.")
    return gate


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("repo")
    ap.add_argument("--project", required=True, help="the project's name, as conversation titles use it")
    ap.add_argument("--owner", default="the owner", help='the person whose word the agents wait for (default "the owner")')
    ap.add_argument("--lane", action="append", default=[], help='"id|Title|path,path", once per builder')
    ap.add_argument("--checks", default="checks|Checks|tests/", help='the checks agent, "id|Title|path,path"')
    ap.add_argument("--dir", default="team", help="the folder for the plan, prompts, boards and scripts")
    ap.add_argument("--git-name", help="a git author name for this repo only")
    ap.add_argument("--git-email", help="a git author email for this repo only, such as a GitHub noreply address")
    ap.add_argument("--init", action="store_true", help="git init the folder if it isn't a repo yet")
    ap.add_argument("--force", action="store_true", help="refresh the scripts, hooks and owners.txt; add what's missing")
    ap.add_argument("--remove", action="append", default=[], help="with --force: an agent id to drop on purpose")
    ap.add_argument("--clone", action="store_true", help="a fresh clone of a repo already set up: turn on its hooks "
                                                         "and settings, and write no files")
    a = ap.parse_args()
    if not a.lane and not a.clone:
        die("pass at least one --lane (or --clone for a fresh clone of a repo already set up)")

    repo = pathlib.Path(a.repo).expanduser().resolve()
    if not repo.is_dir():
        die(f"{repo} isn't a folder")
    if not git(repo, "rev-parse", "--show-toplevel", check=False):
        if not a.init:
            die(f"{repo} isn't a git repo (add --init to make one)")
        git(repo, "init", "-q")
    top = pathlib.Path(git(repo, "rev-parse", "--show-toplevel")).resolve()
    if top != repo:
        die(f"run it on the repo's top folder, {top}")
    d = a.dir.strip("/")
    if not re.match(r"^[A-Za-z0-9_.-]+$", d) or d.startswith("."):
        die(f'--dir "{a.dir}" must be one plain folder name, like team')
    if a.clone:
        if not (repo / d / "owners.txt").exists():
            die(f"--clone is for a repo already set up, and this one has no {d}/owners.txt")
        notes = []
        gate = configure(repo, d, a, notes)
        print(f"Turned on {a.project}'s hooks and settings in this clone, {repo}. No files were written.")
        print(f"  the gate's private terms for this clone: {gate} (add them again here)")
        for n in notes:
            print(f"  NOTE: {n}")
        return
    if (repo / d / "AGENTS.md").exists() and not a.force:
        die(f"{d}/AGENTS.md is already there. --force refreshes the scripts, hooks and owners.txt and adds what's "
            "missing; it never rewrites the plan, prompts, status boards or contracts.")

    builders = [lane(s, "--lane") for s in a.lane]
    checks = lane(a.checks, "--checks")
    lanes = builders + [checks]
    ids = [x["id"] for x in lanes]
    if len(set(ids)) != len(ids):
        die("two agents share an id")
    if set(a.remove) & set(ids):
        die(f"--remove {', '.join(sorted(set(a.remove) & set(ids)))} is also passed as an agent")
    owners_file = repo / d / "owners.txt"
    if owners_file.exists():
        before = {ln.split()[0] for ln in owners_file.read_text().splitlines() if ln.strip() and not ln.startswith("#")}
        missing = sorted(before - {"planning"} - set(ids) - set(a.remove))
        if missing:
            die(f"owners.txt has agents you didn't pass: {', '.join(missing)}. Pass every agent again, and "
                "--remove <id> for one you mean to drop.")
    planning = [f"{d}/AGENTS.md", f"{d}/prompts/", f"{d}/owners.txt", f"{d}/commit.sh", f"{d}/hooks/", f"{d}/gate.py",
                ".gitignore", "contracts/README.md", "CLAUDE.md"]
    checks["paths"].append(f"{d}/checkpoints/")
    for x in lanes:
        x["paths"].append(f"{d}/status/{x['id']}.md")
    claimed = [("planning", p) for p in planning] + [(x["id"], p) for x in lanes for p in x["paths"]]
    for i, (who, p) in enumerate(claimed):
        for other, q in claimed[i + 1:]:
            if who != other and overlaps(p, q):
                die(f'"{p}" ({who}) and "{q}" ({other}) overlap: every path has one owner')

    now = datetime.datetime.now()
    name = lambda x: f"{a.project}: {x['title']}"  # noqa: E731
    code = lambda ps: ", ".join(f"`{p}`" for p in ps)  # noqa: E731
    planning_name = f"{a.project}: Planning"
    owner_cap = a.owner[:1].upper() + a.owner[1:]
    builds = lambda x: ("End-to-end checks, privacy checks and the stage notes" if x is checks  # noqa: E731
                        else "TODO: what it builds")
    rows = [f"| Planning | {planning_name} | Keeps this plan, routes {a.owner}'s decisions, checks claims, hands "
            f"{a.owner} builds to try | {code(planning)} |"]
    rows += [f"| {x['title']} | {name(x)} | {builds(x)} | {code(x['paths'][:-1])} |" for x in lanes]
    base = {
        "PROJECT": a.project, "OWNER": a.owner, "OWNER_CAP": owner_cap, "DIR": d,
        "CLOCK": f"{now:%a %b} {now.day}, {now:%H:%M}",
        "N_AGENTS": str(len(lanes)), "AGENTS_TABLE": "\n".join(rows),
        "PLANNING_NAME": planning_name, "CONVERSATIONS": ", ".join(name(x) for x in lanes),
        "CHECKS_TITLE": checks["title"], "CHECKS_NAME": name(checks),
    }

    written, kept, notes = [], [], []

    def put(rel: str, text: str, machinery: bool = False, mode: int = 0o644) -> None:
        p = repo / rel
        if p.exists() and not (machinery and a.force):
            kept.append(rel)
            return
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        p.chmod(mode)
        written.append(rel)

    put(f"{d}/AGENTS.md", render((TEAM_T / "AGENTS.md").read_text(), base))
    for rel in ("commit.sh", "gate.py", "hooks/pre-commit", "hooks/commit-msg", "hooks/pre-push"):
        put(f"{d}/{rel}", (TEAM_T / rel).read_text(), machinery=True, mode=0o755)
    width = max(len(i) for i in ["planning", *ids]) + 2
    owners = ['# Who may commit which paths: one "agent path" per line. A path ending in / covers everything under it.',
              f"# {d}/commit.sh stages and commits only these, and {d}/hooks/pre-commit refuses anything else.",
              "# The owner commits anything with TEAM_AGENT=owner."]
    owners += [f"{'planning':<{width}}{p}" for p in planning]
    owners += [f"{x['id']:<{width}}{p}" for x in lanes for p in x["paths"]]
    put(f"{d}/owners.txt", "\n".join(owners) + "\n", machinery=True)
    for x in lanes:
        v = {**base, "LANE": x["id"], "LANE_TITLE": x["title"], "OWNED": code(x["paths"])}
        prompt = "prompt-checks.md" if x is checks else "prompt-builder.md"
        put(f"{d}/prompts/{x['id']}.md", render((TEAM_T / prompt).read_text(), v))
        put(f"{d}/status/{x['id']}.md", render((TEAM_T / "status.md").read_text(), v))
    put("contracts/README.md", render((ROOT_T / "contracts-README.md").read_text(), base))

    gi = repo / ".gitignore"
    have = gi.read_text().splitlines() if gi.exists() else []
    new = [x for x in GITIGNORE if x not in have]
    if new:
        lead = "\n".join(have).rstrip("\n") + "\n\n" if have else ""
        gi.write_text(lead + "# Machine-made and private files stay out of git (multi-agent-build).\n" + "\n".join(new) + "\n")
        written.append(".gitignore (lines added)" if have else ".gitignore")
    else:
        kept.append(".gitignore")

    block = f"{MARK_START}\n{render((ROOT_T / 'CLAUDE.md').read_text(), base).strip()}\n{MARK_END}\n"
    cm = repo / "CLAUDE.md"
    if not cm.exists():
        cm.write_text(block)
        written.append("CLAUDE.md")
    elif MARK_START not in cm.read_text():
        cm.write_text(cm.read_text().rstrip("\n") + "\n\n" + block)
        written.append("CLAUDE.md (its block added at the end)")
    else:
        kept.append("CLAUDE.md")

    gate = configure(repo, d, a, notes)

    print(f"Set up {len(lanes)} agents and a planning conversation for {a.project} in {repo}")
    for r in written:
        print(f"  wrote {r}")
    for r in kept:
        print(f"  kept  {r} (already there)")
    print(f"  hooks: {d}/hooks (each agent's own paths, the privacy gate on files and messages, pushes by the owner only)")
    print(f"  the gate's private terms: {gate} (outside the repo)")
    for n in notes:
        print(f"  NOTE: {n}")
    print("\nNext:")
    print(f"  1. Fill every TODO until `cd {repo} && grep -rn TODO {d} contracts CLAUDE.md` finds none, and write each "
          "contract as a v0 sketch.")
    print(f'  2. Private terms, one form at a time (full name, surname, email, the part before its @): cd {repo} && '
          f'python3 {d}/gate.py add "First Last" --kind "a person\'s name". Then python3 {d}/gate.py --all.')
    print(f'  3. First commit, as the owner: cd {repo} && git add CLAUDE.md .gitignore {d} contracts && '
          'TEAM_AGENT=owner git commit -m "Set up the multi-agent build"')
    print("  4. Rename the planning conversation, then start one new conversation per agent in this folder, all in "
          "the planning conversation's permission mode, each renamed and started like this:")
    print(f'       "{planning_name}"  (the conversation that ran this)')
    for x in lanes:
        print(f'       "{name(x)}"  first message: Read {d}/prompts/{x["id"]}.md and start.')


if __name__ == "__main__":
    main()
