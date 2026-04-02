"""Generate a quality report for all (repo, bot) pairs.

Scans assembled timelines to detect template/scripted human responses,
low-engagement repos, and other quality signals. Outputs a JSON report
that can be used for filtering in the API or further analysis.

Does NOT modify any data — read-only.

Usage:
    cd ~/crb/online/etl
    PYTHONPATH=. uv run python scripts/generate_quality_report.py -o quality_report.json
    PYTHONPATH=. uv run python scripts/generate_quality_report.py --min-prs 10 --limit 500 -o quality_report.json
    PYTHONPATH=. uv run python scripts/generate_quality_report.py --bot "cubic-dev-ai[bot]" -o cubic_report.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from typing import Any

from config import DBConfig
from db.connection import DBAdapter
from pipeline.quality import is_bot_username

logger = logging.getLogger(__name__)

COMMENT_EVENT_TYPES = frozenset({"review", "review_comment", "issue_comment"})

# Thresholds for flagging
SCRIPTED_DIVERSITY_THRESHOLD = 0.2
LOW_DIVERSITY_THRESHOLD = 0.4
TEMPLATE_PREFIX_THRESHOLD = 0.5
SHORT_COMMENT_THRESHOLD = 0.8
SHORT_COMMENT_LENGTH = 50
MIN_PREFIX_LENGTH = 50
# Minimum comments to trigger any flag
MIN_COMMENTS_FOR_FLAG = 5
MIN_USER_COMMENTS_FOR_FLAG = 5


def _normalize(text: str) -> str:
    """Normalize comment text for comparison."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text


def _extract_human_comments_after_bot(
    events: list[dict[str, Any]],
    chatbot_username: str,
) -> list[tuple[str, str]]:
    """Extract (actor, body) pairs for human comments after bot's first review."""
    bot_lower = chatbot_username.lower()

    bot_first_ts: str | None = None
    for e in events:
        actor = (e.get("actor") or "").lower()
        if actor == bot_lower and e.get("event_type") in COMMENT_EVENT_TYPES:
            bot_first_ts = e.get("timestamp")
            break

    if bot_first_ts is None:
        return []

    comments: list[tuple[str, str]] = []
    for e in events:
        ts = e.get("timestamp", "")
        if ts <= bot_first_ts:
            continue
        actor = e.get("actor") or ""
        if not actor or actor.lower() == bot_lower:
            continue
        if is_bot_username(actor):
            continue
        etype = e.get("event_type", "")
        if etype in COMMENT_EVENT_TYPES:
            body = (e.get("data") or {}).get("body") or ""
            body = body.strip()
            if body:
                comments.append((actor, body))

    return comments


def _longest_common_prefix(strings: list[str]) -> str:
    if not strings:
        return ""
    shortest = min(strings, key=len)
    for i, char in enumerate(shortest):
        if any(s[i] != char for s in strings):
            return shortest[:i]
    return shortest


def _compute_prefix_ratio(
    comments: list[str],
    min_prefix_len: int = MIN_PREFIX_LENGTH,
) -> tuple[float, str]:
    """Fraction of comments sharing a prefix >= min_prefix_len chars."""
    if len(comments) < 3:
        return 0.0, ""

    normalized = [_normalize(c) for c in comments]

    best_ratio = 0.0
    best_prefix = ""
    for candidate in normalized:
        if len(candidate) < min_prefix_len:
            continue
        prefix = candidate[:min_prefix_len]
        matching = sum(1 for c in normalized if c.startswith(prefix))
        ratio = matching / len(normalized)
        if ratio > best_ratio:
            matching_comments = [c for c in normalized if c.startswith(prefix)]
            actual_prefix = _longest_common_prefix(matching_comments)
            best_ratio = ratio
            best_prefix = actual_prefix

    return best_ratio, best_prefix


