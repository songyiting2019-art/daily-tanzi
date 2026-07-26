#!/usr/bin/env python3
"""Publish one prebuilt issue into the GitHub Pages root and seven-issue archive."""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "issues.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True, help="Scheduled issue date in YYYY-MM-DD")
    return parser.parse_args()


def snapshot_issue(date: str, document: str) -> None:
    issue_dir = ROOT / "issues" / date
    issue_dir.mkdir(parents=True, exist_ok=True)
    snapshot = document
    snapshot = snapshot.replace('href="./style.css"', 'href="../../style.css"')
    snapshot = snapshot.replace('src="./assets/', 'src="../../assets/')
    snapshot = snapshot.replace('href="./archive/"', 'href="../../archive/"')
    snapshot = snapshot.replace(
        '<body id="top">',
        '<body id="top">\n  <a class="issue-home-link" href="../../">返回最新一期</a>',
    )
    (issue_dir / "index.html").write_text(snapshot, encoding="utf-8")


def build_archive(issues: list[dict[str, str]]) -> None:
    cards = []
    for issue in issues:
        cards.append(
            f"""      <article class="archive-card">
        <p class="story-index">{html.escape(issue["label"])}</p>
        <h2>每日谈资</h2>
        <p>{html.escape(issue["summary"])}</p>
        <div class="archive-actions">
          <a href="../issues/{issue["date"]}/">阅读这一期</a>
        </div>
      </article>"""
        )
    page = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
  <meta name="theme-color" content="#f4efe6">
  <meta name="robots" content="noindex,nofollow">
  <title>每日谈资｜最近7期</title>
  <link rel="stylesheet" href="../style.css">
</head>
<body class="archive-shell">
  <header class="cover archive-cover">
    <p class="eyebrow">随时翻回来，再捡一个能聊的点</p>
    <h1 class="archive-title">最近7期</h1>
    <p class="tease">网页只保留最近七期。更早的选题仍留在内部去重记录里，不会换件衣服又端上来。</p>
    <div class="release-actions">
      <a class="primary-action" href="../">返回最新一期</a>
    </div>
  </header>
  <main class="archive-list">
{chr(10).join(cards)}
  </main>
</body>
</html>
"""
    archive_dir = ROOT / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    (archive_dir / "index.html").write_text(page, encoding="utf-8")


def main() -> None:
    args = parse_args()
    datetime.strptime(args.date, "%Y-%m-%d")
    scheduled = ROOT / "scheduled" / args.date
    source_path = scheduled / "index.html"
    metadata_path = scheduled / "metadata.json"
    if not source_path.exists() or not metadata_path.exists():
        raise SystemExit(f"No scheduled issue found for {args.date}")

    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    if metadata["date"] != args.date:
        raise SystemExit("Scheduled metadata date does not match requested date")
    source = source_path.read_text(encoding="utf-8")
    if f"每日谈资｜{metadata['label']}" not in source:
        raise SystemExit("Scheduled HTML title does not match metadata")

    assets_dir = scheduled / "assets"
    for asset in assets_dir.iterdir():
        if asset.is_file():
            shutil.copy2(asset, ROOT / "assets" / asset.name)

    (ROOT / "index.html").write_text(source, encoding="utf-8")
    snapshot_issue(args.date, source)

    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    issues = [issue for issue in manifest["issues"] if issue["date"] != args.date]
    issues.insert(0, metadata)
    issues = issues[: int(manifest.get("retention", 7))]
    MANIFEST.write_text(
        json.dumps({"retention": 7, "issues": issues}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    build_archive(issues)

    keep_dates = {issue["date"] for issue in issues}
    issues_root = ROOT / "issues"
    for issue_dir in issues_root.iterdir():
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", issue_dir.name) and issue_dir.name not in keep_dates:
            shutil.rmtree(issue_dir)

    print(f"Prepared {args.date} as the latest issue")


if __name__ == "__main__":
    main()
