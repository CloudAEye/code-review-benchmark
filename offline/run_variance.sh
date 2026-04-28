#!/usr/bin/env bash
# Run step3 judge 4 times with Sonnet on cal.com / cloudaeye to measure F1 variance.
# Uses opus candidates (already extracted) so only the judge varies between runs.
#
# Usage: bash run_variance.sh
# Prerequisites: offline/.env with ANTHROPIC_API_KEY set

set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# .env lives in the canonical offline dir (not the worktree)
MAIN_OFFLINE="C:/Projects/cloudaeye/code-review-benchmark/offline"
if [ -f "$MAIN_OFFLINE/.env" ]; then
    set -a; source "$MAIN_OFFLINE/.env"; set +a
elif [ -f ".env" ]; then
    set -a; source ".env"; set +a
fi

MODEL="anthropic/claude-sonnet-4-6"
REPO_FILTER="calcom/cal.com"
TOOL="cloudaeye"
OUTDIR="results/variance_calcom"

mkdir -p "$OUTDIR"

echo "=== Variance run: $TOOL on $REPO_FILTER with $MODEL ==="
echo ""

for RUN in 1 2 3 4; do
    EVAL_FILE="$OUTDIR/run_${RUN}.json"
    echo "--- Run $RUN / 4 ---"
    MARTIAN_API_KEY="$ANTHROPIC_API_KEY" \
    MARTIAN_BASE_URL="https://api.anthropic.com/v1" \
    MARTIAN_MODEL="$MODEL" \
    uv run python -m code_review_benchmark.step3_judge_comments \
        --tool "$TOOL" \
        --repo "$REPO_FILTER" \
        --force \
        --evaluations-file "$EVAL_FILE"
    echo ""
done

echo "=== Variance summary ==="
uv run python - <<'PYEOF'
import json, math, os, glob

outdir = "results/variance_calcom"
runs = sorted(glob.glob(f"{outdir}/run_*.json"))

f1_scores = []
print(f"{'Run':<6} {'Precision':>10} {'Recall':>10} {'F1':>10} {'TP':>5} {'FP':>5} {'FN':>5}")
print("-" * 52)

for run_file in runs:
    run_num = os.path.basename(run_file).replace("run_", "").replace(".json", "")
    with open(run_file) as f:
        data = json.load(f)

    tp = fp = fn = 0
    for golden_url, tools in data.items():
        result = tools.get("cloudaeye", {})
        if result.get("skipped"):
            continue
        tp += result.get("tp", 0)
        fp += result.get("fp", 0)
        fn += result.get("fn", 0)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    f1_scores.append(f1)
    print(f"{run_num:<6} {precision:>10.1%} {recall:>10.1%} {f1:>10.1%} {tp:>5} {fp:>5} {fn:>5}")

if f1_scores:
    mean = sum(f1_scores) / len(f1_scores)
    variance = sum((x - mean) ** 2 for x in f1_scores) / len(f1_scores)
    std_dev = math.sqrt(variance)
    print("-" * 52)
    print(f"{'Mean':<6} {'':>10} {'':>10} {mean:>10.1%}")
    print(f"{'Std'::<6} {'':>10} {'':>10} {std_dev:>10.1%}")
    print(f"{'Range':<6} {'':>10} {'':>10} {min(f1_scores):>5.1%} – {max(f1_scores):.1%}")
PYEOF
