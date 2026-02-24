# AGENTS.md — Code Review Benchmark Repo

These are guidelines for agents and contributors working in this repository.
They apply to the entire repo unless a more-specific AGENTS.md exists deeper
in the tree.

## Goal
Provide simple, reproducible scripts to fetch benchmark data, evaluate with an
LLM judge, and summarize/visualize results. Preserve existing data layout and
naming conventions so runs are comparable across judge models.

## Environment
- Python: >= 3.10
- Package manager: UV (preferred)
  - Install deps: `uv sync`
  - Run: `uv run python <script>.py` or the console scripts
- Key env vars (never commit secrets):
  - `OPENAI_API_KEY` (required for evaluation)
  - `OPENAI_BASE_URL` (optional; OpenAI-compatible endpoints supported)
  - `OPENAI_MODEL` (default: `openai/gpt-4o-mini`)
  - `GITHUB_TOKEN` (optional; increases API rate limits)

## Primary Scripts & Entrypoints
- `fetch_benchmark_data.py` / `fetch-data`
  - Fetches golden comments and tool PR review comments into `data/`.
  - Idempotent; safe to resume.
- `evaluate_with_llm.py` / `evaluate`
  - Uses an LLM judge to match tool comments to golden comments.
  - Saves per-PR checkpoints under `data/checkpoints/{model_name}/`.
  - Tune concurrency via `BATCH_SIZE` (respect vendor rate limits).
- `generate_benchmark_table.py` / `generate-table`
  - Aggregates evaluations into precision/recall/F1.
  - Writes `data/benchmark_results_{model}.json` and
    `data/benchmark_table_{model}.md`.
- `visualize_results.py`
  - Generates scatter plots `data/benchmark_chart_{model}.png` and optional
    multi-model comparison.
- `migrate_data.py`
  - One-off migrator to the model-scoped layout.

## Data Layout (Do Not Break)
- Golden comments: `data/golden_comments.json`
- Tool comments: `data/tool_comments/*.json`
- Judge-scoped outputs (directories must be model-specific):
  - Evaluations: `data/evaluations/{model_name}/*.json`
  - Checkpoints: `data/checkpoints/{model_name}/*.json`
- Summaries:
  - JSON: `data/benchmark_results_{model_name}.json`
  - Markdown: `data/benchmark_table_{model_name}.md`
- Visuals:
  - `data/benchmark_chart_{model_name}.png`
  - `data/benchmark_comparison.png` (when comparing models)

Model naming convention: derive `{model_name}` from `OPENAI_MODEL` by replacing
non-filename-safe characters with `-`/`_` (e.g., `openai/gpt-4o-mini` →
`openai_gpt-4o-mini`). Keep it consistent across new scripts.

## Implementation Guidelines
- Keep changes minimal and focused; avoid unrelated refactors.
- Prefer standard library + existing deps (`aiohttp`, `openai`, `matplotlib`,
  `requests`). Avoid introducing heavy new dependencies.
- Maintain idempotency and resumability:
  - Always read existing files if present and append/merge as needed.
  - Never delete or rewrite checkpoints automatically.
- Logging/prints: concise progress messages; never print secrets.
- File I/O: create parent dirs as needed; write atomically when practical
  (temp file + move) to avoid partial writes on interruption.
- Performance: batch external calls; respect API limits; make concurrency
  configurable.
- Prompts: If editing judge prompts in `evaluate_with_llm.py`, preserve the
  current schema of results so downstream scripts continue to work.

## Safety & Secrets
- Secrets live in environment variables or local `.env` files; `.env*` is
  ignored by `.gitignore`.
- Do not commit API keys, tokens, or personally identifiable data.
- Large artifacts: prefer keeping generated images and bulky intermediates out
  of version control unless explicitly required.

## Extending the Benchmark
- New judge models: store outputs under a new `data/evaluations/{model_name}/`
  and `data/checkpoints/{model_name}/` directory; reuse naming rules above.
- New metrics/columns: add non-breaking fields to the JSON; keep existing keys
  intact so historical runs parse correctly.
- New visualizations: write new files to `data/` and avoid overwriting
  established filenames unless the CLI/UI expects it.

## PR Expectations
- Describe the exact behavior change and data files created/modified.
- Include minimal reproduction steps (commands) and expected outputs.
- Do not rewrite repository history or reformat unrelated files.

## Quick Commands
- Install deps: `uv sync`
- Fetch data: `uv run python fetch_benchmark_data.py`
- Evaluate: `uv run python evaluate_with_llm.py`
- Table: `uv run python generate_benchmark_table.py [model_name]`
- Visualize: `uv run python visualize_results.py [options]`

## Do / Don’t
- Do: preserve directory structure and filenames; keep runs resumable; keep
  outputs model-scoped; be conservative with dependencies.
- Don’t: commit secrets; break JSON schemas; remove checkpoints; hardcode model
  names or vendor-specific endpoints.

## Code Style
- Follow the Google Python Style Guide (docstrings, naming, structure).
- Type hints for public functions and key internal helpers.
- Line length 120; 4-space indentation; prefer double quotes.
- Docstrings use Google style (handled via Ruff pydocstyle).

## Linting & Formatting (Ruff)
- Install dev tools: `uv sync --extra dev` (adds Ruff), or run once with
  `uvx ruff` if you prefer not to install locally.
- Lint: `ruff check .` (auto-fix: `ruff check . --fix`).
- Format: `ruff format .`.
- Import sorting is enforced by Ruff (isort rules); single-line imports are
  required, with special-casing for `typing`/`collections.abc`.

Ruff configuration lives in `pyproject.toml` and targets Python 3.13 with
line length 120 and the Google docstring convention.
