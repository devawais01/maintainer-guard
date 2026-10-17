"""Run Maintainer Guard locally, without GitHub — handy for testing and demos.

    python -m guard.cli pr samples/spam_name.diff --title "Added my name"
    python -m guard.cli screenshot samples/error.png --title "app crashes"
"""
import argparse
import mimetypes
import re

from .issue_triage import analyze_issue, render_issue_comment
from .pr_triage import classify_pr, render_comment


def parse_unified_diff(text):
    """Turn a `git diff` into the same shape GitHub's /pulls/{n}/files API returns."""
    files = []
    for block in re.split(r"(?m)^diff --git ", text):
        if not block.strip():
            continue
        m = re.search(r"(?m)^\+\+\+ b/(.+)$", block) or re.search(r"^a/\S+ b/(\S+)", block)
        name = m.group(1).strip() if m else "unknown"
        hunk_start = block.find("@@")
        patch = block[hunk_start:] if hunk_start != -1 else ""
        adds = sum(1 for l in patch.splitlines() if l.startswith("+") and not l.startswith("+++"))
        dels = sum(1 for l in patch.splitlines() if l.startswith("-") and not l.startswith("---"))
        files.append({"filename": name, "additions": adds, "deletions": dels, "patch": patch})
    return files


def main():
    p = argparse.ArgumentParser(prog="maintainer-guard")
    sub = p.add_subparsers(dest="cmd", required=True)

    pr = sub.add_parser("pr", help="classify a diff as if it were a pull request")
    pr.add_argument("diff")
    pr.add_argument("--title", default="Update")
    pr.add_argument("--body", default="")
    pr.add_argument("--author", default="contributor")

    sc = sub.add_parser("screenshot", help="turn a screenshot into a structured bug report")
    sc.add_argument("images", nargs="+")
    sc.add_argument("--title", default="It doesn't work")
    sc.add_argument("--body", default="see screenshot")
    sc.add_argument("--repo", default="example/project")

    a = p.parse_args()
    if a.cmd == "pr":
        with open(a.diff, encoding="utf-8") as f:
            files = parse_unified_diff(f.read())
        result = classify_pr(a.title, a.body, a.author, files)
        print(render_comment(result, a.author))
    else:
        imgs = []
        for path in a.images:
            mime = mimetypes.guess_type(path)[0] or "image/png"
            with open(path, "rb") as f:
                imgs.append((f.read(), mime))
        result = analyze_issue(a.repo, a.title, a.body, imgs)
        print(render_issue_comment(result, len(imgs)))


if __name__ == "__main__":
    main()
