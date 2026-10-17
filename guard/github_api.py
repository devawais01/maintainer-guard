"""Tiny GitHub REST helper — only the calls Maintainer Guard needs."""
import os

import requests

API = "https://api.github.com"
MARKER = "<!-- maintainer-guard -->"

LABEL_COLORS = {
    "guard:spam": "b60205",
    "guard:low-effort": "fbca04",
    "guard:needs-work": "d4c5f9",
    "guard:looks-good": "0e8a16",
    "guard:bug-report": "1d76db",
}


class GitHub:
    def __init__(self, repo, token=None, dry_run=False):
        self.repo = repo
        self.dry_run = dry_run
        self.s = requests.Session()
        self.s.headers.update({
            "Authorization": f"Bearer {token or os.environ.get('GITHUB_TOKEN', '')}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        })

    def _get(self, path, **params):
        r = self.s.get(f"{API}{path}", params=params, timeout=30)
        r.raise_for_status()
        return r.json()

    def pr_files(self, number):
        files, page = [], 1
        while page <= 10:
            batch = self._get(f"/repos/{self.repo}/pulls/{number}/files", per_page=100, page=page)
            files.extend(batch)
            if len(batch) < 100:
                break
            page += 1
        return files

    def download(self, url, max_bytes=5_000_000):
        """Download an image attachment. Returns (bytes, mime) or None."""
        r = self.s.get(url, timeout=30, stream=True, allow_redirects=True)
        if r.status_code != 200:
            return None
        mime = r.headers.get("Content-Type", "").split(";")[0]
        if not mime.startswith("image/"):
            return None
        data = r.raw.read(max_bytes + 1, decode_content=True)
        if len(data) > max_bytes:
            return None
        return data, mime

    # ---- write actions (skipped in dry-run) ----

    def ensure_label(self, name):
        if self.dry_run:
            return
        self.s.post(f"{API}/repos/{self.repo}/labels", timeout=30,
                    json={"name": name, "color": LABEL_COLORS.get(name, "ededed"),
                          "description": "Added by Maintainer Guard"})  # 422 = exists, fine

    def set_guard_label(self, number, label):
        """Apply one guard:* label and remove any stale guard:* labels."""
        if self.dry_run:
            print(f"[dry-run] label #{number} -> {label}")
            return
        self.ensure_label(label)
        current = [l["name"] for l in self._get(f"/repos/{self.repo}/issues/{number}/labels")]
        for old in current:
            if old.startswith("guard:") and old != label:
                self.s.delete(f"{API}/repos/{self.repo}/issues/{number}/labels/{old}", timeout=30)
        self.s.post(f"{API}/repos/{self.repo}/issues/{number}/labels", json={"labels": [label]}, timeout=30)

    def upsert_comment(self, number, body):
        """Post our comment, or edit the existing one so re-runs don't spam the thread."""
        body = f"{MARKER}\n{body}"
        if self.dry_run:
            print(f"[dry-run] comment on #{number}:\n{body}\n")
            return
        comments = self._get(f"/repos/{self.repo}/issues/{number}/comments", per_page=100)
        for c in comments:
            if MARKER in (c.get("body") or ""):
                self.s.patch(f"{API}/repos/{self.repo}/issues/comments/{c['id']}", json={"body": body}, timeout=30)
                return
        self.s.post(f"{API}/repos/{self.repo}/issues/{number}/comments", json={"body": body}, timeout=30)

    def close(self, number):
        if self.dry_run:
            print(f"[dry-run] close #{number}")
            return
        self.s.patch(f"{API}/repos/{self.repo}/issues/{number}", json={"state": "closed"}, timeout=30)
