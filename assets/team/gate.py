#!/usr/bin/env python3
"""The privacy gate. Refuses a commit whose files carry a private term, a secret, or a file kind that stays out of git.

Private terms (people's names, the owner's email or street, a client's name) live only as salted one-way fingerprints
in a file outside the repo (git config team.gate; the scaffold makes it), so the repo never names them and a finding
shows only its file, line and kind. A line marked privacy-ok, with its why, is left out.

    python3 team/gate.py                                      # the staged files (the pre-commit hook runs this)
    python3 team/gate.py --all                                # every tracked file
    python3 team/gate.py add "Jane Doe" --kind "a person's name"
"""
import argparse
import fnmatch
import hashlib
import json
import os
import pathlib
import re
import secrets
import subprocess
import sys

OK_MARK = "privacy-ok"
TOKEN = re.compile(r"\w[\w@+.'’-]*")
SECRETS = [
    ("an Anthropic key", re.compile(r"sk-ant-[A-Za-z0-9_-]{20,}")),
    ("an API key", re.compile(r"\bsk-(?!ant-)(?:proj-)?[A-Za-z0-9_-]{32,}")),
    ("a GitHub token", re.compile(r"\bgh[pousr]_[A-Za-z0-9]{36}\b|\bgithub_pat_[A-Za-z0-9_]{50,}")),
    ("an AWS key id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("a Google API key", re.compile(r"\bAIza[0-9A-Za-z_-]{35}\b")),
    ("a Slack token", re.compile(r"\bxox[abprs]-[A-Za-z0-9-]{10,}")),
    ("a private key", re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
]
REFUSE_FILES = ["*.db", "*.sqlite", "*.sqlite3", "*.db-wal", "*.db-shm", ".env", ".env.*", "*.pem", "*.p12", "*.key",
                "id_rsa*", "id_ed25519*"]
ALLOW_FILES = ["*.example", "*.sample", "*.template"]


def git(*args: str) -> bytes:
    return subprocess.run(["git", "--no-optional-locks", *args], capture_output=True, check=True).stdout


def top() -> pathlib.Path:
    return pathlib.Path(git("rev-parse", "--show-toplevel").decode().strip())


def config_path() -> pathlib.Path:
    try:
        set_to = git("config", "--get", "team.gate").decode().strip()
    except subprocess.CalledProcessError:  # not set
        set_to = ""
    if set_to:
        return pathlib.Path(os.path.expanduser(set_to))
    name = re.sub(r"[^a-z0-9]+", "-", top().name.lower()).strip("-") or "project"
    return pathlib.Path.home() / ".config" / "agent-team" / name / "gate.json"


def load(path: pathlib.Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {"salt": "", "terms": []}


def tokens(text: str) -> list[str]:
    """The words of a line as the gate compares them: lowercased, an email or a dotted name kept whole."""
    out = []
    for m in TOKEN.finditer(text.lower()):
        t = m.group().rstrip(".'’-")
        if t.endswith(("'s", "’s")):
            t = t[:-2]
        if t:
            out.append(t)
    return out


def fingerprint(salt: str, words: list[str]) -> str:
    return hashlib.sha256(f"{salt}\0{' '.join(words)}".encode()).hexdigest()


def staged() -> dict:
    names = [n for n in git("diff", "--cached", "--name-only", "-z", "--diff-filter=ACMR").decode().split("\0") if n]
    return {n: git("show", f":{n}") for n in names}


def tracked() -> dict:
    names = [n for n in git("ls-files", "-z").decode().split("\0") if n]
    return {n: pathlib.Path(n).read_bytes() for n in names if pathlib.Path(n).is_file()}


def findings(files: dict, cfg: dict) -> list[str]:
    salt, terms = cfg.get("salt", ""), {}
    for t in cfg.get("terms", []):
        terms.setdefault(t["words"], {})[t["fp"]] = t["kind"]
    refuse, allow = REFUSE_FILES + cfg.get("refuse_files", []), ALLOW_FILES + cfg.get("allow_files", [])
    found = []
    for path, data in sorted(files.items()):
        name = path.rsplit("/", 1)[-1]
        if any(fnmatch.fnmatch(name, p) for p in refuse) and not any(fnmatch.fnmatch(name, p) for p in allow):
            found.append(f"{path}: a file kind that stays out of git (a database, an env file or a key)")
            continue
        if b"\0" in data[:8192]:  # binary
            continue
        for n, line in enumerate(data.decode(errors="replace").splitlines(), 1):
            if OK_MARK in line:
                continue
            kinds = [kind for kind, rx in SECRETS if rx.search(line)]
            if terms:
                words = tokens(line)
                for size, fps in terms.items():
                    for i in range(len(words) - size + 1):
                        kind = fps.get(fingerprint(salt, words[i:i + size]))
                        if kind:
                            kinds.append(kind)
            found += [f"{path}:{n}: {kind}" for kind in dict.fromkeys(kinds)]
    return found


def add(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="gate.py add", description="Add a private term, stored only as a fingerprint.")
    ap.add_argument("term")
    ap.add_argument("--kind", default="a private term", help='what it is, as findings name it: "a person\'s name"')
    a = ap.parse_args(argv)
    words = tokens(a.term)
    if not words:
        print("Nothing to add: the term has no words.", file=sys.stderr)
        return 2
    os.chdir(top())
    path = config_path()
    cfg = load(path)
    cfg["salt"] = cfg.get("salt") or secrets.token_hex(16)
    fp = fingerprint(cfg["salt"], words)
    if any(t["fp"] == fp for t in cfg.setdefault("terms", [])):
        print(f"Already there ({a.kind}, {len(words)} word{'s' * (len(words) > 1)}).")
        return 0
    cfg["terms"].append({"fp": fp, "words": len(words), "kind": a.kind})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(cfg, indent=1) + "\n")
    path.chmod(0o600)
    print(f"Added {a.kind} ({len(words)} word{'s' * (len(words) > 1)}) to {path}.")
    return 0


def main(argv: list[str]) -> int:
    if argv[:1] == ["add"]:
        return add(argv[1:])
    if argv[:1] in (["-h"], ["--help"]):
        print(__doc__)
        return 0
    os.chdir(top())
    path = config_path()
    whole = "--all" in argv
    if whole and not path.exists():
        print(f"note: no private terms set up yet ({path}); checking secrets and file kinds only.", file=sys.stderr)
    found = findings(tracked() if whole else staged(), load(path))
    if not found:
        return 0
    print(f"{'Found' if whole else 'Commit refused:'} {len(found)} place{'s' * (len(found) > 1)} carrying something "
          "private (gate.py). Take it out, or mark an intended mention privacy-ok with its why:", file=sys.stderr)
    for f in found[:40]:
        print(f"  {f}", file=sys.stderr)
    if len(found) > 40:
        print(f"  ...and {len(found) - 40} more", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
