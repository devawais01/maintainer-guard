"""Fast, deterministic signals computed before Gemma is asked anything.

These give the model hard facts (so it can't be talked out of them by a PR description)
and let obvious cases be explained clearly in the comment.
"""
import re

DOC_EXT = (".md", ".mdx", ".markdown", ".rst", ".txt", ".adoc")
NAME_LIST_FILES = re.compile(r"(contributors|authors|thanks|people|members)", re.I)


def pr_signals(files, title="", body=""):
    """files: list of dicts like GitHub's /pulls/{n}/files (filename, additions, deletions, patch)."""
    total_add = sum(f.get("additions", 0) for f in files)
    total_del = sum(f.get("deletions", 0) for f in files)
    names = [f.get("filename", "") for f in files]
    docs_only = bool(names) and all(n.lower().endswith(DOC_EXT) for n in names)
    name_list_only = bool(names) and all(NAME_LIST_FILES.search(n) for n in names)

    whitespace_only = True
    for f in files:
        for line in (f.get("patch") or "").splitlines():
            if line.startswith(("+++", "---", "@@")):
                continue
            if line[:1] in "+-" and line[1:].strip():
                whitespace_only = False
                break
        if not whitespace_only:
            break
    if not files:
        whitespace_only = False

    text = f"{title}\n{body}".lower()
    hacktober_bait = any(k in text for k in (
           "hacktoberfest", "please merge", "accept my pr", "for hacktober",
           "merge my pr", "plz merge", "kindly merge", "add hacktoberfest-accepted",
       ))

    flags = []
    if total_add + total_del <= 3:
        flags.append("tiny change (3 lines or fewer)")
    if docs_only:
        flags.append("only documentation files changed")
    if name_list_only:
        flags.append("only a contributors/names list changed")
    if whitespace_only:
        flags.append("only whitespace changed")
    if not (body or "").strip():
        flags.append("empty PR description")
    if hacktober_bait:
        flags.append("description asks for a merge/Hacktoberfest credit")

    return {
        "files_changed": len(files),
        "additions": total_add,
        "deletions": total_del,
        "docs_only": docs_only,
        "name_list_only": name_list_only,
        "whitespace_only": whitespace_only,
        "flags": flags,
    }


IMG_MD = re.compile(r"!\[[^\]]*\]\((https?://[^)\s]+)\)")
IMG_HTML = re.compile(r"<img[^>]+src=[\"'](https?://[^\"']+)[\"']", re.I)


def image_urls(markdown):
    """Find image links in an issue body (markdown or <img> tags), in order, de-duplicated."""
    seen, out = set(), []
    for url in IMG_MD.findall(markdown or "") + IMG_HTML.findall(markdown or ""):
        if url not in seen:
            seen.add(url)
            out.append(url)
    return out
