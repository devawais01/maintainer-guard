# 🛡️ Maintainer Guard

**Gemma 4-powered triage for open-source maintainers.** A GitHub Action that automatically reviews every new pull request and issue, so maintainers spend their time on real contributions instead of Hacktoberfest spam.

- 🚫 **Spam PR filter**: reads each PR's diff and description, labels it `spam`, `low-effort`, `needs-work` or `looks-good`, and posts a kind, specific comment explaining why.
- 🔍 **Screenshot → bug report**: when someone opens a vague issue like *"it doesn't work"* with a screenshot, Gemma 4 **reads the image** (error text, stack trace, environment) and posts a structured bug report.
- 🤖 **Fully automatic**: runs on every PR and issue. Nobody has to click anything.

> Built for the Hacktoberfest Hack Day Lahore × AWS Student Builder Group (Virtual University of Pakistan).
> Entered in **Best Use of Gemma 4** and **Best Open-Source AI Project**.

---

## The problem

Every October, maintainers are flooded with pull requests that add someone's name to a list, change one word in a README, or reformat whitespace, just to earn Hacktoberfest credit. At the same time, real users file bug reports that are only a blurry screenshot and "not working." Maintainers burn hours triaging both, and burnout follows.

## How it works

```
 New PR / issue ──► GitHub Action (Maintainer Guard)
                         │
          ┌──────────────┴───────────────┐
          ▼                              ▼
   Pull request                   Issue with screenshots
   1. Fetch diff + metadata       1. Find image links in the issue
   2. Script computes hard facts  2. Download screenshots
      (docs-only? name-list only?  3. Gemma 4 VISION reads the image:
       whitespace-only? size?)        error text, environment, UI state
   3. Gemma 4 judges the change   4. Writes a structured bug report
      with those facts as ground      (steps, expected/actual, cause,
      truth                           missing info)
   4. Label + comment (+ optional  5. Label guard:bug-report + comment
      auto-close of high-confidence
      spam)
```

**Why the hybrid design:** a deterministic script computes facts the PR author can't argue with (e.g. *"only CONTRIBUTORS.md changed"*). Gemma 4 gets those facts plus the diff and makes the judgement call that rules can't: is this typo fix real, or is this rewording pointless?

## Why Gemma 4

- **Multimodal:** one open model handles both code diffs (text) and screenshots (images).
- **Open weights:** maintainers can self-host it (e.g. with Ollama) so no repo data has to leave their infrastructure, which matters for open-source projects that can't send code to a closed vendor.
- **Small and cheap:** the 26B-A4B mixture-of-experts model activates only ~4B parameters per token, fast enough to run on every PR.

Default model: `gemma-4-26b-a4b-it` via the Gemini API. Switch to `gemma-4-31b-it` with the `model` input.

## Safety by design

- **Prompt-injection resistant:** PR and issue text is wrapped and marked untrusted; the model is told to ignore instructions inside it. Even if it's fooled, the code **only accepts the four allowed verdicts**. Anything else falls back to `needs-work`.
- **Never runs contributor code:** uses `pull_request_target` but only checks out the base repository, never the PR branch.
- **Humans decide:** it labels and comments by default. Auto-closing spam is **off** unless you enable it, and then only above a confidence threshold (default 90%).
- **Never breaks CI:** if the model or API fails, the job logs a warning and exits cleanly.
- **No comment spam:** re-runs edit the bot's existing comment instead of posting new ones.
- Skips bots, and skips owners/members/collaborators by default.

## Quick start (2 minutes)

1. Get a free Gemini API key at [Google AI Studio](https://aistudio.google.com/apikey).
2. In your repo: **Settings → Secrets and variables → Actions → New repository secret** → name `GEMINI_API_KEY`.
3. Add `.github/workflows/maintainer-guard.yml`:

```yaml
name: Maintainer Guard
on:
  pull_request_target:
    types: [opened, edited, synchronize, reopened]
  issues:
    types: [opened, edited]
permissions:
  contents: read
  issues: write
  pull-requests: write
jobs:
  triage:
    runs-on: ubuntu-latest
    steps:
      - uses: devawais01/maintainer-guard@main
        with:
          gemini_api_key: ${{ secrets.GEMINI_API_KEY }}
```

### Options

| Input | Default | What it does |
|---|---|---|
| `model` | `gemma-4-26b-a4b-it` | Gemma 4 model id |
| `close_spam` | `false` | Auto-close PRs judged spam |
| `close_threshold` | `0.9` | Minimum confidence to auto-close |
| `include_maintainers` | `false` | Also triage PRs from owners/members |
| `dry_run` | `false` | Log decisions only; no labels or comments |

## Try it locally (no GitHub needed)

```bash
pip install -r requirements.txt
export GEMINI_API_KEY=your_key

# Pull-request triage on sample diffs
python -m guard.cli pr samples/spam_name.diff --title "Added my name" --body "hacktoberfest please merge"
python -m guard.cli pr samples/low_effort.diff --title "Update README.md"
python -m guard.cli pr samples/good_fix.diff --title "Fix Kelvin conversion" --body "0°C is 273.15K, not 273. Added a test."

# Screenshot → bug report
python -m guard.cli screenshot path/to/error_screenshot.png --title "app not working"
```

## Run the tests

```bash
pip install pytest && pytest -q
```

The tests mock Gemma, so they run offline. They cover diff parsing, the heuristics, JSON extraction, comment rendering, and the guarantee that an injected or malformed verdict can't trigger an unlisted action.

## Project structure

```
action.yml              # the GitHub Action definition
guard/
  main.py               # Action entry point (dispatches PR vs issue events)
  pr_triage.py          # PR prompt, verdict validation, comment
  issue_triage.py       # screenshot → structured bug report
  heuristics.py         # deterministic signals + image link extraction
  gemma.py              # Gemma 4 client (Gemini API REST) + robust JSON parsing
  github_api.py         # labels, comments (upsert), close
  cli.py                # local runner for testing/demos
samples/                # example diffs: spam, low-effort, good fix
tests/                  # offline unit tests
```

## Roadmap

- Self-hosted mode: point at a local Ollama Gemma 4 endpoint
- Duplicate-issue detection using the screenshot + text
- Weekly maintainer digest of what was triaged

## License

[MIT](LICENSE)
