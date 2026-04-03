"""
Shared helpers for benchmark_phase1 and benchmark_phase2 CLIs.
"""
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

from trading_dag.utils.config import Config, load_config

FIGURE_PATH_LABELS = {
    "equity_absolute": "Equity chart (absolute $)",
    "equity_normalized": "Equity chart (normalized, start=100)",
    "returns_bar": "Total return bar chart",
}


def load_benchmark_options(path: str) -> Dict[str, Any]:
    """Load optional benchmark overrides from yaml file."""
    benchmark_path = Path(path)
    if not benchmark_path.exists():
        return {}
    with benchmark_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"Benchmark config must be a mapping: {path}")
    return data


def load_yaml_mapping(path: str) -> Dict[str, Any]:
    """Load yaml file root as a mapping; return {} if missing or empty."""
    yaml_path = Path(path)
    if not yaml_path.exists():
        return {}
    with yaml_path.open("r", encoding="utf-8") as file:
        data = yaml.safe_load(file) or {}
    if not isinstance(data, dict):
        raise ValueError(f"YAML root must be a mapping: {path}")
    return data


def as_string_list(raw_value: Any) -> List[str]:
    """Normalize config value to a list of non-empty strings."""
    if raw_value is None:
        return []
    if isinstance(raw_value, list):
        return [str(item).strip() for item in raw_value if str(item).strip()]
    if isinstance(raw_value, str):
        normalized = raw_value.strip()
        return [normalized] if normalized else []
    return []


def load_unified_benchmark(
    config_path: str,
    phase_section: str,
) -> Tuple[Config, Dict[str, Any]]:
    """
    Load Config + phase options from unified benchmark.yaml (main + phase1|phase2).

    If the file has no ``main`` key, fall back to legacy ``load_config`` with empty options.
    """
    combined = load_yaml_mapping(config_path)
    if "main" not in combined:
        return load_config(config_path), {}

    main_cfg = combined.get("main", {})
    if not isinstance(main_cfg, dict):
        raise ValueError("benchmark.yaml field 'main' must be a mapping")

    raw_phase = combined.get(phase_section)
    if raw_phase is None:
        options: Dict[str, Any] = {}
    elif isinstance(raw_phase, dict):
        options = raw_phase
    else:
        raise ValueError(f"benchmark.yaml field '{phase_section}' must be a mapping")

    return Config(**main_cfg), options


def print_suite_outputs(results: Dict[str, Any], phase_label: str) -> None:
    """Print summary table, CSV paths, and figure paths from a phase runner return dict."""
    summary_df = results["summary_df"]
    print(f"\n{phase_label} benchmark completed.")
    print(summary_df.to_string(index=False))
    print(f"\nSummary CSV: {results['summary_path']}")
    if results.get("equity_path"):
        print(f"Equity CSV: {results['equity_path']}")
    for key, path in sorted((results.get("figure_paths") or {}).items()):
        if path:
            print(f"{FIGURE_PATH_LABELS.get(key, key)}: {path}")
