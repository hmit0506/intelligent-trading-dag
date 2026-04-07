"""Benchmark builder screen with benchmark config editing."""
from __future__ import annotations

import os
import re
import signal
import subprocess
import time
from io import StringIO
from datetime import date, datetime
from pathlib import Path
from typing import Any

import streamlit as st
from ruamel.yaml import YAML

from trading_dag.viz.helpers import _page_header

BENCHMARK_CONFIG_REL = Path("config/benchmark.yaml")
DEFAULT_INTERVAL_OPTIONS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
DEFAULT_PROVIDERS = ["openai", "groq", "anthropic", "google", "ollama", "openrouter"]
DEFAULT_STRATEGIES = ["MacdStrategy", "RSIStrategy", "BollingerStrategy"]
DEFAULT_PHASE1_EXPERIMENTS = ["SingleMACD", "SingleRSI", "SingleBollinger"]
DEFAULT_PHASE2_EXPERIMENTS = [
    "Ablate_MultiInterval",
    "Ablate_LLMPortfolio",
    "Ablate_RiskSizing",
]
DEFAULT_RESPONSE_FORMATS = ["json"]
YAML_RW = YAML(typ="rt")
YAML_RW.preserve_quotes = True
YAML_RW.indent(mapping=2, sequence=4, offset=2)
RUN_STATE_KEY = "viz_benchmark_run_state"
RUN_LOG_LINES = 120
RUN_LOG_AUTO_REFRESH_KEY = "benchmark_run_log_auto_refresh"
RUN_NOTICE_KEY = "benchmark_run_notice"
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TRACEBACK_BLOCK_RE = re.compile(r"Traceback \(most recent call last\):[\s\S]*?(?:KeyboardInterrupt|$)")
PY_FATAL_BLOCK_RE = re.compile(r"object address\s*:[\s\S]*?lost sys\.stderr", re.IGNORECASE)
PROGRESS_RE = re.compile(
    r"Backtesting:\s*(?:(?P<pct>\d{1,3})%\|[^\n]*?\|)?\s*(?P<done>\d+)\s*/\s*(?P<total>\d+)[^\n]*?"
    r"Value=\$(?P<value>[+\-]?[\d,\.]+?)\s*,\s*Return=(?P<ret>[+\-]?[\d,\.]+)%",
    re.IGNORECASE,
)
PORTFOLIO_RE = re.compile(
    r"Cash:\s*\$(?P<cash>[-\d,\.]+)\s*\|\s*Positions:\s*\$(?P<positions>[-\d,\.]+)\s*\|\s*"
    r"Total:\s*\$(?P<total>[-\d,\.]+)\s*\|\s*Return[^\:]*:\s*(?P<total_return>[+\-]?[\d,\.]+)%",
    re.IGNORECASE,
)
RISK_RE = re.compile(
    r"Sharpe Ratio:\s*(?P<sharpe>(?:[+\-]?[\d,\.]+|N/?A))\s*\|\s*"
    r"Sortino Ratio:\s*(?P<sortino>(?:[+\-]?[\d,\.]+|N/?A))\s*\|\s*"
    r"Max Drawdown:\s*(?P<mdd>(?:[+\-]?[\d,\.]+|N/?A))%?",
    re.IGNORECASE,
)
PHASE_PROGRESS_RE = re.compile(
    r"\[(?P<phase>Phase\d+)\]\[(?P<idx>\d+)\s*/\s*(?P<total>\d+)\]\s*"
    r"(?:(?:DAG experiment)|(?:Ablation)):\s*(?P<name>.+?)\s*-\s*(?P<status>start|done)",
    re.IGNORECASE,
)


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _parse_date(value: Any) -> date:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.strptime(value.strip(), "%Y-%m-%d").date()
        except ValueError:
            return date.today()
    return date.today()


