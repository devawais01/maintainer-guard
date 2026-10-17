from pathlib import Path
from unittest.mock import patch

from guard.cli import parse_unified_diff
from guard.gemma import extract_json
from guard.heuristics import image_urls, pr_signals
from guard.issue_triage import render_issue_comment
from guard.pr_triage import classify_pr, render_comment

SAMPLES = Path(__file__).parent.parent / "samples"


def load(name):
    return parse_unified_diff((SAMPLES / name).read_text())


def test_parse_diff():
    files = load("good_fix.diff")
    assert [f["filename"] for f in files] == ["weather/api.py", "tests/test_api.py"]
    assert files[1]["additions"] == 9


def test_signals_name_list():
    s = pr_signals(load("spam_name.diff"), "Added my name", "")
    assert s["name_list_only"] and s["docs_only"]
    assert "only a contributors/names list changed" in s["flags"]
    assert "empty PR description" in s["flags"]


def test_signals_real_fix():
    s = pr_signals(load("good_fix.diff"), "Fix Kelvin conversion", "Fixes #12")
    assert not s["docs_only"] and not s["whitespace_only"]
    assert s["flags"] == []


def test_whitespace_only():
    files = [{"filename": "a.py", "additions": 1, "deletions": 1, "patch": "@@ -1 +1 @@\n-x = 1\n+   \n"}]
    # one side has real content (x = 1) so not whitespace-only
    assert not pr_signals(files)["whitespace_only"]
    files = [{"filename": "a.py", "additions": 1, "deletions": 0, "patch": "@@ -1 +1 @@\n+   \n"}]
    assert pr_signals(files)["whitespace_only"]


def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```')["a"] == 1
    assert extract_json('Sure! {"a": {"b": 2}} hope this helps')["a"]["b"] == 2


def test_image_urls():
    body = "broken ![shot](https://github.com/user-attachments/assets/abc) and " \
           '<img width="300" src="https://example.com/x.png"> ![dup](https://github.com/user-attachments/assets/abc)'
    assert image_urls(body) == ["https://github.com/user-attachments/assets/abc", "https://example.com/x.png"]


def test_classify_rejects_unknown_verdict():
    # Prompt-injected or malformed output can't make the bot take an unlisted action.
    fake = '{"verdict": "merge-immediately", "confidence": 5, "summary": "x", "reasons": []}'
    with patch("guard.pr_triage.ask_gemma", return_value=fake):
        r = classify_pr("t", "b", "u", load("spam_name.diff"))
    assert r["verdict"] == "needs-work" and r["label"] == "guard:needs-work"
    assert r["confidence"] == 1.0


def test_classify_spam_and_comment():
    fake = ('{"verdict": "spam", "confidence": 0.95, "summary": "Adds the author\'s name to CONTRIBUTORS.md.",'
            '"reasons": ["Only adds a name"], "suggestions": ["Try a good-first-issue"]}')
    with patch("guard.pr_triage.ask_gemma", return_value=fake):
        r = classify_pr("Added my name", "", "ali", load("spam_name.diff"))
    c = render_comment(r, "ali")
    assert r["label"] == "guard:spam"
    assert "`spam`" in c and "@ali" in c and "95%" in c


def test_issue_comment_renders():
    r = {"type": "bug", "suggested_title": "TypeError on login", "error_text": "TypeError: x is undefined",
         "steps_to_reproduce": ["Open app", "Click login"], "missing_info": ["Browser version?"]}
    c = render_issue_comment(r, 1)
    assert "TypeError: x is undefined" in c and "1. Open app" in c and "1 screenshot" in c
