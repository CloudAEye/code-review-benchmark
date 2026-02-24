# AI Code Review Benchmark

Benchmark suite for evaluating AI code review tools against golden comments.

## Setup

1. Install dependencies:
```bash
uv sync
```

2. Create `.env` file with tokens:
```bash
GH_TOKEN=your_github_token
MARTIAN_API_KEY=your_api_key
MARTIAN_BASE_URL=https://api.withmartian.com/v1  # optional
MARTIAN_MODEL=openai/gpt-4o-mini  # optional
```

## Scripts

All scripts live in the `code_review_benchmark/` package. Run them from the repo root with `python -m`. All output files are stored in `results/`.

## Tests

Run the pytest suite (no network access required):

```bash
pytest
```

## Linting

The project uses Ruff for linting and formatting:

```bash
ruff check .
```

Apply auto-fixes as needed with `ruff check . --fix`.

### 0. Fork PRs

Fork benchmark PRs into the benchmark org:

```bash
uv run python -m code_review_benchmark.step0_fork_prs
```

### 1. Download PR Data

Aggregate PR reviews from benchmark repos with golden comments:

```bash
# Full run (incremental - skips already loaded)
uv run python -m code_review_benchmark.step1_download_prs --output results/benchmark_data.json

# Test mode: 1 PR per tool
uv run python -m code_review_benchmark.step1_download_prs --output results/benchmark_data.json --test

# Force refetch all reviews
uv run python -m code_review_benchmark.step1_download_prs --output results/benchmark_data.json --force

# Force refetch for a specific tool
uv run python -m code_review_benchmark.step1_download_prs --output results/benchmark_data.json --force --tool copilot
```

**Output:** `results/benchmark_data.json`

### 2. Extract Comments

Extract individual issues from reviews for matching:

```bash
# Extract for all tools
uv run python -m code_review_benchmark.step2_extract_comments

# Extract for specific tool
uv run python -m code_review_benchmark.step2_extract_comments --tool claude

# Limit extractions (for testing)
uv run python -m code_review_benchmark.step2_extract_comments --tool claude --limit 5
```

Line-specific comments become direct candidates. General comments are sent to LLM to extract individual issues.

**Output:** Updates `results/benchmark_data.json` with `candidates` field per review.

### 3. Judge Comments

Match candidates against golden comments, calculate precision/recall:

```bash
# Evaluate all tools
uv run python -m code_review_benchmark.step3_judge_comments

# Evaluate specific tool
uv run python -m code_review_benchmark.step3_judge_comments --tool claude

# Force re-evaluation
uv run python -m code_review_benchmark.step3_judge_comments --tool claude --force
```

**Output:** `results/evaluations.json` with TP/FP/FN, precision, recall per review.

### 4. Summary Table

Show review counts by tool and repo:

```bash
uv run python -m code_review_benchmark.summary_table
```

**Example output:**
```
Tool        cal_dot_com  discourse    grafana      keycloak     sentry       Total
----------------------------------------------------------------------------------
claude      10           10           10           10           10           50
coderabbit  10           10           10           10           10           50
...
```

### 5. Export by Tool

Export tool reviews with evaluation results:

```bash
# Export Claude (default)
uv run python -m code_review_benchmark.step4_export_by_tool

# Export specific tool
uv run python -m code_review_benchmark.step4_export_by_tool --tool greptile
uv run python -m code_review_benchmark.step4_export_by_tool --tool gemini
uv run python -m code_review_benchmark.step4_export_by_tool --tool bugbot
```

**Output:** `results/{tool}_reviews.xlsx`

Columns: pr_id, review_url, review_text, candidates, last_comment, golden_comments, judge_results, found_issues, total_issues

## Data Structure

### benchmark_data.json
```json
{
  "https://github.com/getsentry/sentry/pull/93824": {
    "pr_title": "...",
    "original_url": "...",
    "source_repo": "sentry",
    "golden_comments": [
      {"comment": "...", "severity": "High"}
    ],
    "golden_source_file": "sentry.json",
    "reviews": [
      {
        "tool": "claude",
        "repo_name": "sentry__sentry__claude__PR93824__20260127",
        "pr_url": "https://github.com/code-review-benchmark/...",
        "review_comments": [
          {"path": "...", "line": 42, "body": "...", "created_at": "..."}
        ]
      }
    ]
  }
}
```

### evaluations.json
```json
{
  "https://github.com/getsentry/sentry/pull/93824": {
    "claude": {
      "score": 0.6,
      "total_matched": 3,
      "total_golden": 5,
      "matches": [...],
      "false_negatives": [...]
    }
  }
}
```

## Golden Comments

Source files in `golden_comments/`:
- `sentry.json`
- `grafana.json`
- `keycloak.json`
- `discourse.json`
- `cal_dot_com.json`