def _comma_split(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def _load_yaml(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    if not path.is_file():
        return None, f"Config not found: {path}"
    try:
        with path.open(encoding="utf-8") as f:
            data = YAML_RW.load(f) or {}
    except Exception as exc:
        return None, str(exc)
    if not isinstance(data, dict):
        return None, "benchmark.yaml root must be a mapping."
    return data, None


def _write_yaml(path: Path, data: dict[str, Any]) -> str | None:
    try:
        with path.open("w", encoding="utf-8") as f:
            YAML_RW.dump(data, f)
        return None
    except Exception as exc:
        return str(exc)


def _dump_yaml_text(data: Any) -> str:
    buf = StringIO()
    YAML_RW.dump(data, buf)
    return buf.getvalue()


def _is_pid_running(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    # On macOS, zombie PIDs can still pass kill(pid, 0); filter them out.
    try:
        res = subprocess.run(
            ["ps", "-o", "stat=", "-p", str(pid)],
            capture_output=True,
            text=True,
            timeout=1.0,
            check=False,
        )
        stat = (res.stdout or "").strip()
        if not stat:
            return False
        if stat.startswith("Z"):
            return False
    except Exception:
        pass
    return True


def _read_log_tail(log_path: Path, max_lines: int = RUN_LOG_LINES) -> str:
    if not log_path.is_file():
        return "(log file not created yet)"
    try:
        lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except Exception as exc:
        return f"(failed to read log: {exc})"
    if not lines:
        return "(no output yet)"
    return "\n".join(lines[-max_lines:])


def _read_log_for_metrics(log_path: Path, max_chars: int = 1_000_000) -> str:
    """Read a larger chunk for metrics extraction (independent of tail-lines UI)."""
    if not log_path.is_file():
        return ""
    try:
        text = log_path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return ""
    if len(text) <= max_chars:
        return text
    return text[-max_chars:]


def _clean_terminal_output(text: str) -> str:
    """Strip ANSI color/control codes for readable web display."""
    cleaned = ANSI_ESCAPE_RE.sub("", text)
    return cleaned.replace("\r", "")


def _clean_interruption_noise(text: str) -> str:
    cleaned = TRACEBACK_BLOCK_RE.sub("[interrupted traceback omitted]\n", text)
    return PY_FATAL_BLOCK_RE.sub("[python fatal stderr block omitted]\n", cleaned)


def _detect_failure_reason(log_text: str) -> str | None:
    """Detect whether the run likely exited due to an exception."""
    if "Traceback (most recent call last):" in log_text:
        if "KeyboardInterrupt" in log_text:
            return "KeyboardInterrupt"
        return "Python exception"
    if "lost sys.stderr" in log_text:
        return "Python fatal stderr"
    return None


def _parse_float(raw: str) -> float | None:
    try:
        return float(raw.replace(",", "").strip().rstrip(","))
    except Exception:
        return None


def _parse_float_or_na(raw: str) -> float | str | None:
    token = raw.strip().upper()
    if token in {"N/A", "NA"}:
        return "N/A"
    return _parse_float(raw)


def _extract_live_metrics(log_text: str) -> dict[str, float | int | str]:
    metrics: dict[str, float | int | str] = {}
    progress_hits = list(PROGRESS_RE.finditer(log_text))
    if progress_hits:
        hit = progress_hits[-1]
        done = int(hit.group("done"))
        total = int(hit.group("total"))
        pct_raw = hit.group("pct")
        pct = int(pct_raw) if pct_raw is not None else (int(round((done / total) * 100.0)) if total > 0 else 0)
        metrics["progress_pct"] = pct
        metrics["progress_done"] = done
        metrics["progress_total"] = total
        value = _parse_float(hit.group("value"))
        ret = _parse_float(hit.group("ret"))
        if value is not None:
            metrics["progress_value"] = value
        if ret is not None:
            metrics["progress_return_pct"] = ret

    portfolio_hits = list(PORTFOLIO_RE.finditer(log_text))
    if portfolio_hits:
        hit = portfolio_hits[-1]
        for key in ("cash", "positions", "total", "total_return"):
            parsed = _parse_float(hit.group(key))
            if parsed is not None:
                metrics[f"portfolio_{key}"] = parsed

    risk_hits = list(RISK_RE.finditer(log_text))
    if risk_hits:
        hit = risk_hits[-1]
        for key in ("sharpe", "sortino", "mdd"):
            parsed = _parse_float_or_na(hit.group(key))
            if parsed is not None:
                metrics[f"risk_{key}"] = parsed

    phase_hits = list(PHASE_PROGRESS_RE.finditer(log_text))
    if phase_hits:
        hit = phase_hits[-1]
        idx = int(hit.group("idx"))
        total = int(hit.group("total"))
        status = hit.group("status").lower()
        done = idx if status == "done" else max(0, idx - 1)
        pct = int(round((done / total) * 100.0)) if total > 0 else 0
        metrics["suite_phase"] = hit.group("phase")
        metrics["suite_current_name"] = hit.group("name").strip()
        metrics["suite_done"] = done
        metrics["suite_total"] = total
        metrics["suite_progress_pct"] = pct
    return metrics


def _estimate_log_view_height(log_text: str, min_height: int = 260, max_height: int = 900) -> int:
    """Estimate a readable log panel height from current tail length."""
    line_count = max(1, len(log_text.splitlines()))
    estimated = line_count * 18 + 32
    return max(min_height, min(max_height, estimated))


def _format_compact_currency(value: float | None) -> str:
    if value is None:
        return "—"
    sign = "-" if value < 0 else ""
    abs_value = abs(value)
    if abs_value >= 1_000_000_000:
        return f"{sign}${abs_value / 1_000_000_000:.2f}B"
    if abs_value >= 1_000_000:
        return f"{sign}${abs_value / 1_000_000:.2f}M"
    if abs_value >= 1_000:
        return f"{sign}${abs_value / 1_000:.2f}k"
    return f"{sign}${abs_value:,.2f}"


def _list_streamlit_run_logs(log_dir: Path, pattern: str = "*_streamlit_run_*.log") -> list[Path]:
    log_dir = log_dir.resolve()
    if not log_dir.is_dir():
        return []
    return sorted(
        log_dir.glob(pattern),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _start_benchmark_run(root: Path, phase: str, cfg_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    cli_module = "trading_dag.cli.benchmark_phase1" if phase == "phase1" else "trading_dag.cli.benchmark_phase2"
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = (root / "output" / "benchmark" / f"{phase}_streamlit_run_{run_id}.log").resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["uv", "run", "python", "-m", cli_module, "--config", str(cfg_path)]
    try:
        with log_path.open("w", encoding="utf-8") as log_file:
            # Non-TTY stdout is block-buffered by default; force line-buffered prints into the log file.
            run_env = {**os.environ, "PYTHONUNBUFFERED": "1"}
            process = subprocess.Popen(
                cmd,
                cwd=str(root),
                stdout=log_file,
                stderr=subprocess.STDOUT,
                start_new_session=True,
                env=run_env,
            )
    except Exception as exc:
        return None, str(exc)
    state = {
        "pid": process.pid,
        "pgid": os.getpgid(process.pid),
        "phase": phase,
        "cmd": " ".join(cmd),
        "log_path": str(log_path),
        "started_at": time.time(),
        "stop_requested": False,
        "notified_finished": False,
        "terminal_status": "running",
    }
    return state, None


def _stop_benchmark_run(state: dict[str, Any]) -> str | None:
    try:
        pid = int(state.get("pid", -1))
    except (TypeError, ValueError):
        return "Invalid PID."
    if pid <= 0:
        return "Invalid PID."
    try:
        pgid = int(state.get("pgid", pid))
    except (TypeError, ValueError):
        pgid = pid
    # Escalating stop for process group: SIGINT -> SIGTERM -> SIGKILL.
    def _send_group(sig: int) -> None:
        try:
            os.killpg(pgid, sig)
        except OSError:
            os.kill(pid, sig)

    for sig, wait_s in ((signal.SIGINT, 1.0), (signal.SIGTERM, 1.5), (signal.SIGKILL, 1.0)):
        try:
            _send_group(sig)
        except OSError:
            pass
        # Extra fallback: kill direct children of the launcher process.
        try:
            subprocess.run(
                ["pkill", f"-{sig.value if hasattr(sig, 'value') else int(sig)}", "-P", str(pid)],
                capture_output=True,
                text=True,
                timeout=1.0,
                check=False,
            )
        except Exception:
            pass
        deadline = time.time() + wait_s
        while time.time() < deadline:
            if not _is_pid_running(pid):
                return None
            time.sleep(0.1)
    if _is_pid_running(pid):
        return "Process is still running after SIGKILL."
    return None


def render(root: Path) -> None:
    _page_header(
        "Benchmark Builder",
        "Edit benchmark settings",
        "Load `config/benchmark.yaml`, tune suite parameters, and save back to the same file.",
    )
    notice = st.session_state.pop(RUN_NOTICE_KEY, None)
    if isinstance(notice, str) and notice.strip():
        st.warning(notice)
        st.toast(notice, icon="🛑")

    cfg_path = (root / BENCHMARK_CONFIG_REL).resolve()
    col_meta_l, col_meta_r = st.columns([3, 2])
    with col_meta_l:
        st.caption(f"Config file: `{cfg_path}`")
    with col_meta_r:
        reload_clicked = st.button("Reload from file", use_container_width=True)

    cfg, load_err = _load_yaml(cfg_path)
    if load_err:
        st.error(f"Could not load benchmark config: {load_err}")
        return
    assert cfg is not None

    if reload_clicked:
        st.rerun()

    main_cfg = cfg.setdefault("main", {})
    phase1_cfg = cfg.setdefault("phase1", {})
    phase2_cfg = cfg.setdefault("phase2", {})
    if not isinstance(main_cfg, dict) or not isinstance(phase1_cfg, dict) or not isinstance(phase2_cfg, dict):
        st.error("`main`, `phase1`, and `phase2` must be mappings in benchmark.yaml.")
        return

    model_cfg = main_cfg.setdefault("model", {})
    signals_cfg = main_cfg.setdefault("signals", {})
    risk_cfg = main_cfg.setdefault("risk", {})
    output_layout_cfg = main_cfg.setdefault("output_layout", {})

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Main (shared run settings)</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        timezone = st.text_input("Timezone", value=str(main_cfg.get("timezone", "UTC")).strip())
        start_d = st.date_input("Start date", value=_parse_date(main_cfg.get("start_date")))
        end_d = st.date_input("End date", value=_parse_date(main_cfg.get("end_date")))
    with c2:
        interval_options = list(dict.fromkeys(DEFAULT_INTERVAL_OPTIONS + [str(main_cfg.get("primary_interval", "1h"))]))
        primary_interval = st.selectbox(
            "Primary interval",
            interval_options,
            index=max(0, interval_options.index(str(main_cfg.get("primary_interval", "1h")))),
        )
        initial_cash = st.number_input(
            "Initial cash",
            min_value=0.0,
            step=1000.0,
            value=float(main_cfg.get("initial_positions", {}).get("cash", 100000.0)),
        )
        margin_requirement = st.number_input(
            "Margin requirement",
            min_value=0.0,
            step=0.01,
            value=float(main_cfg.get("margin_requirement", 0.0)),
        )
        sync_from_exchange = st.checkbox(
            "Sync from exchange",
            value=bool(main_cfg.get("sync_from_exchange", False)),
            help="Mainly for live/account sync; usually false for benchmark backtests.",
        )
        print_frequency = st.number_input(
            "Print frequency",
            min_value=1,
            step=1,
            value=int(main_cfg.get("print_frequency", 1)),
        )
    with c3:
        benchmark_subdir = st.text_input(
            "Benchmark subdir",
            value=str(output_layout_cfg.get("benchmark_subdir", "benchmark")),
        )
        show_reasoning = st.checkbox("Show LLM reasoning", value=bool(main_cfg.get("show_reasoning", False)))
        show_graph = st.checkbox("Save workflow graph", value=bool(main_cfg.get("show_agent_graph", True)))
        use_progress_bar = st.checkbox(
            "Use progress bar",
            value=bool(main_cfg.get("use_progress_bar", True)),
        )
        enable_logging = st.checkbox(
            "Enable logging",
            value=bool(main_cfg.get("enable_logging", True)),
        )
        save_history = st.checkbox(
            "Save decision history",
            value=bool(main_cfg.get("save_decision_history", True)),
            help="Mainly used by live mode; kept here for config parity.",
        )
        auto_cleanup_files = st.checkbox(
            "Auto cleanup files",
            value=bool(main_cfg.get("auto_cleanup_files", False)),
        )
        file_retention_days = st.number_input(
            "File retention days",
            min_value=1,
            step=1,
            value=int(main_cfg.get("file_retention_days", 30)),
        )
        file_keep_latest = st.number_input(
            "File keep latest",
            min_value=1,
            step=1,
            value=int(main_cfg.get("file_keep_latest", 10)),
        )

    positions_yaml_default = _dump_yaml_text(main_cfg.get("initial_positions", {}).get("positions", {}))
    with st.expander("Initial positions map (advanced)", expanded=False):
        positions_yaml = st.text_area(
            "main.initial_positions.positions (YAML mapping)",
            value=positions_yaml_default if isinstance(positions_yaml_default, str) else "{}\n",
            height=120,
            key="benchmark_initial_positions_yaml",
        )

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Signals & model</span></div>',
        unsafe_allow_html=True,
    )
    s1, s2 = st.columns(2)
    with s1:
        intervals_default = [str(x) for x in _as_list(signals_cfg.get("intervals"))]
        intervals_options = list(dict.fromkeys(DEFAULT_INTERVAL_OPTIONS + intervals_default))
        intervals = st.multiselect(
            "Signal intervals",
            intervals_options,
            default=intervals_default,
        )
        tickers = st.text_input(
            "Tickers (comma-separated)",
            value=", ".join(str(x) for x in _as_list(signals_cfg.get("tickers"))),
        )
        strategies_options = list(
            dict.fromkeys(DEFAULT_STRATEGIES + [str(x) for x in _as_list(signals_cfg.get("strategies"))])
        )
        strategies = st.multiselect(
            "Strategies",
            strategies_options,
            default=[str(x) for x in _as_list(signals_cfg.get("strategies"))],
        )
    with s2:
        provider_options = list(dict.fromkeys(DEFAULT_PROVIDERS + [str(model_cfg.get("provider", "openai"))]))
        model_provider = st.selectbox(
            "Model provider",
            provider_options,
            index=max(0, provider_options.index(str(model_cfg.get("provider", "openai")))),
        )
        model_name = st.text_input("Model name", value=str(model_cfg.get("name", "deepseek-chat")))
        model_base_url = st.text_input("Model base_url", value=str(model_cfg.get("base_url", "") or ""))
        model_temperature = st.number_input(
            "Model temperature",
            min_value=0.0,
            max_value=2.0,
            step=0.1,
            value=float(model_cfg.get("temperature", 0.0)),
        )
        format_options = list(dict.fromkeys(DEFAULT_RESPONSE_FORMATS + [str(model_cfg.get("format", "json"))]))
        model_format = st.selectbox(
            "Response format",
            format_options,
            index=max(0, format_options.index(str(model_cfg.get("format", "json")))),
        )

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Risk sizing</span></div>',
        unsafe_allow_html=True,
    )
    r1, r2, r3 = st.columns(3)
    with r1:
        risk_per_trade_pct = st.number_input(
            "Risk per trade %",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=float(risk_cfg.get("risk_per_trade_pct", 0.02)),
        )
        stop_loss_pct = st.number_input(
            "Stop loss %",
            min_value=0.0,
            max_value=1.0,
            step=0.01,
            value=float(risk_cfg.get("stop_loss_pct", 0.05)),
        )
        max_notional_fraction = st.number_input(
            "Max notional fraction per ticker",
            min_value=0.0,
            max_value=1.0,
            step=0.05,
            value=float(risk_cfg.get("max_notional_fraction_per_ticker", 1.0)),
        )
    with r2:
        min_quantity = st.number_input(
            "Min quantity",
            min_value=0.0,
            step=0.001,
            value=float(risk_cfg.get("min_quantity", 0.001)),
        )
        quantity_decimals = st.number_input(
            "Quantity decimals",
            min_value=0,
            max_value=10,
            step=1,
            value=int(risk_cfg.get("quantity_decimals", 3)),
        )
        stop_distance_mode = st.selectbox(
            "Stop distance mode",
            ["entry_or_spot_pct", "atr"],
            index=0 if str(risk_cfg.get("stop_distance_mode", "entry_or_spot_pct")) == "entry_or_spot_pct" else 1,
        )
    with r3:
        atr_period = st.number_input(
            "ATR period",
            min_value=1,
            max_value=500,
            step=1,
            value=int(risk_cfg.get("atr_period", 14)),
        )
        atr_multiplier = st.number_input(
            "ATR multiplier",
            min_value=0.1,
            max_value=10.0,
            step=0.1,
            value=float(risk_cfg.get("atr_multiplier", 1.0)),
        )

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Phase 1 / Phase 2 suite options</span></div>',
        unsafe_allow_html=True,
    )
    p1, p2 = st.columns(2)
    with p1:
        phase1_print_frequency = st.number_input(
            "Phase1 print frequency",
            min_value=1,
            step=1,
            value=int(phase1_cfg.get("dag_print_frequency", 1)),
        )
        phase1_progress = st.checkbox(
            "Phase1 use progress bar",
            value=bool(phase1_cfg.get("dag_use_progress_bar", False)),
        )
        phase1_exports = st.checkbox(
            "Phase1 export individual results",
            value=bool(phase1_cfg.get("export_individual_results", True)),
        )
        phase1_charts = st.checkbox(
            "Phase1 export charts",
            value=bool(phase1_cfg.get("export_charts", True)),
        )
        phase1_experiments = st.multiselect(
            "Phase1 experiments",
            DEFAULT_PHASE1_EXPERIMENTS,
            default=[x for x in _as_list(phase1_cfg.get("include_dag_experiments")) if isinstance(x, str)],
        )
    with p2:
        phase2_print_frequency = st.number_input(
            "Phase2 print frequency",
            min_value=1,
            step=1,
            value=int(phase2_cfg.get("dag_print_frequency", 999)),
        )
        phase2_progress = st.checkbox(
            "Phase2 use progress bar",
            value=bool(phase2_cfg.get("dag_use_progress_bar", True)),
        )
        phase2_exports = st.checkbox(
            "Phase2 export individual results",
            value=bool(phase2_cfg.get("export_individual_results", True)),
        )
        phase2_charts = st.checkbox(
            "Phase2 export charts",
            value=bool(phase2_cfg.get("export_charts", True)),
        )
        phase2_experiments = st.multiselect(
            "Phase2 experiments",
            DEFAULT_PHASE2_EXPERIMENTS,
            default=[x for x in _as_list(phase2_cfg.get("include_ablation_experiments")) if isinstance(x, str)],
            help="Empty means run all registered ablations (with FullDAG auto-prepended).",
        )

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Save</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(f"Save target: `{cfg_path}`")
    save_clicked = st.button("Save benchmark.yaml", type="primary", use_container_width=True)
    if save_clicked:
        errors: list[str] = []
        if end_d < start_d:
            errors.append("End date must be on or after start date.")
        ticker_list = _comma_split(tickers)
        if not ticker_list:
            errors.append("At least one ticker is required.")
        if not intervals:
            errors.append("At least one signal interval is required.")
        if not strategies:
            errors.append("At least one strategy is required.")
        if not benchmark_subdir.strip():
            errors.append("Benchmark subdir cannot be empty.")

        if errors:
            for err in errors:
                st.error(err)
        else:
            positions_mapping: dict[str, Any] = {}
            try:
                parsed_positions = YAML_RW.load(positions_yaml) if positions_yaml.strip() else {}
                if parsed_positions is None:
                    parsed_positions = {}
                if not isinstance(parsed_positions, dict):
                    raise ValueError("initial_positions.positions must be a mapping.")
                positions_mapping = parsed_positions
            except Exception as exc:
                st.error(f"Invalid initial_positions.positions YAML: {exc}")
                return

            main_cfg["mode"] = "backtest"
            main_cfg["timezone"] = timezone.strip() or "UTC"
            main_cfg["start_date"] = start_d.isoformat()
            main_cfg["end_date"] = end_d.isoformat()
            main_cfg["primary_interval"] = primary_interval
            main_cfg["margin_requirement"] = float(margin_requirement)
            main_cfg["sync_from_exchange"] = bool(sync_from_exchange)
            main_cfg["show_reasoning"] = bool(show_reasoning)
            main_cfg["show_agent_graph"] = bool(show_graph)
            main_cfg["use_progress_bar"] = bool(use_progress_bar)
            main_cfg["enable_logging"] = bool(enable_logging)
            main_cfg["save_decision_history"] = bool(save_history)
            main_cfg["print_frequency"] = int(print_frequency)
            main_cfg["auto_cleanup_files"] = bool(auto_cleanup_files)
            main_cfg["file_retention_days"] = int(file_retention_days)
            main_cfg["file_keep_latest"] = int(file_keep_latest)
            main_cfg["initial_positions"] = main_cfg.get("initial_positions", {}) if isinstance(
                main_cfg.get("initial_positions"), dict
            ) else {}
            main_cfg["initial_positions"]["cash"] = float(initial_cash)
            main_cfg["initial_positions"]["positions"] = positions_mapping

            output_layout_cfg["benchmark_subdir"] = benchmark_subdir.strip()

            signals_cfg["intervals"] = intervals
            signals_cfg["tickers"] = ticker_list
            signals_cfg["strategies"] = strategies

            model_cfg["provider"] = model_provider
            model_cfg["name"] = model_name.strip()
            model_cfg["base_url"] = model_base_url.strip() or None
            model_cfg["temperature"] = float(model_temperature)
            model_cfg["format"] = model_format

            risk_cfg["risk_per_trade_pct"] = float(risk_per_trade_pct)
            risk_cfg["stop_loss_pct"] = float(stop_loss_pct)
            risk_cfg["min_quantity"] = float(min_quantity)
            risk_cfg["quantity_decimals"] = int(quantity_decimals)
            risk_cfg["stop_distance_mode"] = stop_distance_mode
            risk_cfg["atr_period"] = int(atr_period)
            risk_cfg["atr_multiplier"] = float(atr_multiplier)
            risk_cfg["max_notional_fraction_per_ticker"] = float(max_notional_fraction)

            phase1_cfg["dag_print_frequency"] = int(phase1_print_frequency)
            phase1_cfg["dag_use_progress_bar"] = bool(phase1_progress)
            phase1_cfg["include_dag_experiments"] = phase1_experiments
            phase1_cfg["export_individual_results"] = bool(phase1_exports)
            phase1_cfg["export_charts"] = bool(phase1_charts)

            phase2_cfg["dag_print_frequency"] = int(phase2_print_frequency)
            phase2_cfg["dag_use_progress_bar"] = bool(phase2_progress)
            phase2_cfg["include_ablation_experiments"] = phase2_experiments
            phase2_cfg["export_individual_results"] = bool(phase2_exports)
            phase2_cfg["export_charts"] = bool(phase2_charts)

            write_err = _write_yaml(cfg_path, cfg)
            if write_err:
                st.error(f"Save failed: {write_err}")
            else:
                st.success("Saved `config/benchmark.yaml`")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Run via terminal</span></div>',
        unsafe_allow_html=True,
    )
    st.code(
        "uv run python -m trading_dag.cli.benchmark_phase1 --config config/benchmark.yaml\n"
        "# or\n"
        "uv run python -m trading_dag.cli.benchmark_phase2 --config config/benchmark.yaml",
        language="bash",
    )

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Run benchmark in this page</span></div>',
        unsafe_allow_html=True,
    )
    st.caption(
        "This launches the benchmark CLI in the background and streams logs from a file. "
        "For page-driven runs, monitor progress in `Run logs` below. "
        "Save `benchmark.yaml` first if you changed form values."
    )
    run_state = st.session_state.get(RUN_STATE_KEY)
    is_running = False
    if isinstance(run_state, dict):
        try:
            pid = int(run_state.get("pid", -1))
        except (TypeError, ValueError):
            pid = -1
        is_running = _is_pid_running(pid)
        if not is_running and run_state.get("finished_at") is None:
            failure_reason = None
            try:
                state_log = Path(str(run_state.get("log_path", "")))
                raw_log = _clean_terminal_output(_read_log_for_metrics(state_log))
                failure_reason = _detect_failure_reason(raw_log)
            except Exception:
                failure_reason = None
            run_state["finished_at"] = time.time()
            run_state["terminal_status"] = "failed" if failure_reason else "finished"
            if failure_reason and not bool(run_state.get("stop_requested", False)):
                run_state["failure_reason"] = failure_reason
            st.session_state[RUN_STATE_KEY] = run_state
        if (
            not is_running
            and run_state.get("finished_at") is not None
            and not bool(run_state.get("notified_finished", False))
        ):
            if bool(run_state.get("stop_requested", False)):
                st.warning("Benchmark run stopped.")
            elif str(run_state.get("terminal_status", "")).lower() == "failed":
                reason = str(run_state.get("failure_reason", "unknown error"))
                st.error(f"Benchmark run failed ({reason}). Check traceback in the log panel.")
            else:
                st.success("Benchmark run finished.")
            st.toast("Run status updated", icon="✅")
            run_state["notified_finished"] = True
            st.session_state[RUN_STATE_KEY] = run_state

    run_col1, run_col2, run_col3 = st.columns([1, 1, 1])
    with run_col1:
        run_phase1 = st.button("Run Phase 1", disabled=is_running, use_container_width=True)
    with run_col2:
        run_phase2 = st.button("Run Phase 2", disabled=is_running, use_container_width=True)
    with run_col3:
        stop_run = st.button("Stop running task", disabled=not is_running, use_container_width=True)

    if run_phase1 or run_phase2:
        phase = "phase1" if run_phase1 else "phase2"
        new_state, start_err = _start_benchmark_run(root, phase, cfg_path)
        if start_err:
            st.error(f"Could not start {phase}: {start_err}")
        else:
            st.session_state[RUN_STATE_KEY] = new_state
            st.success(f"Started {phase} run (PID {new_state['pid']}).")
            st.rerun()

    if stop_run and isinstance(run_state, dict):
        run_state["stop_requested"] = True
        st.session_state[RUN_STATE_KEY] = run_state
        st.session_state[RUN_LOG_AUTO_REFRESH_KEY] = False
        stop_err = _stop_benchmark_run(run_state)
        if stop_err:
            st.warning(f"Could not stop run: {stop_err}")
        else:
            run_state["finished_at"] = time.time()
            run_state["terminal_status"] = "stopped"
            run_state["notified_finished"] = True
            st.session_state[RUN_STATE_KEY] = run_state
            st.session_state[RUN_NOTICE_KEY] = "Benchmark run stopped."
        st.rerun()

    run_state = st.session_state.get(RUN_STATE_KEY)
    running_now = False
    if isinstance(run_state, dict):
        pid_text = run_state.get("pid", "—")
        phase_text = run_state.get("phase", "—")
        log_path = Path(str(run_state.get("log_path", "")))
        try:
            started_ts = float(run_state.get("started_at", 0.0))
        except (TypeError, ValueError):
            started_ts = 0.0
        elapsed = max(0.0, time.time() - started_ts) if started_ts > 0 else 0.0
        running_now = _is_pid_running(int(pid_text)) if str(pid_text).isdigit() else False
        terminal_status = str(run_state.get("terminal_status", "")).lower()
        if terminal_status == "stopped":
            status = "Stopped"
        elif terminal_status == "failed":
            status = "Failed"
        elif terminal_status == "finished" or (not running_now and run_state.get("finished_at") is not None):
            status = "Finished"
        else:
            status = "Running"
        m1, m2, m3 = st.columns(3)
        m1.metric("Status", status)
        m2.metric("Phase", str(phase_text))
        m3.metric("PID", str(pid_text))
        st.caption(f"Elapsed: {elapsed:.1f}s")
        st.caption(f"Log file: `{log_path}`")
        if running_now:
            st.info("Run is active. Click Refresh in sidebar to update logs.")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Run logs</span></div>',
        unsafe_allow_html=True,
    )
    benchmark_log_dir = (root / "output" / "benchmark").resolve()
    log_files = _list_streamlit_run_logs(benchmark_log_dir)
    default_log = None
    if isinstance(run_state, dict) and run_state.get("log_path"):
        state_log = Path(str(run_state["log_path"]))
        if state_log.is_file():
            default_log = state_log
    if default_log is None and log_files:
        default_log = log_files[0]

    if not log_files:
        st.caption("No streamlit run logs found yet. Start Phase 1 or Phase 2 above.")
    else:
        selected = st.selectbox(
            "Select log file",
            log_files,
            index=log_files.index(default_log) if default_log in log_files else 0,
            format_func=lambda p: p.name,
            key="benchmark_run_log_file",
        )
        tail_lines = st.slider(
            "Tail lines",
            min_value=40,
            max_value=1200,
            value=280,
            step=20,
            key="benchmark_run_log_tail_lines",
        )
        log_text = _read_log_tail(selected, max_lines=int(tail_lines))
        log_text = _clean_terminal_output(log_text)

        metrics_source = _clean_terminal_output(_read_log_for_metrics(selected))
        live_metrics = _extract_live_metrics(metrics_source)
        if live_metrics:
            st.markdown(
                '<div class="viz-panel-title"><span></span><span>Live run metrics</span></div>',
                unsafe_allow_html=True,
            )
            suite_pct = live_metrics.get("suite_progress_pct")
            if isinstance(suite_pct, int):
                bounded_suite = max(0, min(100, suite_pct))
                suite_done = live_metrics.get("suite_done")
                suite_total = live_metrics.get("suite_total")
                phase = str(live_metrics.get("suite_phase", "Suite"))
                exp_name = str(live_metrics.get("suite_current_name", "")).strip()
                suite_label = (
                    f"{phase}: {bounded_suite}% ({int(suite_done)}/{int(suite_total)}) — {exp_name}"
                    if isinstance(suite_done, int) and isinstance(suite_total, int) and exp_name
                    else (
                        f"{phase}: {bounded_suite}% ({int(suite_done)}/{int(suite_total)})"
                        if isinstance(suite_done, int) and isinstance(suite_total, int)
                        else f"{phase}: {bounded_suite}%"
                    )
                )
                st.progress(bounded_suite, text=suite_label)

            progress_pct = live_metrics.get("progress_pct")
            progress_done = live_metrics.get("progress_done")
            progress_total = live_metrics.get("progress_total")
            if isinstance(progress_pct, int):
                bounded_pct = max(0, min(100, progress_pct))
                backtest_label = (
                    f"Backtesting progress: {bounded_pct}% ({int(progress_done)}/{int(progress_total)})"
                    if isinstance(progress_done, int) and isinstance(progress_total, int)
                    else f"Backtesting progress: {bounded_pct}%"
                )
                st.progress(bounded_pct, text=backtest_label)

            if "suite_progress_pct" in live_metrics:
                s1, s2, s3 = st.columns(3)
                s1.metric(
                    "Benchmark progress",
                    f"{int(live_metrics['suite_progress_pct'])}%",
                    delta=f"{int(live_metrics['suite_done'])}/{int(live_metrics['suite_total'])}",
                )
                s2.metric("Phase", str(live_metrics.get("suite_phase", "—")))
                s3.metric("Current experiment", str(live_metrics.get("suite_current_name", "—")))

            p1, p2, p3, p4 = st.columns(4)
            if isinstance(progress_pct, int):
                p1.metric(
                    "Progress",
                    f"{progress_pct}%",
                    delta=(
                        f"{int(progress_done)}/{int(progress_total)}"
                        if isinstance(progress_done, int) and isinstance(progress_total, int)
                        else None
                    ),
                )
            else:
                p1.metric("Progress", "—")
            p2.metric(
                "Live value",
                _format_compact_currency(float(live_metrics["progress_value"]))
                if "progress_value" in live_metrics
                else "—",
            )
            p3.metric(
                "Live return",
                f"{float(live_metrics['progress_return_pct']):+.2f}%"
                if "progress_return_pct" in live_metrics
                else "—",
            )
            p4.metric(
                "Portfolio total",
                _format_compact_currency(float(live_metrics["portfolio_total"]))
                if "portfolio_total" in live_metrics
                else "—",
            )

            q1, q2, q3, q4 = st.columns(4)
            q1.metric(
                "Cash",
                _format_compact_currency(float(live_metrics["portfolio_cash"]))
                if "portfolio_cash" in live_metrics
                else "—",
            )
            q2.metric(
                "Positions",
                _format_compact_currency(float(live_metrics["portfolio_positions"]))
                if "portfolio_positions" in live_metrics
                else "—",
            )
            q3.metric(
                "Summary return",
                f"{float(live_metrics['portfolio_total_return']):+.2f}%"
                if "portfolio_total_return" in live_metrics
                else "—",
            )
            q4.metric(
                "Max drawdown",
                (
                    f"{float(live_metrics['risk_mdd']):.2f}%"
                    if isinstance(live_metrics.get("risk_mdd"), float)
                    else str(live_metrics.get("risk_mdd", "—"))
                ),
            )

            r1, r2 = st.columns(2)
            r1.metric(
                "Sharpe ratio",
                (
                    f"{float(live_metrics['risk_sharpe']):+.2f}"
                    if isinstance(live_metrics.get("risk_sharpe"), float)
                    else str(live_metrics.get("risk_sharpe", "—"))
                ),
            )
            r2.metric(
                "Sortino ratio",
                (
                    f"{float(live_metrics['risk_sortino']):+.2f}"
                    if isinstance(live_metrics.get("risk_sortino"), float)
                    else str(live_metrics.get("risk_sortino", "—"))
                ),
            )

        auto_height = st.checkbox(
            "Auto-fit log window height",
            value=True,
            key="benchmark_run_log_auto_height",
            help="Use an adaptive panel height based on current tail length.",
        )
        manual_height = st.slider(
            "Manual log height (px)",
            min_value=220,
            max_value=1200,
            value=560,
            step=20,
            disabled=auto_height,
            key="benchmark_run_log_height_px",
        )
        log_height = _estimate_log_view_height(log_text) if auto_height else int(manual_height)
        st.caption(f"Log panel height: {log_height}px")
        st.code(log_text, language="text", height=log_height)

        auto_refresh = st.checkbox(
            "Live tail (auto refresh every 2s)",
            value=bool(st.session_state.get(RUN_LOG_AUTO_REFRESH_KEY, True)),
            key=RUN_LOG_AUTO_REFRESH_KEY,
            help="Enable to keep updating logs while a run is active.",
        )
        if auto_refresh and running_now:
            st.caption("Live tail is on. Refreshing logs every 2 seconds...")
            time.sleep(2)
            st.rerun()

