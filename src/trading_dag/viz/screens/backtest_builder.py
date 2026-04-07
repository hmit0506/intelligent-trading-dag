"""Standard backtest builder screen (config.yaml + run + logs)."""
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

CONFIG_PATH_REL = Path("config/config.yaml")
DEFAULT_INTERVAL_OPTIONS = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
DEFAULT_PROVIDERS = ["openai", "groq", "anthropic", "google", "ollama", "openrouter"]
DEFAULT_STRATEGIES = ["MacdStrategy", "RSIStrategy", "BollingerStrategy"]
DEFAULT_RESPONSE_FORMATS = ["json"]
RUN_STATE_KEY = "viz_std_backtest_run_state"
RUN_LOG_AUTO_REFRESH_KEY = "std_backtest_run_log_auto_refresh"
RUN_NOTICE_KEY = "std_backtest_run_notice"
ANSI_ESCAPE_RE = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
TRACEBACK_BLOCK_RE = re.compile(r"Traceback \(most recent call last\):[\s\S]*?(?:KeyboardInterrupt|$)")
PY_FATAL_BLOCK_RE = re.compile(r"object address\s*:[\s\S]*?lost sys\.stderr", re.IGNORECASE)
REASONING_BLOCK_RE = re.compile(
    r"={10,}\s*\n={5,}\s*.*?Agent\s*={5,}\s*\n[\s\S]*?\n={10,}",
    re.IGNORECASE,
)
PROGRESS_RE = re.compile(
    r"Backtesting:\s*(?:(?P<pct>\d{1,3})%\|[^\n]*?\|)?\s*(?P<done>\d+)\s*/\s*(?P<total>\d+)[^\n]*?"
    r"Value=\$(?P<value>[+\-]?[\d,\.]+?)\s*,\s*Return=(?P<ret>[+\-]?[\d,\.]+)%",
    re.IGNORECASE,
)
SNAPSHOT_BEFORE_BACKTESTING_RE = re.compile(r"\nBacktesting:\s", re.MULTILINE)
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
YAML_RW = YAML(typ="rt")
YAML_RW.preserve_quotes = True
YAML_RW.indent(mapping=2, sequence=4, offset=2)


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
        return None, "config.yaml root must be a mapping."
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


def _read_log_tail(log_path: Path, max_lines: int = 120) -> str:
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
    return ANSI_ESCAPE_RE.sub("", text).replace("\r", "")


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


def _clean_reasoning_blocks(text: str) -> str:
    """Hide giant agent reasoning JSON blocks from log view."""
    return REASONING_BLOCK_RE.sub("[reasoning block omitted]\n", text)


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
    return metrics


def _extract_latest_portfolio_snapshot(log_text: str, max_lines: int = 56) -> str | None:
    """Last PORTFOLIO SUMMARY block + decision table, up to the next tqdm line."""
    marker = "PORTFOLIO SUMMARY:"
    idx = log_text.rfind(marker)
    if idx < 0:
        return None
    rest = log_text[idx:].lstrip()
    m = SNAPSHOT_BEFORE_BACKTESTING_RE.search(rest)
    if m:
        rest = rest[: m.start()].rstrip()
    lines = rest.splitlines()
    if not lines:
        return None
    if len(lines) > max_lines:
        rest = "\n".join(lines[:max_lines]) + "\n... (truncated for display; see full log tail below)"
    else:
        rest = "\n".join(lines)
    return rest.strip()


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


