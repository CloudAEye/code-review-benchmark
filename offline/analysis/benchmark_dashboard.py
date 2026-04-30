#!/usr/bin/env python3
"""
Generate a single interactive HTML dashboard for code review benchmark results.

This script creates one dashboard HTML file with all models' data embedded:
- Predefined filters at the top ("Best for Python PRs", "Best for Large PRs", etc.)
- Left sidebar with dimension filters (Language, PR Size, Domain, etc.)
- Scatter plot showing Precision vs Recall for each tool
- Data table below with Precision, Recall, and F1 scores
- Model selector to switch between different judge models dynamically
"""

import base64
import json
from pathlib import Path

# Tools excluded from the dashboard (superseded versions, incomplete runs, etc.)
# Anything matching these exact slugs or the "mra-" prefix is hidden.
_HIDDEN_TOOLS: frozenset[str] = frozenset({
    "qodo",
    "greptile",
    "linearb",
    "bito",
    "sentry",
    "vercel",
    "kodus",
    "cubic-dev",
    "cubic-v3",
    "greptile-v4",
    "mergemonkey",
    "qodo-v22",
    "qodo-v2-2",
    "qodo-extended-summary",
    "entelligence",
    "mesa",
    "codeant",
})
_HIDDEN_PREFIXES: tuple[str, ...] = ("mra-",)


def _is_hidden(tool: str) -> bool:
    return tool in _HIDDEN_TOOLS or any(tool.startswith(p) for p in _HIDDEN_PREFIXES)


# Tool display configuration
TOOL_DISPLAY_NAMES = {
    "graphite": "Graphite",
    "qodo": "Qodo",
    "gemini": "Gemini",
    "claude": "Claude Code",
    "augment": "Augment",
    "bugbot": "Cursor Bugbot",
    "coderabbit": "CodeRabbit",
    "propel": "Propel",
    "copilot": "GitHub Copilot",
    "baz": "Baz",
    "greptile": "Greptile",
    "kg": "KG",
    "entelligence": "Entelligence",
    "cubic-dev": "Cubic",
    "sourcery": "Sourcery",
    "mesa": "Mesa",
    "codeant": "CodeAnt",
    "codeant-v2": "CodeAnt v2",
    "claude-code": "Claude Code (CLI)",
    "devin": "Devin",
    "kodus-v2": "Kodus",
    "greptile-v4": "Greptile v4",
    "qodo-v2": "Qodo v2",
    "qodo-extended-v2": "Qodo Extended",
    "macroscope": "Macroscope",
    "cubic-v2": "Cubic v2",
    "cloudaeye": "CloudAEye",
}

TOOL_COLORS = {
    "graphite": "#6366f1",
    "qodo": "#8b5cf6",
    "gemini": "#06b6d4",
    "claude": "#f59e0b",
    "augment": "#10b981",
    "bugbot": "#3b82f6",
    "coderabbit": "#ec4899",
    "propel": "#14b8a6",
    "propel-v2": "#0d9488",
    "copilot": "#6b7280",
    "baz": "#f97316",
    "greptile": "#22c55e",
    "kg": "#a855f7",
    "entelligence": "#0ea5e9",
    "cubic-dev": "#d946ef",
    "sourcery": "#84cc16",
    "mesa": "#f43f5e",
    "codeant": "#e11d48",
    "codeant-v2": "#fb7185",
    "claude-code": "#d97706",
    "devin": "#7c3aed",
    "kodus-v2": "#059669",
    "greptile-v4": "#16a34a",
    "qodo-v2": "#7c3aed",
    "qodo-extended-v2": "#6d28d9",
    "macroscope": "#0891b2",
    "cubic-v2": "#c026d3",
    "cloudaeye": "#0052cc",
}


def load_tool_logos(logos_dir: Path) -> dict[str, str]:
    """Load tool logo images from logos/ dir and return as base64 data URIs.

    Expected filenames: {tool_slug}.png / .jpg / .svg / .webp
    e.g. logos/cloudaeye.png
    """
    logos: dict[str, str] = {}
    if not logos_dir.exists():
        return logos
    mime = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".svg": "image/svg+xml", ".webp": "image/webp", ".ico": "image/x-icon"}
    for f in logos_dir.iterdir():
        if f.suffix.lower() in mime:
            data = base64.b64encode(f.read_bytes()).decode()
            logos[f.stem] = f"data:{mime[f.suffix.lower()]};base64,{data}"
    return logos


def load_model_data(results_dir: Path, model_name: str, central_labels: dict) -> dict:
    """Load evaluations for a specific model, using central labels."""
    model_dir = results_dir / model_name
    evaluations_path = model_dir / "evaluations.json"

    if not evaluations_path.exists():
        raise FileNotFoundError(f"Evaluations not found: {evaluations_path}")

    with open(evaluations_path) as f:
        evaluations = json.load(f)

    return evaluations


def load_central_labels(results_dir: Path) -> dict:
    """Load labels from central file (shared across all models)."""
    labels_path = results_dir / "pr_labels.json"
    if labels_path.exists():
        with open(labels_path) as f:
            return json.load(f)
    return {}


def get_available_models(results_dir: Path) -> list[str]:
    """Get list of available model directories."""
    models = []
    for item in results_dir.iterdir():
        if item.is_dir() and (item / "evaluations.json").exists():
            models.append(item.name)
    return sorted(models)


def prepare_model_data(evaluations: dict, labels: dict) -> dict:
    """Prepare data structure for a single model."""
    prs = []
    all_tools = set()
    languages = set()
    pr_sizes = set()
    domains = set()
    change_types = set()
    complexities = set()
    difficulties = set()
    risk_levels = set()
    context_levels = set()
    concerns = set()

    for pr_url, pr_evals in evaluations.items():
        pr_labels = labels.get(pr_url, {})
        derived = pr_labels.get("derived", {})
        llm_labels = pr_labels.get("llm_pr_labels", {})

        language = derived.get("language", "Unknown")
        pr_size = llm_labels.get("pr_size_category", "unknown")
        domain = llm_labels.get("domain", "unknown")
        change_type = llm_labels.get("change_type", "unknown")
        complexity = llm_labels.get("code_complexity", "unknown")
        difficulty = llm_labels.get("review_difficulty", "unknown")
        risk = llm_labels.get("risk_level", "unknown")
        context = llm_labels.get("requires_context", "unknown")
        concern = llm_labels.get("primary_concern", "unknown")
        summary = llm_labels.get("summary", "")

        languages.add(language)
        pr_sizes.add(pr_size)
        domains.add(domain)
        change_types.add(change_type)
        complexities.add(complexity)
        difficulties.add(difficulty)
        risk_levels.add(risk)
        context_levels.add(context)
        concerns.add(concern)

        tool_metrics = {}
        for tool_name, tool_eval in pr_evals.items():
            if _is_hidden(tool_name):
                continue
            all_tools.add(tool_name)
            tool_metrics[tool_name] = {
                "tp": tool_eval.get("tp", 0),
                "fp": tool_eval.get("fp", 0),
                "fn": tool_eval.get("fn", 0),
            }

        prs.append({
            "url": pr_url,
            "language": language,
            "pr_size": pr_size,
            "domain": domain,
            "change_type": change_type,
            "complexity": complexity,
            "difficulty": difficulty,
            "risk": risk,
            "context": context,
            "concern": concern,
            "summary": summary,
            "tool_metrics": tool_metrics,
        })

    tool_metrics = calculate_aggregate_metrics(prs, list(all_tools))

    return {
        "prs": prs,
        "tools": sorted(all_tools),
        "dimensions": {
            "language": sorted(languages),
            "pr_size": ["small", "medium", "large"],
            "domain": sorted(domains),
            "change_type": sorted(change_types - {"unknown"}),
            "complexity": ["simple", "moderate", "complex"],
            "difficulty": ["obvious", "moderate", "subtle", "very_subtle"],
            "risk": ["low", "medium", "high", "critical"],
            "context": ["local", "file", "cross_file", "system"],
            "concern": sorted(concerns - {"unknown"}),
        },
        "overall_metrics": tool_metrics,
    }


def calculate_aggregate_metrics(prs: list, tools: list) -> dict:
    """Calculate aggregate precision/recall/F1 for each tool across PRs."""
    metrics = {}

    for tool in tools:
        total_tp = 0
        total_fp = 0
        total_fn = 0

        for pr in prs:
            if tool in pr["tool_metrics"]:
                tm = pr["tool_metrics"][tool]
                total_tp += tm["tp"]
                total_fp += tm["fp"]
                total_fn += tm["fn"]

        precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0
        recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        metrics[tool] = {
            "precision": round(precision * 100, 1),
            "recall": round(recall * 100, 1),
            "f1": round(f1 * 100, 1),
            "tp": total_tp,
            "fp": total_fp,
            "fn": total_fn,
            "num_prs": len([p for p in prs if tool in p["tool_metrics"]]),
        }

    return metrics


