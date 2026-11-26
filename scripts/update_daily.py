#!/usr/bin/env python3
"""Refresh the small, source-verified daily answer sample for Deep Dive.

Exits nonzero rather than publishing wrong-day or unverifiable questions.
This does not copy or claim to replicate Krillion's complete answer database.
"""
from __future__ import annotations

import html
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dist" / "data" / "daily.json"
CATEGORIES = ["GENERAL KNOWLEDGE", "FOOD & DRINK", "SPORTS", "GEOGRAPHY", "TV & ENTERTAINMENT", "GEOGRAPHY", "TECHNOLOGY"]
VALID_SCORES = {10, 15, 30, 60, 85, 100}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (compatible; DailyDiveUpdater/1.0)", "Accept": "text/html"})
    with urllib.request.urlopen(req, timeout=25) as response:
        if response.status != 200:
            raise RuntimeError(f"Unexpected HTTP {response.status}: {url}")
        return response.read(3_000_000).decode("utf-8", errors="replace")


def plain(fragment: str) -> str:
    text = re.sub(r"<[^>]+>", "", fragment)
    return " ".join(html.unescape(text).split())


def compact_key(answer: str) -> str:
    # Mirrors the game's case/diacritic-insensitive matching closely enough
    # to deduplicate examples in the generated JSON.
    import unicodedata

    s = unicodedata.normalize("NFKD", answer.lower())
    return "".join(c for c in s if c.isascii() and c.isalnum())


def collect(date: str) -> dict:
    prompts_url = f"https://krilliontoday.com/answers/{date}"
    answers_url = "https://krillionquestions.com/"
    prompts_page, answers_page = fetch(prompts_url), fetch(answers_url)

    prompts = {}
    for n, label in re.findall(r'<a\b[^>]*href="#prompt-([1-7])"[^>]*>(.*?)</a>', prompts_page, re.S | re.I):
        prompts[int(n)] = plain(label)
    if sorted(prompts) != list(range(1, 8)) or not all(p.lower().startswith('name ') for p in prompts.values()):
        raise RuntimeError("Today's official question wording could not be verified")

    # The daily companion prints dates in each question's heading. Guard against
    # stale pages and partial refreshes around midnight New York time.
    cards = re.findall(r'<article\b[^>]*class="question-card"[^>]*id="q(0[1-7])"[^>]*>(.*?)</article>', answers_page, re.S | re.I)
    if len(cards) != 7:
        raise RuntimeError("Today's answer source does not have seven question cards")
    questions = []
    for i, (number, card) in enumerate(cards, start=1):
        if int(number) != i or f'Top answers today · {date}' not in plain(card):
            # Some categories use "Top picks" rather than "Top answers today".
            if int(number) != i or date not in card:
                raise RuntimeError(f"Question {i} is not dated {date}")
        examples = re.findall(r'<li[^>]*>\s*<strong>(.*?)</strong>\s*·\s*(\d{2,3})\s*pts\s*</li>', card, re.S | re.I)
        answers: dict[str, int] = {}
        unique = set()
        for label, score_text in examples:
            label, score = plain(label), int(score_text)
            key = compact_key(label)
            if not key or key in unique or score not in VALID_SCORES:
                continue
            unique.add(key)
            answers[label] = score
        if len(answers) < 7 or not any(v == 100 for v in answers.values()) or not any(v == 10 for v in answers.values()):
            raise RuntimeError(f"Question {i} has too few verified scoring examples")
        questions.append({"cat": CATEGORIES[i - 1], "q": prompts[i], "a": answers})

    current_dive = re.search(r'<title>[^<]*\(Dive\s*#(\d+)\)</title>', prompts_page, re.I)
    if not current_dive:
        raise RuntimeError("Could not verify daily dive number")
    return {"date": date, "dive": int(current_dive.group(1)), "source": [prompts_url, answers_url], "questions": questions}


def main() -> int:
    date = datetime.now(ZoneInfo("America/New_York")).strftime("%Y-%m-%d")
    try:
        data = collect(date)
    except Exception as exc:
        print(f"No safe update for {date}: {exc}", file=sys.stderr)
        return 1

    content = json.dumps(data, ensure_ascii=False, indent=2) + "\n"
    if DEST.exists() and DEST.read_text(encoding="utf-8") == content:
        print(f"Daily # {data['dive']} already current")
        return 0
    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_text(content, encoding="utf-8")
    print(f"Saved {date} daily #{data['dive']} with {sum(len(q['a']) for q in data['questions'])} example scores")
    return 0


if __name__ == "__main__":
    sys.exit(main())
