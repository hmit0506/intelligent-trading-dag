"""
Resolved output directory layout (backtest / benchmark / live) under a single root.

Defaults match the conventional folder names: ``output/{backtest,benchmark,live}``.
Paths are resolved relative to *cwd* unless ``root`` is absolute.

**YAML split:** ``root``, ``backtest_subdir``, and ``live_subdir`` are defined only in
``config/config.yaml``. ``benchmark_subdir`` is defined only under ``main.output_layout`` in
``config/benchmark.yaml``. Use :func:`resolve_output_layout_for_benchmark` when building a
full layout for benchmark runs or the Streamlit lab.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, NamedTuple, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field


class OutputLayoutConfig(BaseModel):
    """
    Artifact tree: ``cwd / root / {backtest_subdir,benchmark_subdir,live_subdir}``.

    Configure ``root``, ``backtest_subdir``, ``live_subdir`` in ``config/config.yaml``.
    Configure ``benchmark_subdir`` in ``config/benchmark.yaml`` → ``main.output_layout`` only.
    """

    model_config = ConfigDict(extra="ignore")

    root: str = Field(
        default="output",
        description="Artifact tree root under cwd; set only in config/config.yaml output_layout.",
    )
    backtest_subdir: str = Field(
        default="backtest",
        description="Backtest exports; set only in config/config.yaml output_layout.",
    )
    benchmark_subdir: str = Field(
        default="benchmark",
        description="Benchmark suite folder; set only in config/benchmark.yaml main.output_layout.",
    )
    live_subdir: str = Field(
        default="live",
        description="Live decision JSON; set only in config/config.yaml output_layout.",
    )


class ResolvedOutputDirs(NamedTuple):
    root: Path
    backtest: Path
    benchmark: Path
    live: Path


def _dirs_under_artifact_root(base: Path, layout: OutputLayoutConfig) -> ResolvedOutputDirs:
    base = base.expanduser().resolve()
    return ResolvedOutputDirs(
        root=base,
        backtest=(base / layout.backtest_subdir).resolve(),
        benchmark=(base / layout.benchmark_subdir).resolve(),
        live=(base / layout.live_subdir).resolve(),
    )


def resolve_output_dirs(
    cwd: Path,
    layout: OutputLayoutConfig,
) -> ResolvedOutputDirs:
    """
    Resolve paths for CLI / library use when the process cwd is the repo (or project) root.

    The artifact tree root is ``cwd / layout.root`` (e.g. ``./output``), then subdirs
    ``backtest``, ``benchmark``, ``live``.
    """
    return _dirs_under_artifact_root(cwd / layout.root, layout)


def read_benchmark_main_output_layout(benchmark_yaml: Path) -> Optional[Dict[str, Any]]:
    """
    Return ``main.output_layout`` from a benchmark YAML file, or ``None`` if missing/unreadable.

    Only ``benchmark_subdir`` is read from this block when merging layouts; other keys are ignored.
    """
    if not benchmark_yaml.is_file():
        return None
    try:
        with open(benchmark_yaml, encoding="utf-8") as f:
            data: Any = yaml.safe_load(f) or {}
        main = data.get("main") or {}
        ol = main.get("output_layout")
        return ol if isinstance(ol, dict) else None
    except Exception:
        return None


def resolve_output_layout_for_benchmark(
    config_yaml: Path,
    benchmark_main_output_layout: Optional[Dict[str, Any]] = None,
) -> OutputLayoutConfig:
    """
    Merge layout for benchmark tooling and Streamlit.

    - ``root``, ``backtest_subdir``, ``live_subdir``: from *config_yaml* when it exists and loads;
      otherwise defaults.
    - ``benchmark_subdir``: optional override from *benchmark_main_output_layout* (typically
      ``main.output_layout`` in ``benchmark.yaml``).
    """
    layout = OutputLayoutConfig()
    if config_yaml.is_file():
        try:
            from trading_dag.utils.config import load_config

            layout = load_config(str(config_yaml)).output_layout
        except Exception:
            try:
                with open(config_yaml, encoding="utf-8") as f:
                    data: Any = yaml.safe_load(f) or {}
                ol = data.get("output_layout")
                if isinstance(ol, dict):
                    layout = OutputLayoutConfig(**ol)
            except Exception:
                layout = OutputLayoutConfig()
    if isinstance(benchmark_main_output_layout, dict):
        bs = benchmark_main_output_layout.get("benchmark_subdir")
        if isinstance(bs, str) and bs.strip():
            layout = layout.model_copy(update={"benchmark_subdir": bs.strip()})
    return layout


def resolve_artifact_root_dirs(artifact_root: Path, layout: OutputLayoutConfig) -> ResolvedOutputDirs:
    """
    Resolve paths when *artifact_root* is already the directory that contains
    ``backtest/``, ``benchmark/``, and ``live/`` (no extra ``layout.root`` segment).

    Use this for Streamlit workspace paths that already point at ``.../output``.
    """
    return _dirs_under_artifact_root(artifact_root, layout)


def resolve_benchmark_output_path(config: Any, output_dir_override: Optional[str]) -> Path:
    """
    Directory for benchmark suite CSV/PNG exports.

    Uses ``config.output_layout`` when *output_dir_override* is None or blank.
    """
    if output_dir_override is not None and str(output_dir_override).strip() != "":
        raw = Path(output_dir_override).expanduser()
        return raw.resolve() if raw.is_absolute() else (Path.cwd() / raw).resolve()
    layout = getattr(config, "output_layout", None)
    if layout is None:
        layout = OutputLayoutConfig()
    return resolve_output_dirs(Path.cwd(), layout).benchmark