def load_all_models(results_dir: Path) -> dict:
    """Load data from all available models."""
    models = get_available_models(results_dir)
    all_data = {}

    # Load central labels (shared across all models)
    central_labels = load_central_labels(results_dir)
    if central_labels:
        print(f"  Loaded {len(central_labels)} PR labels from central file")
    else:
        print("  No central labels found (run step5_label_prs.py first)")

    for model in models:
        try:
            evaluations = load_model_data(results_dir, model, central_labels)
            all_data[model] = prepare_model_data(evaluations, central_labels)
            print(f"  Loaded: {model}")
        except Exception as e:
            print(f"  Error loading {model}: {e}")

    return all_data


def get_model_display_name(model: str) -> str:
    """Convert model ID to display name."""
    return (model
            .replace("_", " / ")
            .replace("anthropic / ", "Anthropic ")
            .replace("openai / ", "OpenAI "))


def format_dimension_label(dim: str, value: str) -> str:
    """Format a dimension value as a human-readable label."""
    # Special cases for better labels
    label_overrides = {
        ("pr_size", "small"): "Small PRs",
        ("pr_size", "medium"): "Medium PRs",
        ("pr_size", "large"): "Large PRs",
        ("complexity", "simple"): "Simple Code",
        ("complexity", "moderate"): "Moderate Code",
        ("complexity", "complex"): "Complex Code",
        ("difficulty", "obvious"): "Obvious Bugs",
        ("difficulty", "moderate"): "Moderate Bugs",
        ("difficulty", "subtle"): "Subtle Bugs",
        ("difficulty", "very_subtle"): "Very Subtle Bugs",
        ("risk", "low"): "Low Risk",
        ("risk", "medium"): "Medium Risk",
        ("risk", "high"): "High Risk",
        ("risk", "critical"): "Critical Risk",
        ("context", "local"): "Local Context",
        ("context", "file"): "File Context",
        ("context", "cross_file"): "Cross-File",
        ("context", "system"): "System-Wide",
        ("change_type", "bug_fix"): "Bug Fixes",
        ("change_type", "feature"): "Features",
        ("change_type", "refactoring"): "Refactoring",
        ("change_type", "security_patch"): "Security Patches",
        ("change_type", "performance"): "Performance Optimization",
        ("change_type", "migration"): "Migration",
        ("change_type", "test_update"): "Test Updates",
    }

    if (dim, value) in label_overrides:
        return label_overrides[(dim, value)]

    # Default: title case with underscores replaced
    return value.replace("_", " ").title()


def generate_filter_description(filters: dict) -> str:
    """Generate a human-readable description for a filter combination."""
    descriptions = {
        # Language
        "language": {
            "Python": "Python codebases with dynamic typing.",
            "Java": "Java codebases with OOP patterns.",
            "Go": "Go codebases with concurrency patterns.",
            "TypeScript": "TypeScript codebases with frontend patterns.",
            "Ruby": "Ruby codebases with Rails patterns.",
        },
        # PR Size
        "pr_size": {
            "small": "Small PRs with 1-2 files, easier to review thoroughly",
            "medium": "Medium PRs with 3-5 files, typical feature development",
            "large": "Large PRs with 6+ files, complex changes requiring careful review",
        },
        # Domain
        "domain": {
            "authentication": "Auth and access control.",
            "data_processing": "Data transformation and ETL.",
            "API": "API endpoints and request handling.",
            "UI": "User interface and frontend.",
            "concurrency": "Threading and async operations.",
            "database": "Database queries and persistence.",
            "caching": "Cache and memoization.",
            "configuration": "Config and environment.",
            "error_handling": "Exception handling.",
            "networking": "Network requests.",
            "scheduling": "Task scheduling.",
            "file_io": "File operations.",
            "serialization": "Data parsing.",
            "logging": "Logging and monitoring.",
            "testing": "Test code.",
            "memory_management": "Memory handling.",
            "other": "General code.",
        },
        # Complexity
        "complexity": {
            "simple": "Straightforward logic.",
            "moderate": "Some abstraction.",
            "complex": "Deep logic and dependencies.",
        },
        # Difficulty
        "difficulty": {
            "obvious": "Easy to spot issues.",
            "moderate": "Requires careful reading.",
            "subtle": "Non-obvious, needs domain knowledge.",
            "very_subtle": "Very hard to catch edge cases.",
        },
        # Risk
        "risk": {
            "low": "Low impact if bugs ship.",
            "medium": "Moderate user impact.",
            "high": "Significant impact, potential data loss.",
            "critical": "Critical security or data corruption risk.",
        },
        # Context
        "context": {
            "local": "Issues visible in local context.",
            "file": "Requires full file understanding.",
            "cross_file": "Spans multiple files.",
            "system": "Requires system-wide knowledge.",
        },
        # Concern
        "concern": {
            "correctness": "Logical correctness and expected behavior",
            "security": "Security vulnerabilities and attack vectors",
            "performance": "Performance bottlenecks and efficiency",
            "maintainability": "Code quality and long-term maintenance",
            "reliability": "Error handling and system stability",
        },
        # Change Type
        "change_type": {
            "bug_fix": "Bug fixes and issue resolution",
            "feature": "New feature implementation",
            "refactoring": "Code restructuring without behavior change",
            "performance": "Performance optimization changes",
            "security_patch": "Security-related fixes and hardening",
        },
    }

    parts = []
    for dim, values in filters.items():
        if dim in descriptions:
            for val in values:
                if val in descriptions[dim]:
                    parts.append(descriptions[dim][val])
                    break  # Only use first value's description per dimension

    if len(parts) >= 2:
        # For combined filters, create a concise summary
        return f"{parts[0]} {parts[1]}"
    elif parts:
        return parts[0]
    return ""


def generate_predefined_filters(all_models_data: dict) -> list[dict]:
    """Dynamically generate predefined filter configurations based on actual data."""
    filters = []

    # Collect all unique dimension values across all models
    all_dimensions = {}
    for model_data in all_models_data.values():
        dims = model_data.get("dimensions", {})
        for dim, values in dims.items():
            if dim not in all_dimensions:
                all_dimensions[dim] = set()
            all_dimensions[dim].update(v for v in values if v and v != "unknown")

    # Define which dimensions to create single-value filters for
    single_filter_dims = ["language", "pr_size", "domain", "complexity", "difficulty",
                         "risk", "context", "concern", "change_type"]

    # Generate single-dimension filters
    for dim in single_filter_dims:
        if dim not in all_dimensions:
            continue
        for value in sorted(all_dimensions[dim]):
            label = format_dimension_label(dim, value)
            filters.append({
                "id": f"{dim}_{value}".replace(" ", "_").lower(),
                "label": f"Best for {label}",
                "filters": {dim: [value]}
            })

    # Generate combined filters (language + size) dynamically
    if "language" in all_dimensions and "pr_size" in all_dimensions:
        for lang in sorted(all_dimensions["language"]):
            for size in ["small", "medium", "large"]:
                if size in all_dimensions["pr_size"]:
                    size_label = format_dimension_label("pr_size", size).replace(" PRs", "")
                    filters.append({
                        "id": f"{lang.lower()}_{size}",
                        "label": f"Best for {size_label} {lang} PRs",
                        "filters": {"language": [lang], "pr_size": [size]}
                    })

    # Combined: complexity + difficulty
    if "complexity" in all_dimensions and "difficulty" in all_dimensions:
        filters.append({
            "id": "complex_subtle",
            "label": "Complex & Subtle",
            "filters": {"complexity": ["complex"], "difficulty": ["subtle", "very_subtle"]}
        })
        filters.append({
            "id": "simple_obvious",
            "label": "Simple & Obvious",
            "filters": {"complexity": ["simple"], "difficulty": ["obvious"]}
        })

    # Combined: high risk + auth domain
    if "risk" in all_dimensions and "domain" in all_dimensions:
        if "authentication" in all_dimensions["domain"]:
            filters.append({
                "id": "high_risk_auth",
                "label": "High Risk Auth",
                "filters": {"risk": ["high", "critical"], "domain": ["authentication"]}
            })

    # Combined: security concern + high risk
    if "concern" in all_dimensions and "risk" in all_dimensions:
        if "security" in all_dimensions["concern"]:
            filters.append({
                "id": "security_critical",
                "label": "Security Critical",
                "filters": {"concern": ["security"], "risk": ["high", "critical"]}
            })

    # Sort-based filters (always include these)
    filters.extend([
        {"id": "high_precision", "label": "Highest Precision", "filters": {}, "sort": "precision",
         "description": "Tools ranked by precision - fewer false positives, more reliable findings"},
        {"id": "high_recall", "label": "Highest Recall", "filters": {}, "sort": "recall",
         "description": "Tools ranked by recall - catches more issues, may have more noise"},
        {"id": "high_f1", "label": "Highest F1", "filters": {}, "sort": "f1",
         "description": "Tools ranked by F1 score - balanced precision and recall"},
    ])

    return filters


