# PR Review Dataset

Benchmarking suite for AI code-review bots. Discovers PRs reviewed by chatbots, enriches them with GitHub data, runs LLM analysis, and serves an interactive dashboard.

## Structure

- **[`etl/`](etl/)** — Python pipeline: BigQuery discovery, GitHub enrichment, LLM analysis, Streamlit dashboard
- **[`api_service/`](api_service/)** — Rust API service: Axum server with embedded dashboard UI

See each subdirectory's README for setup and usage.
