# Submission form text (copy-paste)

**Project name:** Maintainer Guard

**Description:**

**Maintainer Guard** is a GitHub Action that uses **Gemma 4** to automatically triage pull requests and issues, protecting open-source maintainers from Hacktoberfest spam and vague bug reports.

**The problem:** every October, maintainers get flooded with PRs that only add a name to a list, change one README word, or reformat whitespace. Meanwhile real users file issues that are just a screenshot and "not working." Triage eats maintainers' time and leads to burnout.

**What it does, automatically on every PR and issue:**
- 🚫 **PR triage:** a script computes hard facts (docs-only? name-list only? whitespace-only? size?), then Gemma 4 reads the diff and labels the PR `spam`, `low-effort`, `needs-work` or `looks-good`, with a kind comment explaining why and how to improve. High-confidence spam can optionally be auto-closed.
- 🔍 **Screenshot → bug report:** when an issue contains screenshots, Gemma 4's **vision** reads the error text, stack trace and environment from the image and posts a structured bug report (steps, expected vs actual, likely cause, missing info).

**Why Gemma 4:** one open-weights model handles both text (diffs) and images (screenshots), it's light enough to run on every PR, and because it's open-weight, maintainers can self-host it so their code never has to leave their infrastructure.

**Safety:** untrusted PR text is isolated against prompt injection, and the code only accepts the four allowed verdicts. It never runs contributor code, never posts duplicate comments, never fails CI, and humans make the final call.

Open source under the MIT license, with offline unit tests.

**Technologies:** Python, GitHub Actions, GitHub REST API, Gemma 4 (gemma-4-26b-a4b-it), Gemini API

**AI your project calls:** Gemma

**Prize categories:** Best Use of Gemma 4 · Best Open-Source AI Project