def calculate_filtered_metrics(model_data: dict, filters: dict) -> tuple[dict, int]:
    """Calculate aggregated metrics for a model given specific filters.

    Returns (metrics_dict, num_prs) tuple.
    """
    prs = model_data["prs"]
    tools = model_data["tools"]

    # Apply filters
    filtered_prs = []
    for pr in prs:
        match = True
        for dim, values in filters.items():
            if values and pr.get(dim) not in values:
                match = False
                break
        if match:
            filtered_prs.append(pr)

    if not filtered_prs:
        return {}, 0

    # Calculate metrics
    metrics = {}
    for tool in tools:
        tp = fp = fn = 0
        for pr in filtered_prs:
            if tool in pr["tool_metrics"]:
                tm = pr["tool_metrics"][tool]
                tp += tm["tp"]
                fp += tm["fp"]
                fn += tm["fn"]

        precision = tp / (tp + fp) if (tp + fp) > 0 else 0
        recall = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        metrics[tool] = {"precision": precision, "recall": recall, "f1": f1}

    return metrics, len(filtered_prs)


MIN_PRS_FOR_FILTER = 5


def find_best_model_for_filter(all_models_data: dict, filter_config: dict) -> tuple[str | None, int]:
    """Find which model shows the best overall tool performance for a given filter.

    Returns (best_model, num_prs) tuple.
    num_prs is the PR count for the best model.
    """
    filters = filter_config.get("filters", {})
    sort_by = filter_config.get("sort", "f1")

    best_model = None
    best_score = -1
    best_model_prs = 0

    for model_name, model_data in all_models_data.items():
        metrics, num_prs = calculate_filtered_metrics(model_data, filters)
        if not metrics or num_prs < MIN_PRS_FOR_FILTER:
            continue

        # Check if there's actual data (non-zero scores)
        scores = [m[sort_by] for m in metrics.values()]
        if scores and max(scores) > 0:
            top_score = max(scores)
            if top_score > best_score:
                best_score = top_score
                best_model = model_name
                best_model_prs = num_prs

    return best_model, best_model_prs


def get_best_tool_for_filter(model_data: dict, filter_config: dict) -> tuple[str | None, float]:
    """Find which tool performs best for a given filter in a specific model.

    Returns (best_tool, best_score) tuple.
    """
    filters = filter_config.get("filters", {})
    sort_by = filter_config.get("sort", "f1")

    metrics, num_prs = calculate_filtered_metrics(model_data, filters)
    if not metrics:
        return None, 0

    best_tool = None
    best_score = -1

    for tool, m in metrics.items():
        score = m[sort_by]
        if score > best_score:
            best_score = score
            best_tool = tool

    return best_tool, best_score


def enrich_predefined_filters(predefined_filters: list, all_models_data: dict) -> list:
    """Add best_model, best_tool, and description to each predefined filter."""
    enriched = []
    for f in predefined_filters:
        best_model, num_prs = find_best_model_for_filter(all_models_data, f)
        # Only include filters where the best model has at least MIN_PRS_FOR_FILTER PRs
        if best_model and num_prs >= MIN_PRS_FOR_FILTER:
            # Also find the best tool for this filter
            best_tool, best_score = get_best_tool_for_filter(
                all_models_data[best_model], f
            )
            # Generate description for this filter (preserve existing if present)
            description = f.get("description") or generate_filter_description(f.get("filters", {}))
            enriched.append({
                **f,
                "description": description,
                "best_model": best_model,
                "best_tool": best_tool,
                "best_score": round(best_score * 100, 1)
            })

    # Sort filters to maximize tool diversity at the top
    # Also finds additional filters for tools that don't have a "best" filter yet
    enriched = sort_filters_for_tool_diversity(enriched, all_models_data)

    return enriched


def find_filters_for_missing_tools(all_models_data: dict, existing_filters: list, all_tools: set) -> list:
    """Find filter combinations where missing tools perform well.

    For tools that don't win any existing filter, search for dimension
    combinations where they perform best or are tied for best.
    Tries F1 first, then precision, then recall.
    """
    # Find which tools already have a winning filter
    covered_tools = {f.get("best_tool") for f in existing_filters}
    missing_tools = all_tools - covered_tools

    if not missing_tools:
        return []

    new_filters = []

    # Collect all dimension values from all models
    all_dims = {}
    for model_data in all_models_data.values():
        for dim, values in model_data.get("dimensions", {}).items():
            if dim not in all_dims:
                all_dims[dim] = set()
            all_dims[dim].update(v for v in values if v and v != "unknown")

    # For each missing tool, find filters where it is actually #1 (or tied for #1)
    # Try F1, then precision, then recall
    for target_tool in missing_tools:
        best_filter = None

        for metric_name in ["f1", "precision", "recall"]:
            if best_filter:
                break  # Found a filter, stop trying other metrics

            best_target_score = -1

            # Try single dimensions
            for dim, values in all_dims.items():
                for val in values:
                    filter_dict = {dim: [val]}

                    for model_name, model_data in all_models_data.items():
                        metrics, num_prs = calculate_filtered_metrics(model_data, filter_dict)
                        if num_prs < MIN_PRS_FOR_FILTER:
                            continue

                        if target_tool not in metrics:
                            continue

                        target_score = metrics[target_tool][metric_name]
                        if target_score == 0:
                            continue

                        top_score = max(metrics[t][metric_name] for t in metrics)
                        if top_score == 0:
                            continue

                        # Only consider if target_tool is #1 or tied for #1
                        if target_score >= top_score and target_score > best_target_score:
                            best_target_score = target_score
                            label = format_dimension_label(dim, val)
                            metric_label = {"f1": "", "precision": " (Precision)", "recall": " (Recall)"}[metric_name]
                            filter_dict = {dim: [val]}
                            best_filter = {
                                "id": f"tool_{target_tool}_{dim}_{val}".replace(" ", "_").lower(),
                                "label": f"Best for {label}{metric_label}",
                                "filters": filter_dict,
                                "description": generate_filter_description(filter_dict),
                                "best_model": model_name,
                                "best_tool": target_tool,
                                "best_score": round(target_score * 100, 1),
                                "sort": metric_name if metric_name != "f1" else None
                            }

            # Also try two-dimension combinations
            dims_list = list(all_dims.keys())
            for i, dim1 in enumerate(dims_list):
                for dim2 in dims_list[i+1:]:
                    for val1 in all_dims[dim1]:
                        for val2 in all_dims[dim2]:
                            filter_dict = {dim1: [val1], dim2: [val2]}

                            for model_name, model_data in all_models_data.items():
                                metrics, num_prs = calculate_filtered_metrics(model_data, filter_dict)
                                if num_prs < MIN_PRS_FOR_FILTER:
                                    continue

                                if target_tool not in metrics:
                                    continue

                                target_score = metrics[target_tool][metric_name]
                                if target_score == 0:
                                    continue

                                top_score = max(metrics[t][metric_name] for t in metrics)
                                if top_score == 0:
                                    continue

                                # Only consider if target_tool is #1 or tied for #1
                                if target_score >= top_score and target_score > best_target_score:
                                    best_target_score = target_score
                                    label1 = format_dimension_label(dim1, val1)
                                    label2 = format_dimension_label(dim2, val2)
                                    metric_label = {"f1": "", "precision": " (Precision)", "recall": " (Recall)"}[metric_name]
                                    filter_dict_2d = {dim1: [val1], dim2: [val2]}
                                    best_filter = {
                                        "id": f"tool_{target_tool}_{dim1}_{val1}_{dim2}_{val2}".replace(" ", "_").lower(),
                                        "label": f"{label1} + {label2}{metric_label}",
                                        "filters": filter_dict_2d,
                                        "description": generate_filter_description(filter_dict_2d),
                                        "best_model": model_name,
                                        "best_tool": target_tool,
                                        "best_score": round(target_score * 100, 1),
                                        "sort": metric_name if metric_name != "f1" else None
                                    }

        # Add filter if we found one where tool is #1
        if best_filter:
            # Remove None sort key
            if best_filter.get("sort") is None:
                best_filter.pop("sort", None)
            new_filters.append(best_filter)

    return new_filters