def _list_run_logs(log_dir: Path) -> list[Path]:
    if not log_dir.is_dir():
        return []
    return sorted(
        log_dir.glob("backtest_streamlit_run_*.log"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def _start_backtest_run(root: Path, cfg_path: Path) -> tuple[dict[str, Any] | None, str | None]:
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = (root / "output" / "backtest" / f"backtest_streamlit_run_{run_id}.log").resolve()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "uv",
        "run",
        "python",
        "-m",
        "trading_dag.cli.backtest",
        "--config",
        str(cfg_path),
        "--mode-override",
        "backtest",
    ]
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
    return {
        "pid": process.pid,
        "pgid": os.getpgid(process.pid),
        "cmd": " ".join(cmd),
        "log_path": str(log_path),
        "started_at": time.time(),
        "stop_requested": False,
        "notified_finished": False,
        "terminal_status": "running",
    }, None


def _stop_run(state: dict[str, Any]) -> str | None:
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
        "Backtest Builder",
        "Edit config.yaml + run",
        "Adjust standard backtest settings in `config/config.yaml`, save, run, and monitor logs in-page.",
    )
    notice = st.session_state.pop(RUN_NOTICE_KEY, None)
    if isinstance(notice, str) and notice.strip():
        st.warning(notice)
        st.toast(notice, icon="🛑")
    cfg_path = (root / CONFIG_PATH_REL).resolve()
    left, right = st.columns([3, 2])
    with left:
        st.caption(f"Config file: `{cfg_path}`")
    with right:
        reload_clicked = st.button("Reload from file", use_container_width=True)

    cfg, load_err = _load_yaml(cfg_path)
    if load_err:
        st.error(f"Could not load config file: {load_err}")
        return
    assert cfg is not None
    if reload_clicked:
        st.rerun()

    initial_positions = cfg.setdefault("initial_positions", {})
    signals_cfg = cfg.setdefault("signals", {})
    model_cfg = cfg.setdefault("model", {})
    output_layout_cfg = cfg.setdefault("output_layout", {})
    risk_cfg = cfg.setdefault("risk", {})

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Main settings</span></div>',
        unsafe_allow_html=True,
    )
    c1, c2, c3 = st.columns(3)
    with c1:
        st.caption("Run mode is fixed to `backtest` on this page.")
        timezone = st.text_input("Timezone", value=str(cfg.get("timezone", "UTC")).strip())
        start_d = st.date_input("Start date", value=_parse_date(cfg.get("start_date")))
        end_d = st.date_input("End date", value=_parse_date(cfg.get("end_date")))
    with c2:
        interval_options = list(dict.fromkeys(DEFAULT_INTERVAL_OPTIONS + [str(cfg.get("primary_interval", "1h"))]))
        primary_interval = st.selectbox(
            "Primary interval",
            interval_options,
            index=max(0, interval_options.index(str(cfg.get("primary_interval", "1h")))),
        )
        initial_cash = st.number_input(
            "Initial cash",
            min_value=0.0,
            step=1000.0,
            value=float(initial_positions.get("cash", 100000.0)),
        )
        margin_requirement = st.number_input(
            "Margin requirement",
            min_value=0.0,
            step=0.01,
            value=float(cfg.get("margin_requirement", 0.0)),
        )
        sync_from_exchange = st.checkbox(
            "Sync from exchange",
            value=bool(cfg.get("sync_from_exchange", False)),
        )
    with c3:
        show_reasoning = st.checkbox("Show reasoning", value=bool(cfg.get("show_reasoning", False)))
        show_graph = st.checkbox("Save workflow graph", value=bool(cfg.get("show_agent_graph", True)))
        enable_logging = st.checkbox("Enable logging", value=bool(cfg.get("enable_logging", True)))
        use_progress_bar = st.checkbox("Use progress bar", value=bool(cfg.get("use_progress_bar", True)))
        save_decision_history = st.checkbox(
            "Save decision history",
            value=bool(cfg.get("save_decision_history", True)),
        )
        auto_cleanup_files = st.checkbox(
            "Auto cleanup files",
            value=bool(cfg.get("auto_cleanup_files", False)),
        )
        print_frequency = st.number_input(
            "Print frequency",
            min_value=1,
            step=1,
            value=int(cfg.get("print_frequency", 1)),
        )
        file_retention_days = st.number_input(
            "File retention days",
            min_value=1,
            step=1,
            value=int(cfg.get("file_retention_days", 30)),
        )
        file_keep_latest = st.number_input(
            "File keep latest",
            min_value=1,
            step=1,
            value=int(cfg.get("file_keep_latest", 10)),
        )

    positions_yaml_default = _dump_yaml_text(initial_positions.get("positions", {}))
    with st.expander("Initial positions map (advanced)", expanded=False):
        positions_yaml = st.text_area(
            "initial_positions.positions (YAML mapping)",
            value=positions_yaml_default if isinstance(positions_yaml_default, str) else "{}\n",
            height=120,
            key="std_initial_positions_yaml",
        )

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Signals & model</span></div>',
        unsafe_allow_html=True,
    )
    s1, s2 = st.columns(2)
    with s1:
        intervals_default = [str(x) for x in _as_list(signals_cfg.get("intervals"))]
        intervals_options = list(dict.fromkeys(DEFAULT_INTERVAL_OPTIONS + intervals_default))
        intervals = st.multiselect("Signal intervals", intervals_options, default=intervals_default)
        tickers = st.text_input(
            "Tickers (comma-separated)",
            value=", ".join(str(x) for x in _as_list(signals_cfg.get("tickers"))),
        )
        strategy_options = list(dict.fromkeys(DEFAULT_STRATEGIES + [str(x) for x in _as_list(signals_cfg.get("strategies"))]))
        strategies = st.multiselect("Strategies", strategy_options, default=[str(x) for x in _as_list(signals_cfg.get("strategies"))])
    with s2:
        provider_options = list(dict.fromkeys(DEFAULT_PROVIDERS + [str(model_cfg.get("provider", "openai"))]))
        model_provider = st.selectbox(
            "Model provider",
            provider_options,
            index=max(0, provider_options.index(str(model_cfg.get("provider", "openai")))),
        )
        model_name = st.text_input("Model name", value=str(model_cfg.get("name", "gpt-4o-mini")))
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

    with st.expander("Advanced: output layout and risk"):
        out1, out2 = st.columns(2)
        with out1:
            output_root = st.text_input("output_layout.root", value=str(output_layout_cfg.get("root", "output")))
            backtest_subdir = st.text_input("output_layout.backtest_subdir", value=str(output_layout_cfg.get("backtest_subdir", "backtest")))
            live_subdir = st.text_input("output_layout.live_subdir", value=str(output_layout_cfg.get("live_subdir", "live")))
        with out2:
            risk_per_trade = st.number_input("risk_per_trade_pct", min_value=0.0, max_value=1.0, step=0.01, value=float(risk_cfg.get("risk_per_trade_pct", 0.02)))
            stop_loss_pct = st.number_input("stop_loss_pct", min_value=0.0, max_value=1.0, step=0.01, value=float(risk_cfg.get("stop_loss_pct", 0.05)))
            min_quantity = st.number_input("min_quantity", min_value=0.0, step=0.001, value=float(risk_cfg.get("min_quantity", 0.001)))
            quantity_decimals = st.number_input("quantity_decimals", min_value=0, max_value=10, step=1, value=int(risk_cfg.get("quantity_decimals", 3)))
            stop_distance_mode = st.selectbox(
                "stop_distance_mode",
                ["entry_or_spot_pct", "atr"],
                index=0 if str(risk_cfg.get("stop_distance_mode", "entry_or_spot_pct")) == "entry_or_spot_pct" else 1,
            )
            atr_period = st.number_input(
                "atr_period",
                min_value=1,
                max_value=500,
                step=1,
                value=int(risk_cfg.get("atr_period", 14)),
            )
            atr_multiplier = st.number_input(
                "atr_multiplier",
                min_value=0.1,
                max_value=10.0,
                step=0.1,
                value=float(risk_cfg.get("atr_multiplier", 1.0)),
            )
            max_notional_fraction = st.number_input(
                "max_notional_fraction_per_ticker",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                value=float(risk_cfg.get("max_notional_fraction_per_ticker", 1.0)),
            )

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Save</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("Save target: `config/config.yaml`")
    save_clicked = st.button("Save config.yaml", type="primary", use_container_width=True)
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

            cfg["timezone"] = timezone.strip() or "UTC"
            cfg["start_date"] = start_d.isoformat()
            cfg["end_date"] = end_d.isoformat()
            cfg["primary_interval"] = primary_interval
            cfg["margin_requirement"] = float(margin_requirement)
            cfg["sync_from_exchange"] = bool(sync_from_exchange)
            cfg["show_reasoning"] = bool(show_reasoning)
            cfg["show_agent_graph"] = bool(show_graph)
            cfg["enable_logging"] = bool(enable_logging)
            cfg["use_progress_bar"] = bool(use_progress_bar)
            cfg["save_decision_history"] = bool(save_decision_history)
            cfg["auto_cleanup_files"] = bool(auto_cleanup_files)
            cfg["print_frequency"] = int(print_frequency)
            cfg["file_retention_days"] = int(file_retention_days)
            cfg["file_keep_latest"] = int(file_keep_latest)

            initial_positions["cash"] = float(initial_cash)
            initial_positions["positions"] = positions_mapping

            signals_cfg["intervals"] = intervals
            signals_cfg["tickers"] = ticker_list
            signals_cfg["strategies"] = strategies

            model_cfg["provider"] = model_provider
            model_cfg["name"] = model_name.strip()
            model_cfg["base_url"] = model_base_url.strip() or None
            model_cfg["temperature"] = float(model_temperature)
            model_cfg["format"] = model_format

            output_layout_cfg["root"] = output_root.strip() or "output"
            output_layout_cfg["backtest_subdir"] = backtest_subdir.strip() or "backtest"
            output_layout_cfg["live_subdir"] = live_subdir.strip() or "live"

            risk_cfg["risk_per_trade_pct"] = float(risk_per_trade)
            risk_cfg["stop_loss_pct"] = float(stop_loss_pct)
            risk_cfg["min_quantity"] = float(min_quantity)
            risk_cfg["quantity_decimals"] = int(quantity_decimals)
            risk_cfg["stop_distance_mode"] = stop_distance_mode
            risk_cfg["atr_period"] = int(atr_period)
            risk_cfg["atr_multiplier"] = float(atr_multiplier)
            risk_cfg["max_notional_fraction_per_ticker"] = float(max_notional_fraction)

            write_err = _write_yaml(cfg_path, cfg)
            if write_err:
                st.error(f"Save failed: {write_err}")
            else:
                st.success("Saved `config/config.yaml`")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Run standard backtest in this page</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("Runs `python -m trading_dag.cli.backtest` in background and streams output below.")

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
                st.warning("Backtest run stopped.")
            elif str(run_state.get("terminal_status", "")).lower() == "failed":
                reason = str(run_state.get("failure_reason", "unknown error"))
                st.error(f"Backtest run failed ({reason}). Check traceback in the log panel.")
            else:
                st.success("Backtest run finished.")
            st.toast("Run status updated", icon="✅")
            run_state["notified_finished"] = True
            st.session_state[RUN_STATE_KEY] = run_state

    c_run, c_stop = st.columns(2)
    with c_run:
        run_clicked = st.button("Run standard backtest", disabled=is_running, use_container_width=True)
    with c_stop:
        stop_clicked = st.button("Stop backtest task", disabled=not is_running, use_container_width=True)

    if run_clicked:
        new_state, start_err = _start_backtest_run(root, cfg_path)
        if start_err:
            st.error(f"Could not start backtest run: {start_err}")
        else:
            st.session_state[RUN_STATE_KEY] = new_state
            st.success(f"Started backtest run (PID {new_state['pid']}).")
            st.rerun()

    if stop_clicked and isinstance(run_state, dict):
        run_state["stop_requested"] = True
        st.session_state[RUN_STATE_KEY] = run_state
        st.session_state[RUN_LOG_AUTO_REFRESH_KEY] = False
        stop_err = _stop_run(run_state)
        if stop_err:
            st.warning(f"Could not stop run: {stop_err}")
        else:
            run_state["finished_at"] = time.time()
            run_state["terminal_status"] = "stopped"
            run_state["notified_finished"] = True
            st.session_state[RUN_STATE_KEY] = run_state
            st.session_state[RUN_NOTICE_KEY] = "Backtest run stopped."
        st.rerun()

    run_state = st.session_state.get(RUN_STATE_KEY)
    running_now = False
    if isinstance(run_state, dict):
        pid_text = run_state.get("pid", "—")
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
        m1, m2 = st.columns(2)
        m1.metric("Status", status)
        m2.metric("PID", str(pid_text))
        st.caption(f"Elapsed: {elapsed:.1f}s")
        st.caption(f"Log file: `{log_path}`")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Backtest run logs</span></div>',
        unsafe_allow_html=True,
    )
    log_dir = (root / "output" / "backtest").resolve()
    log_files = _list_run_logs(log_dir)
    default_log = None
    if isinstance(run_state, dict) and run_state.get("log_path"):
        state_log = Path(str(run_state["log_path"]))
        if state_log.is_file():
            default_log = state_log
    if default_log is None and log_files:
        default_log = log_files[0]

    if not log_files:
        st.caption("No streamlit backtest logs found yet. Start a run above.")
        return

    selected = st.selectbox(
        "Select log file",
        log_files,
        index=log_files.index(default_log) if default_log in log_files else 0,
        format_func=lambda p: p.name,
        key="std_backtest_log_file",
    )
    tail_lines = st.slider(
        "Tail lines",
        min_value=40,
        max_value=1200,
        value=280,
        step=20,
        key="std_backtest_log_tail_lines",
    )
    log_text = _clean_terminal_output(_read_log_tail(selected, max_lines=int(tail_lines)))
    hide_reasoning_blocks = st.checkbox(
        "Optional: hide agent reasoning blocks in tail view (full reasoning stays in log file)",
        value=False,
        key="std_backtest_hide_reasoning_blocks",
        help='When enabled, only the tail code block is shortened. Prefer "Latest portfolio snapshot" for trading tables.',
    )
    if hide_reasoning_blocks:
        log_text = _clean_reasoning_blocks(log_text)

    metrics_source = _clean_terminal_output(_read_log_for_metrics(selected))
    live_metrics = _extract_live_metrics(metrics_source)
    if live_metrics:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Live run metrics</span></div>',
            unsafe_allow_html=True,
        )
        progress_pct = live_metrics.get("progress_pct")
        progress_done = live_metrics.get("progress_done")
        progress_total = live_metrics.get("progress_total")
        if isinstance(progress_pct, int):
            bounded_pct = max(0, min(100, progress_pct))
            progress_label = (
                f"Backtesting progress: {bounded_pct}% ({int(progress_done)}/{int(progress_total)})"
                if isinstance(progress_done, int) and isinstance(progress_total, int)
                else f"Backtesting progress: {bounded_pct}%"
            )
            st.progress(bounded_pct, text=progress_label)

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
            _format_compact_currency(float(live_metrics["progress_value"])) if "progress_value" in live_metrics else "—",
        )
        p3.metric(
            "Live return",
            f"{float(live_metrics['progress_return_pct']):+.2f}%"
            if "progress_return_pct" in live_metrics
            else "—",
        )
        p4.metric(
            "Portfolio total",
            _format_compact_currency(float(live_metrics["portfolio_total"])) if "portfolio_total" in live_metrics else "—",
        )

        q1, q2, q3, q4 = st.columns(4)
        q1.metric(
            "Cash",
            _format_compact_currency(float(live_metrics["portfolio_cash"])) if "portfolio_cash" in live_metrics else "—",
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

    portfolio_snapshot = _extract_latest_portfolio_snapshot(metrics_source)
    snapshot_is_in_tail = bool(portfolio_snapshot and portfolio_snapshot in log_text)
    if portfolio_snapshot and not snapshot_is_in_tail:
        with st.expander("Latest portfolio snapshot (from full log)", expanded=True):
            st.caption(
                "Taken from the log: last PORTFOLIO SUMMARY through the decision table "
                "(cut before the next Backtesting: line)."
            )
            st.code(portfolio_snapshot, language="text")
    elif portfolio_snapshot and snapshot_is_in_tail:
        st.caption("Latest portfolio snapshot is already visible in the current tail window.")

    auto_height = st.checkbox(
        "Auto-fit log window height",
        value=True,
        key="std_backtest_log_auto_height",
        help="Use an adaptive panel height based on current tail length.",
    )
    manual_height = st.slider(
        "Manual log height (px)",
        min_value=220,
        max_value=1200,
        value=560,
        step=20,
        disabled=auto_height,
        key="std_backtest_log_height_px",
    )
    log_height = _estimate_log_view_height(log_text) if auto_height else int(manual_height)
    st.caption(f"Log panel height: {log_height}px")
    st.code(log_text, language="text", height=log_height)

    auto_refresh = st.checkbox(
        "Live tail (auto refresh every 2s)",
        value=bool(st.session_state.get(RUN_LOG_AUTO_REFRESH_KEY, True)),
        key=RUN_LOG_AUTO_REFRESH_KEY,
    )
    if auto_refresh and running_now:
        st.caption("Live tail is on. Refreshing logs every 2 seconds...")
        time.sleep(2)
        st.rerun()