def _classify_pair(
    total_comments: int,
    unique_ratio: float,
    prefix_ratio: float,
    short_ratio: float,
    commenter_stats: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Produce a list of flag dicts for a (repo, bot) pair."""
    flags: list[dict[str, Any]] = []

    if total_comments == 0:
        flags.append({"type": "no_human_comments"})
        return flags

    if unique_ratio < SCRIPTED_DIVERSITY_THRESHOLD and total_comments >= MIN_COMMENTS_FOR_FLAG:
        flags.append({"type": "scripted", "diversity": round(unique_ratio, 3)})
    elif unique_ratio < LOW_DIVERSITY_THRESHOLD and total_comments >= MIN_COMMENTS_FOR_FLAG:
        flags.append({"type": "low_diversity", "diversity": round(unique_ratio, 3)})

    if prefix_ratio >= TEMPLATE_PREFIX_THRESHOLD and total_comments >= MIN_COMMENTS_FOR_FLAG:
        flags.append({"type": "template_prefix", "prefix_ratio": round(prefix_ratio, 3)})

    if short_ratio > SHORT_COMMENT_THRESHOLD and total_comments >= MIN_COMMENTS_FOR_FLAG:
        flags.append({"type": "mostly_short", "short_ratio": round(short_ratio, 3)})

    for actor, cs in commenter_stats.items():
        if cs["count"] < MIN_USER_COMMENTS_FOR_FLAG:
            continue
        if cs["prefix_ratio"] >= TEMPLATE_PREFIX_THRESHOLD:
            flags.append({
                "type": "user_template",
                "user": actor,
                "prefix_ratio": round(cs["prefix_ratio"], 3),
                "prefix_preview": cs.get("prefix", "")[:120],
            })
        elif cs["diversity"] < 0.3:
            flags.append({
                "type": "user_scripted",
                "user": actor,
                "diversity": round(cs["diversity"], 3),
            })

    return flags


async def _analyze_pair(
    db: DBAdapter,
    repo: str,
    chatbot: str,
    pr_count: int,
    include_unmerged: bool,
) -> dict[str, Any]:
    """Analyze a single (repo, bot) pair and return structured results."""
    merged_clause = "" if include_unmerged else "AND p.pr_merged = TRUE"
    rows = await db.fetchall(*db._translate_params(
        f"""
        SELECT p.assembled
        FROM prs p
        JOIN chatbots c ON c.id = p.chatbot_id
        WHERE p.repo_name = $1
          AND c.github_username = $2
          AND p.status = 'analyzed'
          AND p.assembled IS NOT NULL
          {merged_clause}
        ORDER BY p.id
        LIMIT 500
        """,
        (repo, chatbot),
    ))

    commenter_comments: dict[str, list[str]] = defaultdict(list)
    prs_with_comments = 0
    for row in rows:
        assembled = json.loads(row["assembled"])
        comments = _extract_human_comments_after_bot(
            assembled.get("events", []), chatbot
        )
        if comments:
            prs_with_comments += 1
        for actor, body in comments:
            commenter_comments[actor].append(body)

    all_comments = [body for bodies in commenter_comments.values() for body in bodies]
    total = len(all_comments)

    if total == 0:
        result: dict[str, Any] = {
            "repo": repo,
            "chatbot": chatbot,
            "pr_count": pr_count,
            "prs_with_comments": 0,
            "total_comments": 0,
            "unique_comments": 0,
            "unique_ratio": 0.0,
            "short_ratio": 0.0,
            "prefix_ratio": 0.0,
            "commenters": {},
        }
        result["flags"] = _classify_pair(0, 0, 0, 0, {})
        return result

    normalized = [_normalize(c) for c in all_comments]
    unique_count = len(set(normalized))
    unique_ratio = unique_count / total
    short_count = sum(1 for c in all_comments if len(c) < SHORT_COMMENT_LENGTH)
    short_ratio = short_count / total
    prefix_ratio, shared_prefix = _compute_prefix_ratio(all_comments)

    commenter_stats: dict[str, dict[str, Any]] = {}
    for actor, bodies in commenter_comments.items():
        n = [_normalize(b) for b in bodies]
        u = len(set(n))
        pr_ratio, pr_prefix = _compute_prefix_ratio(bodies)
        commenter_stats[actor] = {
            "count": len(bodies),
            "unique": u,
            "diversity": round(u / len(n), 3) if n else 0,
            "prefix_ratio": round(pr_ratio, 3),
            "prefix": pr_prefix[:120] if pr_prefix else "",
        }

    flags = _classify_pair(total, unique_ratio, prefix_ratio, short_ratio, commenter_stats)

    return {
        "repo": repo,
        "chatbot": chatbot,
        "pr_count": pr_count,
        "prs_with_comments": prs_with_comments,
        "total_comments": total,
        "unique_comments": unique_count,
        "unique_ratio": round(unique_ratio, 3),
        "short_ratio": round(short_ratio, 3),
        "prefix_ratio": round(prefix_ratio, 3),
        "shared_prefix": shared_prefix[:120] if shared_prefix else "",
        "commenters": commenter_stats,
        "flags": flags,
    }


async def run(args: argparse.Namespace) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    cfg = DBConfig()
    db = DBAdapter(cfg.database_url)
    await db.connect()

    try:
        bot_clause = f"AND c.github_username = '{args.bot}'" if args.bot else ""
        repo_clause = f"AND p.repo_name = '{args.repo}'" if args.repo else ""
        merged_clause = "" if args.include_unmerged else "AND p.pr_merged = TRUE"

        logger.info(
            "Scanning (repo, bot) pairs with >= %d PRs [limit=%d, %s]",
            args.min_prs, args.limit,
            "include-unmerged" if args.include_unmerged else "merged-only",
        )

        pairs = await db.fetchall(f"""
            SELECT p.repo_name, c.github_username AS chatbot,
                   COUNT(*) AS pr_count
            FROM prs p
            JOIN chatbots c ON c.id = p.chatbot_id
            WHERE p.status = 'analyzed'
              AND p.assembled IS NOT NULL
              {merged_clause}
              {bot_clause}
              {repo_clause}
            GROUP BY p.repo_name, c.github_username
            HAVING COUNT(*) >= {args.min_prs}
            ORDER BY COUNT(*) DESC
            LIMIT {args.limit}
        """)

        logger.info("Found %d pairs to analyze", len(pairs))
        if not pairs:
            print("No pairs found.", file=sys.stderr)
            return

        results: list[dict[str, Any]] = []
        for i, pair in enumerate(pairs):
            repo = pair["repo_name"]
            chatbot = pair["chatbot"]
            pr_count = pair["pr_count"]

            result = await _analyze_pair(db, repo, chatbot, pr_count, args.include_unmerged)
            results.append(result)

            flag_count = len(result["flags"])
            if (i + 1) % 50 == 0 or flag_count > 0:
                flag_types = [f["type"] for f in result["flags"]]
                logger.info(
                    "  [%d/%d] %s | %s — %d comments, flags: %s",
                    i + 1, len(pairs), repo, chatbot,
                    result["total_comments"],
                    flag_types if flag_types else "none",
                )

        # Compile report
        flagged = [r for r in results if r["flags"]]
        unflagged = [r for r in results if not r["flags"]]

        report: dict[str, Any] = {
            "metadata": {
                "total_pairs_analyzed": len(results),
                "total_flagged": len(flagged),
                "total_unflagged": len(unflagged),
                "min_prs_threshold": args.min_prs,
                "include_unmerged": args.include_unmerged,
                "bot_filter": args.bot,
                "repo_filter": args.repo,
            },
            "flag_summary": _summarize_flags(results),
            "flagged_pairs": sorted(flagged, key=lambda r: (-len(r["flags"]), -r["pr_count"])),
            "all_pairs": sorted(results, key=lambda r: (-r["prefix_ratio"], r["unique_ratio"])),
        }

        if args.output:
            with open(args.output, "w") as f:
                json.dump(report, f, indent=2)
            logger.info("Report written to %s", args.output)
        else:
            print(json.dumps(report, indent=2))

        # Print summary table to stderr for quick viewing
        _print_summary(results, file=sys.stderr)

    finally:
        await db.close()


def _summarize_flags(results: list[dict[str, Any]]) -> dict[str, int]:
    """Count occurrences of each flag type across all results."""
    counts: dict[str, int] = defaultdict(int)
    for r in results:
        for f in r["flags"]:
            counts[f["type"]] += 1
    return dict(sorted(counts.items(), key=lambda x: -x[1]))


def _print_summary(results: list[dict[str, Any]], file: Any = sys.stderr) -> None:
    """Print a human-readable summary table."""
    print(f"\n{'='*140}", file=file)
    print("QUALITY REPORT SUMMARY", file=file)
    print(f"{'='*140}\n", file=file)

    print(
        f"{'Repo':<42} {'Bot':<28} {'PRs':>5} "
        f"{'Cmts':>5} {'Uniq':>5} {'Div%':>6} {'Pfx%':>6} {'Shrt%':>6} {'Flags':<30}",
        file=file,
    )
    print("-" * 140, file=file)

    for r in sorted(results, key=lambda x: (-x["prefix_ratio"], x["unique_ratio"])):
        flag_strs: list[str] = []
        for f in r["flags"]:
            match f["type"]:
                case "no_human_comments":
                    flag_strs.append("NO_CMTS")
                case "scripted":
                    flag_strs.append("SCRIPTED")
                case "low_diversity":
                    flag_strs.append("LOW_DIV")
                case "template_prefix":
                    flag_strs.append("TEMPLATE")
                case "mostly_short":
                    flag_strs.append("SHORT")
                case "user_template":
                    flag_strs.append(f"USR_TPL:{f['user'][:12]}")
                case "user_scripted":
                    flag_strs.append(f"USR_SCR:{f['user'][:12]}")

        print(
            f"{r['repo']:<42} {r['chatbot']:<28} "
            f"{r['pr_count']:>5} {r['total_comments']:>5} "
            f"{r.get('unique_comments', 0):>5} {r['unique_ratio']:>5.1%} "
            f"{r['prefix_ratio']:>5.1%} "
            f"{r['short_ratio']:>5.1%} {' '.join(flag_strs):<30}",
            file=file,
        )

    # Totals
    flag_counts = _summarize_flags(results)
    no_comments = sum(1 for r in results if r["total_comments"] == 0)
    print(f"\nTotal pairs: {len(results)}", file=file)
    for flag_type, count in flag_counts.items():
        print(f"  {flag_type}: {count}", file=file)
    print(f"  no_flags: {sum(1 for r in results if not r['flags'])}", file=file)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate quality report for template/scripted response detection"
    )
    parser.add_argument("--min-prs", type=int, default=20,
                        help="Minimum PRs per (repo, bot) pair (default: 20)")
    parser.add_argument("--limit", type=int, default=200,
                        help="Max pairs to analyze (default: 200)")
    parser.add_argument("--bot", type=str, default=None,
                        help="Filter to a specific bot username")
    parser.add_argument("--repo", type=str, default=None,
                        help="Filter to a specific repo")
    parser.add_argument("--include-unmerged", action="store_true",
                        help="Include unmerged PRs (default: merged only)")
    parser.add_argument("-o", "--output", type=str, default=None,
                        help="Output JSON file path (default: stdout)")
    args = parser.parse_args()
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