def sort_filters_for_tool_diversity(filters: list, all_models_data: dict = None) -> list:
    """Sort filters so different tools appear as 'best' first.

    Strategy: Iterate through filters, picking ones that feature tools
    not yet seen, until all tools are represented. Then append the rest.
    """
    if not filters:
        return filters

    # If we have model data, try to find filters for missing tools
    if all_models_data:
        all_tools = set()
        for model_data in all_models_data.values():
            all_tools.update(model_data.get("tools", []))

        extra_filters = find_filters_for_missing_tools(all_models_data, filters, all_tools)
        filters = filters + extra_filters

    # Group filters by their best_tool
    by_tool = {}
    for f in filters:
        tool = f.get("best_tool")
        if tool not in by_tool:
            by_tool[tool] = []
        by_tool[tool].append(f)

    # Sort each tool's filters by score (highest first)
    for tool in by_tool:
        by_tool[tool].sort(key=lambda x: x.get("best_score", 0), reverse=True)

    result = []
    seen_tools = set()

    # First pass: pick the best filter for each tool (one per tool)
    # Sort tools by their best filter's score to put strongest results first
    tools_by_best_score = sorted(
        by_tool.keys(),
        key=lambda t: by_tool[t][0].get("best_score", 0) if by_tool[t] else 0,
        reverse=True
    )

    for tool in tools_by_best_score:
        if by_tool[tool]:
            result.append(by_tool[tool].pop(0))
            seen_tools.add(tool)

    # Second pass: add remaining filters, still prioritizing tool diversity
    remaining = []
    for tool in by_tool:
        remaining.extend(by_tool[tool])

    # Sort remaining by score
    remaining.sort(key=lambda x: x.get("best_score", 0), reverse=True)
    result.extend(remaining)

    return result


