"""Data I/O and chart helpers for the Streamlit lab."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, List, Optional

import pandas as pd
import streamlit as st
import yaml

from trading_dag.viz.constants import SESSION_EMERGENCY_KILL_ALL_TS_KEY


def emergency_kill_all_since_run_started(run_state: dict[str, Any], session_state: Any) -> bool:
    """
    True if the sidebar emergency kill-all ran successfully after this run started.

    Uses ``time.time()`` timestamps from ``run_state["started_at"]`` and session state.
    """
    try:
        kill_ts = float(session_state.get(SESSION_EMERGENCY_KILL_ALL_TS_KEY, 0) or 0)
    except (TypeError, ValueError):
        kill_ts = 0.0
    if kill_ts <= 0:
        return False
    try:
        started = float(run_state.get("started_at", 0) or 0)
    except (TypeError, ValueError):
        started = 0.0
    return kill_ts >= started - 0.5


def project_root() -> Path:
    """Repository root (``.../src/trading_dag/viz/helpers.py`` → parents[3])."""
    return Path(__file__).resolve().parents[3]


def _workspace_chart_timezone(default: str = "UTC") -> str:
    """``timezone`` from ``config/config.yaml`` (matches standalone CLI backtest)."""
    cfg_path = project_root() / "config" / "config.yaml"
    try:
        if not cfg_path.is_file():
            return default
        with cfg_path.open(encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        tz = data.get("timezone", default)
        return str(tz).strip() if tz is not None else default
    except Exception:
        return default


def _benchmark_suite_chart_timezone(default: str = "UTC") -> str:
    """``main.timezone`` from ``config/benchmark.yaml``, else workspace config."""
    bench_path = project_root() / "config" / "benchmark.yaml"
    try:
        if bench_path.is_file():
            with bench_path.open(encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            main = data.get("main") or {}
            tz = main.get("timezone")
            if tz is not None and str(tz).strip():
                return str(tz).strip()
    except Exception:
        pass
    return _workspace_chart_timezone(default=default)


def list_live_decision_jsons(directory: Path) -> List[Path]:
    """Files written by ``TradingSystemRunner._save_decision_history`` in live mode."""
    if not directory.is_dir():
        return []
    return sorted(
        directory.glob("live_decisions_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _short_path_for_ui(path: Path, max_chars: int = 52) -> str:
    """Ellipsize long paths for sidebar captions."""
    s = str(path)
    if len(s) <= max_chars:
        return s
    sep = "…"
    keep = max_chars - len(sep)
    head = keep // 2
    tail = keep - head
    return s[:head] + sep + s[-tail:]


def _list_csvs(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.csv"), key=lambda p: p.stat().st_mtime, reverse=True)


def _list_pngs(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.png"), key=lambda p: p.stat().st_mtime, reverse=True)


def _list_jsons(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(directory.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)


def _is_benchmark_equity_csv(path: Path) -> bool:
    name = path.name.lower()
    return "equity" in name and "benchmark" in name


def _is_benchmark_summary_csv(path: Path) -> bool:
    name = path.name.lower()
    return "summary" in name and "benchmark" in name


def _is_trade_history_csv(path: Path) -> bool:
    """Heuristic: date-like column + ticker + action."""
    try:
        df = pd.read_csv(path, nrows=3)
    except Exception:
        return False
    if df.empty:
        return False
    cols = {c.lower() for c in df.columns}
    if not {"ticker", "action"}.issubset(cols):
        return False
    date_like = bool(
        cols & {"date", "datetime", "time", "open_time", "close_time", "timestamp"}
    )
    return date_like


def _list_standard_backtest_performance_csvs(directory: Path) -> List[Path]:
    """Files written by ``TradingSystemRunner._export_backtest_results``."""
    if not directory.is_dir():
        return []
    return sorted(
        directory.glob("backtest_performance_*.csv"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _list_standard_backtest_trade_jsons(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        directory.glob("backtest_trades_*.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _list_standard_backtest_logs(directory: Path) -> List[Path]:
    if not directory.is_dir():
        return []
    return sorted(
        directory.glob("backtest_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _list_standard_backtest_pngs(directory: Path) -> List[Path]:
    """Optional chart from ``Backtester.analyze_performance``."""
    if not directory.is_dir():
        return []
    return sorted(
        directory.glob("backtest_portfolio_value_*.png"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _read_standard_backtest_perf_for_plot(path: Path) -> Optional[pd.DataFrame]:
    """Build a frame compatible with ``_plotly_equity`` from a standard performance CSV."""
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    if df.empty:
        return None
    date_col = None
    for key in ("Date", "date", "datetime", "open_time", "close_time"):
        if key in df.columns:
            date_col = key
            break
    if date_col is None:
        return None
    pv_col = None
    for key in ("Portfolio Value", "portfolio_value"):
        if key in df.columns:
            pv_col = key
            break
    if pv_col is None:
        for c in df.columns:
            cl = c.lower()
            if "portfolio" in cl and "value" in cl:
                pv_col = c
                break
    if pv_col is None:
        return None
    out = df.copy()
    out["_plot_date"] = pd.to_datetime(out[date_col], errors="coerce")
    out = out.dropna(subset=["_plot_date"])
    out["portfolio_value"] = pd.to_numeric(out[pv_col], errors="coerce")
    out = out.dropna(subset=["portfolio_value"])
    if out.empty:
        return None
    out["experiment"] = path.stem
    return out


def _kpis_from_value_series(values: pd.Series) -> tuple[Optional[float], Optional[float], Optional[float], Optional[float]]:
    """
    From a chronological portfolio value series: total return %, dollar PnL, Sharpe (daily-ish approx), max DD %.
    """
    s = pd.to_numeric(values, errors="coerce").dropna()
    if len(s) < 2:
        return None, None, None, None
    initial = float(s.iloc[0])
    final = float(s.iloc[-1])
    if abs(initial) < 1e-12:
        return None, None, None, None
    total_return_pct = (final - initial) / initial * 100.0
    pnl = final - initial
    rolling_max = s.cummax()
    denom = rolling_max.clip(lower=1e-12)
    dd = (s - rolling_max) / denom
    max_dd_pct = float(dd.min() * 100.0)
    daily_ret = s.pct_change().dropna()
    sharpe = None
    if len(daily_ret) > 1:
        std = float(daily_ret.std())
        if std > 1e-12:
            sharpe = float(daily_ret.mean() / std) * (252.0**0.5)
    return total_return_pct, pnl, sharpe, max_dd_pct


def _read_equity_df(path: Path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_csv(path)
    except Exception:
        return None
    if df.empty:
        return None
    cols = {c.lower(): c for c in df.columns}
    if "portfolio_value" not in cols and "Portfolio Value" in df.columns:
        df = df.rename(columns={"Portfolio Value": "portfolio_value"})
    if "experiment" not in df.columns and "Experiment" in df.columns:
        df = df.rename(columns={"Experiment": "experiment"})
    date_col = None
    for key in ("date", "Date", "datetime", "open_time", "close_time"):
        if key in df.columns:
            date_col = key
            break
    if date_col is None:
        return None
    df = df.copy()
    df["_plot_date"] = pd.to_datetime(df[date_col], errors="coerce")
    df = df.dropna(subset=["_plot_date"])
    if "portfolio_value" not in df.columns:
        candidates = [c for c in df.columns if "value" in c.lower() or "equity" in c.lower()]
        if not candidates:
            return None
        df = df.rename(columns={candidates[0]: "portfolio_value"})
    if "experiment" not in df.columns:
        df["experiment"] = path.stem
    return df


def _plotly_equity(df: pd.DataFrame, *, chart_timezone: str = "UTC") -> Any:
    import plotly.express as px

    x_title = f"Date ({chart_timezone})"
    fig = px.line(
        df,
        x="_plot_date",
        y="portfolio_value",
        color="experiment",
        labels={
            "_plot_date": x_title,
            "portfolio_value": "Portfolio value",
            "experiment": "Run",
        },
        template="plotly_white",
        color_discrete_sequence=["#0048f0", "#18a838", "#d82020", "#c6a656", "#7c5cff"],
    )
    fig.update_layout(
        paper_bgcolor="#f5f8fd",
        plot_bgcolor="#ffffff",
        font=dict(family="IBM Plex Sans, sans-serif", color="#1c2230"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=40, r=20, t=60, b=40),
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(90,101,120,0.2)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(90,101,120,0.2)")
    return fig


def _preview_json(path: Path, max_chars: int = 12000) -> str:
    try:
        text = path.read_text(encoding="utf-8")
    except Exception as exc:
        return f"(Could not read file: {exc})"
    if len(text) > max_chars:
        return text[:max_chars] + "\n\n… (truncated)"
    return text


def _pick_summary_row(df: pd.DataFrame, experiment: Optional[str]) -> Optional[pd.Series]:
    if df.empty:
        return None
    if experiment and "experiment" in df.columns:
        m = df[df["experiment"].astype(str) == experiment]
        if not m.empty:
            return m.iloc[0]
    return df.iloc[0]


def _safe_float(val: Any) -> Optional[float]:
    try:
        return float(val)
    except (TypeError, ValueError):
        return None


def _metric_from_row(row: pd.Series, *candidates: str) -> Optional[float]:
    lower = {str(k).lower().replace(" ", "_"): k for k in row.index}
    for c in candidates:
        key = c.lower().replace(" ", "_")
        if key in lower:
            return _safe_float(row[lower[key]])
        if c in row.index:
            return _safe_float(row[c])
    return None


def _page_header(kicker: str, title: str, blurb: str) -> None:
    st.markdown(
        f"""
        <div class="viz-kicker">{kicker}</div>
        <div class="viz-page-title">{title}</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown(blurb)
