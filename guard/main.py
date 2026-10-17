"""Entry point for the GitHub Action. Dispatches on the triggering event."""
import json
import os
import sys

from .github_api import GitHub
from .heuristics import image_urls
from .issue_triage import analyze_issue, render_issue_comment
from .pr_triage import classify_pr, render_comment

TRUSTED = {"OWNER", "MEMBER", "COLLABORATOR"}


def env_bool(name, default=False):
    return os.environ.get(name, str(default)).strip().lower() in ("1", "true", "yes")


def handle_pr(gh, pr):
    author = pr["user"]["login"]
    if pr["user"].get("type") == "Bot":
        print(f"Skipping bot PR from {author}")
        return
    if pr.get("author_association") in TRUSTED and not env_bool("GUARD_INCLUDE_MAINTAINERS"):
        print(f"Skipping PR from trusted author {author} ({pr['author_association']})")
        return

    files = gh.pr_files(pr["number"])
    result = classify_pr(pr.get("title", ""), pr.get("body") or "", author, files)
    print(json.dumps({k: v for k, v in result.items() if k != "signals"}, indent=2))

    gh.set_guard_label(pr["number"], result["label"])
    gh.upsert_comment(pr["number"], render_comment(result, author))

    threshold = float(os.environ.get("GUARD_CLOSE_THRESHOLD", "0.9"))
    if env_bool("GUARD_CLOSE_SPAM") and result["verdict"] == "spam" and result["confidence"] >= threshold:
        gh.close(pr["number"])
        print(f"Closed spam PR #{pr['number']}")


def handle_issue(gh, issue):
    if issue.get("pull_request"):
        return
    urls = image_urls(issue.get("body") or "")[:4]
    if not urls:
        print("Issue has no screenshots; nothing to do.")
        return
    images = [img for img in (gh.download(u) for u in urls) if img]
    if not images:
        print("Could not download any screenshots.")
        return

    result = analyze_issue(gh.repo, issue.get("title", ""), issue.get("body") or "", images)
    print(json.dumps(result, indent=2))
    if result.get("type") == "bug":
        gh.set_guard_label(issue["number"], "guard:bug-report")
    gh.upsert_comment(issue["number"], render_issue_comment(result, len(images)))


def main():
    event_name = os.environ.get("GITHUB_EVENT_NAME", "")
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as f:
        event = json.load(f)
    gh = GitHub(os.environ["GITHUB_REPOSITORY"], dry_run=env_bool("GUARD_DRY_RUN"))

    if event_name in ("pull_request", "pull_request_target") and "pull_request" in event:
        handle_pr(gh, event["pull_request"])
    elif event_name == "issues" and "issue" in event:
        handle_issue(gh, event["issue"])
    else:
        print(f"Event '{event_name}' not handled; nothing to do.")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:  # never fail a contributor's CI because the bot had a bad day
        print(f"::warning::Maintainer Guard could not finish: {e}")
        sys.exit(0)