def generate_html(all_models_data: dict, default_model: str, tool_logos: dict | None = None) -> str:
    """Generate the complete HTML dashboard with all models' data."""
    if tool_logos is None:
        tool_logos = {}
    # Generate filters dynamically based on actual data
    predefined_filters = generate_predefined_filters(all_models_data)
    # Enrich filters with best model and filter out those with <5 PRs
    predefined_filters = enrich_predefined_filters(predefined_filters, all_models_data)

    # Get dimensions from the default model
    default_data = all_models_data[default_model]
    dimensions = default_data["dimensions"]

    # Generate model options
    model_options = []
    for model in sorted(all_models_data.keys()):
        display = get_model_display_name(model)
        selected = "selected" if model == default_model else ""
        model_options.append(f'<option value="{model}" {selected}>{display}</option>')
    model_options_html = "\n                    ".join(model_options)

    # Generate filter buttons
    filter_buttons = []
    for f in predefined_filters:
        filter_buttons.append(
            (
                f["id"],
                f'<div class="predefined-filter" data-filter-id="{f["id"]}" onclick="applyPredefinedFilter(\'{f["id"]}\')">'
                f'<span class="preset-icon">&#9813;</span>{f["label"]} <span class="arrow">↗</span>'
                f'</div>',
            )
        )
    quick_preset_ids = [
        "high_precision",
        "tool_kodus-v2_domain_concurrency",
        "tool_kg_complexity_complex",
        "tool_propel-v2_risk_high_context_file",
    ]
    visible_filter_buttons = []
    overflow_filter_buttons = []
    for filter_id, button_html in filter_buttons:
        if filter_id in quick_preset_ids:
            visible_filter_buttons.append((quick_preset_ids.index(filter_id), button_html))
        else:
            overflow_filter_buttons.append(button_html)
    visible_filter_buttons_html = "\n            ".join(
        button_html for _, button_html in sorted(visible_filter_buttons)
    )
    overflow_filter_buttons_html = "\n            ".join(overflow_filter_buttons)

    # Generate language checkboxes
    lang_checkboxes = []
    for lang in dimensions["language"]:
        lang_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-language-{lang}" onchange="toggleFilter(\'language\', \'{lang}\')">'
            f'{lang}'
            f'</label>'
        )
    lang_checkboxes_html = "\n                    ".join(lang_checkboxes)

    # Generate PR size checkboxes
    size_checkboxes = []
    for size in ["small", "medium", "large"]:
        display = size.title()
        size_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-pr_size-{size}" onchange="toggleFilter(\'pr_size\', \'{size}\')">'
            f'{display}'
            f'</label>'
        )
    size_checkboxes_html = "\n                    ".join(size_checkboxes)

    # Generate domain checkboxes (first 5 visible, rest hidden)
    domains = dimensions["domain"]
    domain_checkboxes = []
    for dom in domains[:5]:
        display = dom.replace("_", " ").title()
        domain_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-domain-{dom}" onchange="toggleFilter(\'domain\', \'{dom}\')">'
            f'{display}'
            f'</label>'
        )
    domain_checkboxes_html = "\n                    ".join(domain_checkboxes)

    more_domain_checkboxes = []
    for dom in domains[5:]:
        display = dom.replace("_", " ").title()
        more_domain_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-domain-{dom}" onchange="toggleFilter(\'domain\', \'{dom}\')">'
            f'{display}'
            f'</label>'
        )
    more_domain_checkboxes_html = "\n                    ".join(more_domain_checkboxes)

    # Generate complexity checkboxes
    complexity_checkboxes = []
    for comp in ["simple", "moderate", "complex"]:
        display = comp.title()
        complexity_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-complexity-{comp}" onchange="toggleFilter(\'complexity\', \'{comp}\')">'
            f'{display}'
            f'</label>'
        )
    complexity_checkboxes_html = "\n                    ".join(complexity_checkboxes)

    # Generate difficulty checkboxes
    difficulty_checkboxes = []
    for diff, display in [("obvious", "Obvious"), ("moderate", "Moderate"), ("subtle", "Subtle"), ("very_subtle", "Very Subtle")]:
        difficulty_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-difficulty-{diff}" onchange="toggleFilter(\'difficulty\', \'{diff}\')">'
            f'{display}'
            f'</label>'
        )
    difficulty_checkboxes_html = "\n                    ".join(difficulty_checkboxes)

    # Generate risk checkboxes
    risk_checkboxes = []
    for risk in ["low", "medium", "high", "critical"]:
        display = risk.title()
        risk_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-risk-{risk}" onchange="toggleFilter(\'risk\', \'{risk}\')">'
            f'{display}'
            f'</label>'
        )
    risk_checkboxes_html = "\n                    ".join(risk_checkboxes)

    # Generate context checkboxes
    context_checkboxes = []
    for ctx, display in [("local", "Local"), ("file", "File"), ("cross_file", "Cross-File"), ("system", "System")]:
        context_checkboxes.append(
            f'<label class="filter-option">'
            f'<input type="checkbox" id="filter-context-{ctx}" onchange="toggleFilter(\'context\', \'{ctx}\')">'
            f'{display}'
            f'</label>'
        )
    context_checkboxes_html = "\n                    ".join(context_checkboxes)

    # Generate concern checkboxes
    concern_checkboxes = []
    concerns_list = dimensions.get("concern", ["correctness", "security", "performance", "maintainability", "reliability"])
    for concern in concerns_list:
        if concern != "unknown":
            display = concern.title()
            concern_checkboxes.append(
                f'<label class="filter-option">'
                f'<input type="checkbox" id="filter-concern-{concern}" onchange="toggleFilter(\'concern\', \'{concern}\')">'
                f'{display}'
                f'</label>'
            )
    concern_checkboxes_html = "\n                    ".join(concern_checkboxes)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Code Review Benchmark Dashboard</title>
    <script src="https://cdn.plot.ly/plotly-2.27.0.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #fafafa;
            color: #1a1a1a;
        }}
        .predefined-filters {{
            background: #fff;
            border-bottom: 1px solid #e5e5e5;
            padding: 16px 56px;
        }}
        .predefined-filters-row {{
            display: flex;
            align-items: center;
            gap: 12px;
            min-height: 48px;
        }}
        .predefined-label {{
            flex: 0 0 auto;
            color: #a3a3a3;
            font-size: 14px;
            font-weight: 600;
            margin-right: 4px;
        }}
        .predefined-visible,
        .predefined-overflow {{
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .predefined-visible {{
            flex: 1 1 auto;
            min-width: 0;
            overflow: hidden;
        }}
        .predefined-overflow {{
            flex-wrap: wrap;
            padding-top: 12px;
        }}
        .predefined-overflow.hidden {{
            display: none;
        }}
        .preset-toggle {{
            flex: 0 0 auto;
            margin-left: auto;
            display: inline-flex;
            align-items: center;
            gap: 12px;
            border: 0;
            background: transparent;
            color: #666;
            cursor: pointer;
            font-size: 14px;
            font-weight: 600;
            padding: 8px 0 8px 16px;
        }}
        .preset-toggle:hover {{
            color: #1a1a1a;
        }}
        .preset-toggle-icon {{
            font-size: 18px;
            line-height: 1;
        }}
        .predefined-filter {{
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 16px;
            border: 1px solid #e5e5e5;
            border-radius: 6px;
            background: #fff;
            cursor: pointer;
            font-size: 14px;
            color: #4a4a4a;
            transition: all 0.2s;
            white-space: nowrap;
            min-height: 36px;
        }}
        .predefined-filter:hover {{ border-color: #999; color: #333; }}
        .predefined-filter.active {{ background: #1a1a1a; color: #fff; border-color: #1a1a1a; }}
        .predefined-filter .preset-icon {{ font-size: 14px; }}
        .predefined-filter .arrow {{ display: none; }}
        .main-container {{ display: flex; min-height: calc(100vh - 60px); }}
        .sidebar {{
            width: 300px;
            background: #fff;
            border-right: 1px solid #e5e5e5;
            padding: 24px;
            overflow-y: auto;
        }}
        .sidebar-intro {{
            font-size: 15px;
            line-height: 1.5;
            color: #333;
            margin-bottom: 24px;
            font-weight: 500;
        }}
        .filter-section {{ margin-bottom: 24px; }}
        .filter-title {{ font-weight: 600; font-size: 14px; margin-bottom: 12px; color: #1a1a1a; }}
        .filter-options {{ display: flex; flex-direction: column; gap: 8px; }}
        .filter-option {{
            display: flex;
            align-items: center;
            gap: 8px;
            cursor: pointer;
            font-size: 14px;
            color: #666;
        }}
        .filter-option input {{ width: 16px; height: 16px; cursor: pointer; }}
        .filter-option:hover {{ color: #333; }}
        .more-link {{ color: #666; font-size: 13px; cursor: pointer; margin-top: 8px; }}
        .more-link:hover {{ color: #333; }}
        .model-selector select {{
            width: 100%;
            padding: 10px 12px;
            border: 1px solid #e5e5e5;
            border-radius: 6px;
            font-size: 14px;
            background: #fff;
            cursor: pointer;
        }}
        .model-selector select:hover {{ border-color: #999; }}
        .content {{ flex: 1; padding: 24px 32px; background: #fafafa; }}
        .content-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 24px;
        }}
        .results-label {{
            font-size: 12px;
            color: #999;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
        }}
        .results-title {{
            font-size: 24px;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 12px;
        }}
        .results-description {{
            font-size: 14px;
            color: #666;
            margin-top: 8px;
            max-width: 600px;
            line-height: 1.5;
        }}
        .legend-dot {{ width: 24px; height: 8px; border-radius: 4px; }}
        .share-btn {{
            display: flex;
            align-items: center;
            gap: 6px;
            padding: 8px 16px;
            border: 1px solid #e5e5e5;
            border-radius: 6px;
            background: #fff;
            cursor: pointer;
            font-size: 14px;
            color: #666;
        }}
        .share-btn:hover {{ border-color: #999; color: #333; }}
        .chart-container {{
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            padding: 24px;
            margin-bottom: 24px;
            position: relative;
        }}
        #scatter-plot {{ width: 100%; height: 500px; }}
        #scatter-labels {{
            position: absolute;
            pointer-events: none;
            z-index: 2;
        }}
        #chart-tooltip-layer {{
            position: absolute;
            pointer-events: none;
            z-index: 20;
        }}
        .chart-tool-label {{
            position: absolute;
            display: inline-flex;
            align-items: center;
            gap: 7px;
            min-height: 30px;
            padding: 4px 9px 4px 6px;
            border: 1px solid #e5e5e5;
            border-radius: 16px;
            background: #fff;
            color: #1a1a1a;
            box-shadow: 0 2px 7px rgba(0, 0, 0, 0.10);
            font-size: 11px;
            font-weight: 500;
            white-space: nowrap;
            transform: translate(-12px, -50%);
            pointer-events: auto;
        }}
        .chart-tool-label.top-rank {{
            border-color: #4f46e5;
            box-shadow: 0 0 0 2px rgba(79, 70, 229, 0.14), 0 5px 12px rgba(0, 0, 0, 0.12);
        }}
        .chart-tool-icon {{
            width: 20px;
            height: 20px;
            border-radius: 5px;
            display: inline-flex;
            align-items: center;
            justify-content: center;
            flex: 0 0 auto;
            overflow: hidden;
            color: #fff;
            font-size: 9px;
            font-weight: 700;
        }}
        .chart-tool-icon img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
            border-radius: 4px;
            background: #fff;
        }}
        .chart-rank-badge {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            min-width: 22px;
            height: 20px;
            padding: 0 6px;
            border-radius: 999px;
            background: #4f46e5;
            color: #fff;
            font-size: 10px;
            font-weight: 700;
        }}
        .chart-tooltip {{
            position: absolute;
            min-width: 160px;
            padding: 9px 11px;
            border: 2px solid #4f46e5;
            border-radius: 11px;
            background: #fff;
            color: #1a1a1a;
            box-shadow: 0 9px 20px rgba(0, 0, 0, 0.15);
            pointer-events: none;
            text-align: left;
            white-space: normal;
        }}
        .chart-tooltip-title {{
            display: flex;
            align-items: center;
            gap: 6px;
            margin-bottom: 5px;
            font-size: 12px;
            font-weight: 700;
        }}
        .chart-tooltip-row {{
            color: #777;
            font-size: 11px;
            line-height: 1.4;
        }}
        .data-table-container {{
            background: #fff;
            border: 1px solid #e5e5e5;
            border-radius: 8px;
            overflow: hidden;
            margin-bottom: 64px;
        }}
        .table-header {{
            padding: 16px 20px;
            border-bottom: 1px solid #e5e5e5;
            font-weight: 600;
            font-size: 16px;
        }}
        .data-table {{ width: 100%; border-collapse: collapse; }}
        .data-table th {{
            text-align: left;
            padding: 12px 20px;
            font-size: 12px;
            font-weight: 600;
            color: #666;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            border-bottom: 1px solid #e5e5e5;
            background: #fafafa;
            cursor: pointer;
        }}
        .data-table th:hover {{ background: #f0f0f0; }}
        .data-table td {{
            padding: 14px 20px;
            font-size: 14px;
            border-bottom: 1px solid #f0f0f0;
        }}
        .data-table tr:last-child td {{ border-bottom: none; }}
        .data-table tr:hover {{ background: #fafafa; }}
        .tool-cell {{ display: flex; align-items: center; gap: 10px; }}
        .tool-icon {{
            width: 28px;
            height: 28px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: #fff;
            font-size: 12px;
            font-weight: 600;
        }}
        .metric-bar {{ display: flex; align-items: center; gap: 8px; }}
        .metric-bar-fill {{
            height: 6px;
            border-radius: 3px;
            background: #e5e5e5;
            width: 80px;
            overflow: hidden;
        }}
        .metric-bar-value {{ height: 100%; background: #1a1a1a; border-radius: 3px; }}
        .metric-value {{ min-width: 50px; text-align: right; }}
        .repositories-section {{
            padding: 40px 0 56px;
            text-align: center;
        }}
        .repositories-title {{
            font-size: 32px;
            font-weight: 400;
            margin-bottom: 48px;
            color: #111;
        }}
        .repositories-title span {{
            color: #ff4b3e;
        }}
        .repositories-copy {{
            color: #8a8f98;
            font-size: 17px;
            line-height: 1.7;
            max-width: 980px;
            margin: 0 auto 24px;
        }}
        .repositories-copy strong {{
            color: #111;
            font-weight: 600;
        }}
        .repository-links {{
            display: grid;
            grid-template-columns: repeat(5, minmax(140px, 1fr));
            gap: 14px;
            max-width: 1160px;
            margin: 56px auto 0;
        }}
        .repository-card {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            gap: 14px;
            min-height: 58px;
            padding: 0 18px;
            border: 1px solid #e2e2e2;
            border-radius: 8px;
            background: #fff;
            color: #111;
            text-decoration: none;
            box-shadow: 0 1px 2px rgba(0, 0, 0, 0.03);
            transition: border-color 0.2s, box-shadow 0.2s, transform 0.2s;
        }}
        .repository-card:hover {{
            border-color: #bdbdbd;
            box-shadow: 0 8px 22px rgba(0, 0, 0, 0.08);
            transform: translateY(-1px);
        }}
        .repository-card-main {{
            display: flex;
            align-items: center;
            gap: 12px;
            min-width: 0;
        }}
        .repository-icon {{
            width: 32px;
            height: 32px;
            border-radius: 8px;
            object-fit: cover;
            flex: 0 0 auto;
        }}
        .repository-name {{
            font-size: 16px;
            font-weight: 600;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        .repository-arrow {{
            font-size: 20px;
            line-height: 1;
            flex: 0 0 auto;
        }}
        @media (max-width: 1100px) {{
            .repository-links {{
                grid-template-columns: repeat(2, minmax(180px, 1fr));
            }}
        }}
        @media (max-width: 640px) {{
            .repositories-title {{
                font-size: 28px;
                margin-bottom: 28px;
            }}
            .repository-links {{
                grid-template-columns: 1fr;
                margin-top: 36px;
            }}
        }}
        .hidden {{ display: none; }}
        .checkbox-group {{ display: flex; flex-direction: column; gap: 8px; }}
        .checkbox-item {{ display: flex; align-items: center; gap: 8px; font-size: 14px; color: #666; }}
        .checkbox-item input[type="checkbox"] {{ width: 16px; height: 16px; cursor: pointer; }}
    </style>
</head>
<body>
    <div class="predefined-filters">
        <div class="predefined-filters-row">
            <div class="predefined-label">Quick Presets:</div>
            <div class="predefined-visible">
                {visible_filter_buttons_html}
            </div>
            <button class="preset-toggle" id="preset-toggle" type="button" onclick="togglePresetOverflow()" aria-expanded="false" aria-controls="preset-overflow">
                <span id="preset-toggle-label">More</span>
                <span class="preset-toggle-icon" id="preset-toggle-icon">+</span>
            </button>
        </div>
        <div class="predefined-overflow hidden" id="preset-overflow">
            {overflow_filter_buttons_html}
        </div>
    </div>

    <div class="main-container">
        <div class="sidebar">
            <div class="sidebar-intro">
                Tool performance varies by context. Filter and tailor the benchmark to fit your use case:
            </div>

            <div class="filter-section model-selector">
                <div class="filter-title">Judge Model</div>
                <select id="model-select" onchange="changeModel(this.value)">
                    {model_options_html}
                </select>
            </div>

            <div class="filter-section">
                <div class="filter-title">Language</div>
                <div class="filter-options" id="language-filters">
                    {lang_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">PR Size</div>
                <div class="filter-options" id="pr-size-filters">
                    {size_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">Domain</div>
                <div class="filter-options" id="domain-filters">
                    {domain_checkboxes_html}
                </div>
                <div class="more-link" onclick="toggleMore('more-domains')">+ More...</div>
                <div class="filter-options hidden" id="more-domains">
                    {more_domain_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">Code Complexity</div>
                <div class="filter-options">
                    {complexity_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">Review Difficulty</div>
                <div class="filter-options">
                    {difficulty_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">Risk Level</div>
                <div class="filter-options">
                    {risk_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">Context Required</div>
                <div class="filter-options">
                    {context_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">Primary Concern</div>
                <div class="filter-options">
                    {concern_checkboxes_html}
                </div>
            </div>

            <div class="filter-section">
                <div class="filter-title">Show Metrics</div>
                <div class="checkbox-group">
                    <label class="checkbox-item">
                        <input type="checkbox" id="show-precision" checked onchange="updateChart()">
                        Precision
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="show-recall" checked onchange="updateChart()">
                        Recall
                    </label>
                    <label class="checkbox-item">
                        <input type="checkbox" id="show-f1" checked onchange="updateChart()">
                        F1 Score
                    </label>
                </div>
            </div>
        </div>

        <div class="content">
            <div class="content-header">
                <div>
                    <div class="results-label">CURRENT RESULTS</div>
                    <div class="results-title" id="results-title">
                        All Tools
                        <span class="legend-dot" style="background: linear-gradient(90deg, #6366f1 50%, #ec4899 50%);"></span>
                    </div>
                    <div class="results-description" id="results-description"></div>
                </div>
                <button class="share-btn" onclick="shareResults()">
                    Share <span class="arrow">↗</span>
                </button>
            </div>

            <div class="chart-container">
                <div id="scatter-plot"></div>
                <div id="scatter-labels" aria-hidden="true"></div>
                <div id="chart-tooltip-layer" aria-hidden="true"></div>
            </div>

            <div class="data-table-container">
                <div class="table-header">Performance Metrics</div>
                <table class="data-table" id="metrics-table">
                    <thead>
                        <tr>
                            <th onclick="sortTable('rank')">#</th>
                            <th onclick="sortTable('tool')">Tool</th>
                            <th onclick="sortTable('precision')">Precision (%)</th>
                            <th onclick="sortTable('recall')">Recall (%)</th>
                            <th onclick="sortTable('f1')">F1 Score (%)</th>
                            <th onclick="sortTable('tp')">True Positives</th>
                            <th onclick="sortTable('num_prs')">PRs Evaluated</th>
                        </tr>
                    </thead>
                    <tbody id="table-body"></tbody>
                </table>
            </div>

            <section class="repositories-section" aria-labelledby="repositories-title">
                <h2 class="repositories-title" id="repositories-title"><span>Repositories</span> Used</h2>
                <p class="repositories-copy">
                    The offline benchmark draws from a <strong>diverse set of open-source repositories spanning different languages,</strong>
                    frameworks, and domains — from infrastructure and observability tools to web platforms and security projects.
                </p>
                <p class="repositories-copy">
                    This variety ensures our results reflect <strong>how AI reviewers perform across real-world codebases,</strong>
                    not just one type of software.
                </p>
                <div class="repository-links">
                    <a class="repository-card" href="https://github.com/getsentry/sentry" target="_blank" rel="noopener noreferrer">
                        <span class="repository-card-main">
                            <img class="repository-icon" src="https://github.com/getsentry.png" alt="" loading="lazy">
                            <span class="repository-name">Sentry</span>
                        </span>
                        <span class="repository-arrow">↗</span>
                    </a>
                    <a class="repository-card" href="https://github.com/discourse/discourse" target="_blank" rel="noopener noreferrer">
                        <span class="repository-card-main">
                            <img class="repository-icon" src="https://github.com/discourse.png" alt="" loading="lazy">
                            <span class="repository-name">Discourse</span>
                        </span>
                        <span class="repository-arrow">↗</span>
                    </a>
                    <a class="repository-card" href="https://github.com/calcom/cal.com" target="_blank" rel="noopener noreferrer">
                        <span class="repository-card-main">
                            <img class="repository-icon" src="https://github.com/calcom.png" alt="" loading="lazy">
                            <span class="repository-name">cal.com</span>
                        </span>
                        <span class="repository-arrow">↗</span>
                    </a>
                    <a class="repository-card" href="https://github.com/grafana/grafana" target="_blank" rel="noopener noreferrer">
                        <span class="repository-card-main">
                            <img class="repository-icon" src="https://github.com/grafana.png" alt="" loading="lazy">
                            <span class="repository-name">Grafana</span>
                        </span>
                        <span class="repository-arrow">↗</span>
                    </a>
                    <a class="repository-card" href="https://github.com/keycloak/keycloak" target="_blank" rel="noopener noreferrer">
                        <span class="repository-card-main">
                            <img class="repository-icon" src="https://github.com/keycloak.png" alt="" loading="lazy">
                            <span class="repository-name">Keycloak</span>
                        </span>
                        <span class="repository-arrow">↗</span>
                    </a>
                </div>
            </section>
        </div>
    </div>

    <script>
        // All models data embedded
        const allModelsData = {json.dumps(all_models_data)};
        const toolDisplayNames = {json.dumps(TOOL_DISPLAY_NAMES)};
        const toolColors = {json.dumps(TOOL_COLORS)};
        const toolLogos = {json.dumps(tool_logos)};
        const predefinedFilters = {json.dumps(predefined_filters)};

        let currentModel = '{default_model}';
        let currentFilters = {{
            language: [], pr_size: [], domain: [],
            complexity: [], difficulty: [], risk: [],
            context: [], concern: [], change_type: []
        }};
        let currentSort = {{ column: 'f1', direction: 'desc' }};
        let activePredefinedFilter = null;
        let currentChartRows = [];

        function getCurrentData() {{
            return allModelsData[currentModel];
        }}

        function resetFilters() {{
            return {{
                language: [], pr_size: [], domain: [],
                complexity: [], difficulty: [], risk: [],
                context: [], concern: [], change_type: []
            }};
        }}

        document.addEventListener('DOMContentLoaded', function() {{
            updateChart();
            updateTable();
        }});

        window.addEventListener('resize', function() {{
            if (currentChartRows.length) {{
                window.requestAnimationFrame(() => renderChartLabels(currentChartRows));
            }}
        }});

        function changeModel(modelName) {{
            currentModel = modelName;
            updateChart();
            updateTable();
        }}

        function toggleFilter(dimension, value) {{
            if (!currentFilters[dimension]) currentFilters[dimension] = [];
            const index = currentFilters[dimension].indexOf(value);
            if (index > -1) {{
                currentFilters[dimension].splice(index, 1);
            }} else {{
                currentFilters[dimension].push(value);
            }}
            activePredefinedFilter = null;
            updatePredefinedButtons();
            updateChart();
            updateTable();
            updateTitle();
        }}

        function applyPredefinedFilter(filterId) {{
            const filter = predefinedFilters.find(f => f.id === filterId);
            if (!filter) return;

            // Switch to the best model for this filter
            if (filter.best_model && filter.best_model !== currentModel) {{
                currentModel = filter.best_model;
                document.getElementById('model-select').value = currentModel;
            }}

            document.querySelectorAll('.filter-options input[type="checkbox"]').forEach(cb => {{
                cb.checked = false;
            }});

            currentFilters = resetFilters();

            if (filter.filters) {{
                for (const [dim, values] of Object.entries(filter.filters)) {{
                    currentFilters[dim] = [...values];
                    values.forEach(v => {{
                        const checkbox = document.getElementById(`filter-${{dim}}-${{v}}`);
                        if (checkbox) checkbox.checked = true;
                    }});
                }}
            }}

            if (filter.sort) {{
                currentSort = {{ column: filter.sort, direction: 'desc' }};
            }}

            activePredefinedFilter = filterId;
            updatePredefinedButtons();
            updateChart();
            updateTable();
            updateTitle();
        }}

        function updatePredefinedButtons() {{
            document.querySelectorAll('.predefined-filter').forEach(btn => {{
                btn.classList.remove('active');
            }});
            if (activePredefinedFilter) {{
                const btn = document.querySelector(`[data-filter-id="${{activePredefinedFilter}}"]`);
                if (btn) btn.classList.add('active');
            }}
        }}

        function updateTitle() {{
            const titleEl = document.getElementById('results-title');
            const descEl = document.getElementById('results-description');
            let title = 'All Tools';
            let description = '';

            if (activePredefinedFilter) {{
                const filter = predefinedFilters.find(f => f.id === activePredefinedFilter);
                if (filter) {{
                    title = filter.label;
                    description = filter.description || '';
                }}
            }} else {{
                const activeFilters = [];
                if (currentFilters.language.length) activeFilters.push(currentFilters.language.join(', '));
                if (currentFilters.pr_size.length) activeFilters.push(currentFilters.pr_size.map(s => s.charAt(0).toUpperCase() + s.slice(1) + ' PRs').join(', '));
                if (currentFilters.domain.length) activeFilters.push(currentFilters.domain.join(', '));
                if (activeFilters.length) title = activeFilters.join(' | ');
            }}

            titleEl.innerHTML = title + ' <span class="legend-dot" style="background: linear-gradient(90deg, #6366f1 50%, #ec4899 50%);"></span>';
            descEl.textContent = description;
        }}

        function getFilteredMetrics() {{
            const data = getCurrentData();
            const hasFilters = Object.values(currentFilters).some(arr => arr.length > 0);

            if (!hasFilters) {{
                return data.overall_metrics;
            }}

            const filteredPRs = data.prs.filter(pr => {{
                if (currentFilters.language.length && !currentFilters.language.includes(pr.language)) return false;
                if (currentFilters.pr_size.length && !currentFilters.pr_size.includes(pr.pr_size)) return false;
                if (currentFilters.domain.length && !currentFilters.domain.includes(pr.domain)) return false;
                if (currentFilters.complexity.length && !currentFilters.complexity.includes(pr.complexity)) return false;
                if (currentFilters.difficulty.length && !currentFilters.difficulty.includes(pr.difficulty)) return false;
                if (currentFilters.risk.length && !currentFilters.risk.includes(pr.risk)) return false;
                if (currentFilters.context.length && !currentFilters.context.includes(pr.context)) return false;
                if (currentFilters.concern.length && !currentFilters.concern.includes(pr.concern)) return false;
                if (currentFilters.change_type.length && !currentFilters.change_type.includes(pr.change_type)) return false;
                return true;
            }});

            const metrics = {{}};
            for (const tool of data.tools) {{
                let tp = 0, fp = 0, fn = 0, numPrs = 0;
                for (const pr of filteredPRs) {{
                    if (pr.tool_metrics[tool]) {{
                        tp += pr.tool_metrics[tool].tp;
                        fp += pr.tool_metrics[tool].fp;
                        fn += pr.tool_metrics[tool].fn;
                        numPrs++;
                    }}
                }}

                const precision = (tp + fp) > 0 ? (tp / (tp + fp)) * 100 : 0;
                const recall = (tp + fn) > 0 ? (tp / (tp + fn)) * 100 : 0;
                const f1 = (precision + recall) > 0 ? (2 * precision * recall / (precision + recall)) : 0;

                metrics[tool] = {{
                    precision: Math.round(precision * 10) / 10,
                    recall: Math.round(recall * 10) / 10,
                    f1: Math.round(f1 * 10) / 10,
                    tp: tp,
                    fp: fp,
                    fn: fn,
                    num_prs: numPrs
                }};
            }}

            return metrics;
        }}

        function getMetricRows(metrics) {{
            return Object.entries(metrics).map(([tool, m]) => ({{
                tool: tool,
                displayName: toolDisplayNames[tool] || tool,
                color: toolColors[tool] || '#666',
                logo: toolLogos[tool] || null,
                ...m
            }}));
        }}

        function sortMetricRows(rows) {{
            rows.sort((a, b) => {{
                const aVal = a[currentSort.column];
                const bVal = b[currentSort.column];
                if (currentSort.column === 'rank') {{
                    return currentSort.direction === 'asc'
                        ? a.f1 - b.f1
                        : b.f1 - a.f1;
                }}
                if (currentSort.column === 'tool') {{
                    return currentSort.direction === 'asc'
                        ? a.displayName.localeCompare(b.displayName)
                        : b.displayName.localeCompare(a.displayName);
                }}
                return currentSort.direction === 'asc' ? aVal - bVal : bVal - aVal;
            }});
            return rows;
        }}

        function updateChart() {{
            const data = getCurrentData();
            const metrics = getFilteredMetrics();

            const rows = sortMetricRows(getMetricRows(metrics))
                .filter(row => row.num_prs > 0);

            rows.forEach((row, index) => {{
                row.rank = index + 1;
                row.rankLabel = row.rank <= 3 ? `#${{row.rank}}` : '';
            }});
            currentChartRows = rows;

            const x = rows.map(row => row.precision);
            const y = rows.map(row => row.recall);
            const customdata = rows.map(row => [
                row.rankLabel,
                row.displayName,
                row.f1,
                row.precision,
                row.recall,
                row.num_prs
            ]);
            const xMin = Math.max(0, Math.min(...x, 0) - 8);
            const xMax = Math.min(100, Math.max(...x, 10) + 10);
            const yMin = Math.max(0, Math.min(...y, 0) - 8);
            const yMax = Math.min(100, Math.max(...y, 10) + 10);

            const trace = {{
                x: x,
                y: y,
                customdata: customdata,
                mode: 'markers',
                type: 'scatter',
                marker: {{
                    size: 16,
                    color: rows.map(row => row.color),
                    opacity: 0.12,
                    line: {{ color: '#fff', width: 2 }}
                }},
                hoverinfo: 'skip'
            }};

            const layout = {{
                xaxis: {{
                    title: {{ text: 'Precision | Less noisy →', font: {{ size: 12 }} }},
                    range: [xMin, xMax],
                    gridcolor: '#f0f0f0',
                    zeroline: false
                }},
                yaxis: {{
                    title: {{ text: 'Recall | More thorough →', font: {{ size: 12 }} }},
                    range: [yMin, yMax],
                    gridcolor: '#f0f0f0',
                    zeroline: false
                }},
                margin: {{ l: 72, r: 180, t: 28, b: 72 }},
                paper_bgcolor: 'transparent',
                plot_bgcolor: '#fff',
                showlegend: false,
                hovermode: false
            }};

            Plotly.newPlot('scatter-plot', [trace], layout, {{ responsive: true, displayModeBar: false }})
                .then(() => renderChartLabels(rows));
        }}

        function renderChartLabels(rows) {{
            const plot = document.getElementById('scatter-plot');
            const labels = document.getElementById('scatter-labels');
            const tooltipLayer = document.getElementById('chart-tooltip-layer');
            const chartContainer = plot.closest('.chart-container');
            const layout = plot._fullLayout;

            if (!labels || !tooltipLayer || !layout || !layout.xaxis || !layout.yaxis) return;

            const plotRect = plot.getBoundingClientRect();
            const containerRect = chartContainer.getBoundingClientRect();
            labels.style.left = `${{plotRect.left - containerRect.left}}px`;
            labels.style.top = `${{plotRect.top - containerRect.top}}px`;
            labels.style.width = `${{plotRect.width}}px`;
            labels.style.height = `${{plotRect.height}}px`;
            tooltipLayer.style.left = `${{plotRect.left - containerRect.left}}px`;
            tooltipLayer.style.top = `${{plotRect.top - containerRect.top}}px`;
            tooltipLayer.style.width = `${{plotRect.width}}px`;
            tooltipLayer.style.height = `${{plotRect.height}}px`;
            tooltipLayer.innerHTML = '';

            labels.innerHTML = rows.map(row => {{
                const x = layout.margin.l + layout.xaxis.l2p(row.precision);
                const y = layout.margin.t + layout.yaxis.l2p(row.recall);
                const rankBadge = row.rank <= 3 ? `<span class="chart-rank-badge">#${{row.rank}}</span>` : '';
                const icon = row.logo
                    ? `<span class="chart-tool-icon"><img src="${{row.logo}}" alt=""></span>`
                    : `<span class="chart-tool-icon" style="background:${{row.color}}">${{row.displayName.charAt(0)}}</span>`;

                return `
                    <div class="chart-tool-label ${{row.rank <= 3 ? 'top-rank' : ''}}" data-tool="${{row.tool}}" style="left:${{x}}px;top:${{y}}px">
                        ${{icon}}
                        <span>${{row.displayName}}</span>
                        ${{rankBadge}}
                    </div>
                `;
            }}).join('');

            labels.querySelectorAll('.chart-tool-label').forEach(label => {{
                const row = rows.find(item => item.tool === label.dataset.tool);
                if (!row) return;

                label.addEventListener('mouseenter', () => showChartTooltip(row, label, tooltipLayer, plotRect));
                label.addEventListener('mouseleave', () => {{
                    tooltipLayer.innerHTML = '';
                }});
            }});
        }}

        function showChartTooltip(row, label, tooltipLayer, plotRect) {{
            const labelRect = label.getBoundingClientRect();
            const tooltipHtml = `
                <div class="chart-tooltip">
                    <div class="chart-tooltip-title">${{row.rank <= 3 ? `#${{row.rank}} ` : ''}}${{row.displayName}}</div>
                    <div class="chart-tooltip-row">F1 Score: ${{row.f1.toFixed(1)}}%</div>
                    <div class="chart-tooltip-row">Precision: ${{row.precision.toFixed(1)}}%</div>
                    <div class="chart-tooltip-row">Recall: ${{row.recall.toFixed(1)}}%</div>
                    <div class="chart-tooltip-row">Sample Size: ${{row.num_prs}} PRs</div>
                </div>
            `;

            tooltipLayer.innerHTML = tooltipHtml;
            const tooltip = tooltipLayer.querySelector('.chart-tooltip');
            const left = labelRect.left - plotRect.left + (labelRect.width / 2);
            const top = labelRect.top - plotRect.top - 12;

            tooltip.style.left = `${{left}}px`;
            tooltip.style.top = `${{top}}px`;
            tooltip.style.transform = 'translate(-50%, -100%)';
        }}

        function updateTable() {{
            const metrics = getFilteredMetrics();
            const tbody = document.getElementById('table-body');

            let rows = sortMetricRows(getMetricRows(metrics));

            tbody.innerHTML = rows.map((row, index) => `
                <tr>
                    <td>${{index + 1}}</td>
                    <td>
                        <div class="tool-cell">
                            ${{toolLogos[row.tool]
                                ? `<div class="tool-icon" style="background:#fff;padding:2px"><img src="${{toolLogos[row.tool]}}" style="width:100%;height:100%;object-fit:contain;border-radius:4px" /></div>`
                                : `<div class="tool-icon" style="background:${{row.color}}">${{row.displayName.charAt(0)}}</div>`
                            }}
                            ${{row.displayName}}
                        </div>
                    </td>
                    <td>
                        <div class="metric-bar">
                            <div class="metric-bar-fill">
                                <div class="metric-bar-value" style="width: ${{row.precision}}%"></div>
                            </div>
                            <span class="metric-value">${{row.precision.toFixed(1)}}%</span>
                        </div>
                    </td>
                    <td>
                        <div class="metric-bar">
                            <div class="metric-bar-fill">
                                <div class="metric-bar-value" style="width: ${{row.recall}}%"></div>
                            </div>
                            <span class="metric-value">${{row.recall.toFixed(1)}}%</span>
                        </div>
                    </td>
                    <td>
                        <div class="metric-bar">
                            <div class="metric-bar-fill">
                                <div class="metric-bar-value" style="width: ${{row.f1}}%"></div>
                            </div>
                            <span class="metric-value">${{row.f1.toFixed(1)}}%</span>
                        </div>
                    </td>
                    <td>${{row.tp}}</td>
                    <td>${{row.num_prs}}</td>
                </tr>
            `).join('');
        }}

        function sortTable(column) {{
            if (currentSort.column === column) {{
                currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
            }} else {{
                currentSort.column = column;
                currentSort.direction = 'desc';
            }}
            updateChart();
            updateTable();
        }}

        function toggleMore(elementId) {{
            document.getElementById(elementId).classList.toggle('hidden');
        }}

        function togglePresetOverflow() {{
            const overflow = document.getElementById('preset-overflow');
            const toggle = document.getElementById('preset-toggle');
            const label = document.getElementById('preset-toggle-label');
            const icon = document.getElementById('preset-toggle-icon');
            const isExpanded = overflow.classList.toggle('hidden') === false;

            toggle.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
            label.textContent = isExpanded ? 'Less' : 'More';
            icon.textContent = isExpanded ? '-' : '+';
        }}

        function shareResults() {{
            const params = new URLSearchParams();
            params.set('model', currentModel);
            for (const [dim, values] of Object.entries(currentFilters)) {{
                if (values.length) params.set(dim, values.join(','));
            }}

            const url = window.location.href.split('?')[0] + '?' + params.toString();
            navigator.clipboard.writeText(url).then(() => {{
                alert('Link copied to clipboard!');
            }});
        }}
    </script>
</body>
</html>
"""
    return html


def generate_json_data(all_models_data: dict, default_model: str) -> dict:
    """Generate JSON data structure for export."""
    # Generate and enrich predefined filters
    predefined_filters = generate_predefined_filters(all_models_data)
    predefined_filters = enrich_predefined_filters(predefined_filters, all_models_data)

    return {
        "models": all_models_data,
        "predefined_filters": predefined_filters,
        "tool_display_names": TOOL_DISPLAY_NAMES,
        "tool_colors": TOOL_COLORS,
        "default_model": default_model,
        "min_prs_threshold": MIN_PRS_FOR_FILTER,
    }


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="Generate benchmark dashboard HTML and JSON")
    parser.add_argument("--results-dir", type=Path, default=Path("results"),
                        help="Directory containing model results")
    parser.add_argument("--output", type=Path, default=Path("analysis/benchmark_dashboard.html"),
                        help="Output HTML file path")
    parser.add_argument("--json-output", type=Path, default=None,
                        help="Output JSON file path (default: same as HTML with .json extension)")

    args = parser.parse_args()

    # Default JSON output path
    if args.json_output is None:
        args.json_output = args.output.with_suffix(".json")

    print("Loading all models data...")
    all_models_data = load_all_models(args.results_dir)

    if not all_models_data:
        print(f"No model results found in {args.results_dir}")
        return

    # Use the model with the most tools evaluated as default
    default_model = max(all_models_data.keys(), key=lambda m: len(all_models_data[m].get("tools", [])))

    # Load logos (optional — place images in analysis/logos/{tool_slug}.png)
    logos_dir = args.output.parent / "logos"
    tool_logos = load_tool_logos(logos_dir)
    if tool_logos:
        print(f"  Loaded logos for: {', '.join(sorted(tool_logos))}")

    # Generate HTML
    print(f"Generating HTML dashboard (default model: {default_model})...")
    html = generate_html(all_models_data, default_model, tool_logos)

    args.output.parent.mkdir(exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Generated: {args.output}")

    # Generate JSON
    print("Generating JSON data...")
    json_data = generate_json_data(all_models_data, default_model)

    with open(args.json_output, "w", encoding="utf-8") as f:
        json.dump(json_data, f, indent=2)
    print(f"Generated: {args.json_output}")

    # Print summary: each tool and what it's best at
    print("\n" + "=" * 60)
    print("TOOL STRENGTHS SUMMARY")
    print("=" * 60)

    # Get all tools
    all_tools = set()
    for model_data in all_models_data.values():
        all_tools.update(model_data.get("tools", []))

    # Find first filter for each tool
    tool_filters = {}
    for f in json_data["predefined_filters"]:
        tool = f.get("best_tool")
        if tool and tool not in tool_filters:
            tool_filters[tool] = f

    # Print each tool
    for tool in sorted(all_tools):
        display_name = TOOL_DISPLAY_NAMES.get(tool, tool)
        if tool in tool_filters:
            f = tool_filters[tool]
            print(f"  {display_name:20s} -> {f['label']}")
        else:
            print(f"  {display_name:20s} -> (no winning filter found)")

    print("=" * 60)


if __name__ == "__main__":
    main()
