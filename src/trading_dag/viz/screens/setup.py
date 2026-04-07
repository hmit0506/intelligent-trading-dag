"""Setup & API screen."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import streamlit as st
from ruamel.yaml import YAML

from trading_dag.llm.llm import get_llm
from trading_dag.viz.helpers import _page_header, project_root

ENV_PATH = project_root() / ".env"
CONFIG_PATH = project_root() / "config" / "config.yaml"
YAML_RW = YAML(typ="safe")
ENV_KEY_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
LLM_PROVIDER_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "",
}


def _mask_secret(value: str) -> str:
    if not value:
        return "(empty)"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


def _read_env(path: Path) -> dict[str, str]:
    if not path.is_file():
        return {}
    data: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = ENV_KEY_PATTERN.match(line)
        if not m:
            continue
        key = m.group(1).strip()
        raw_val = m.group(2).strip()
        if (raw_val.startswith('"') and raw_val.endswith('"')) or (raw_val.startswith("'") and raw_val.endswith("'")):
            raw_val = raw_val[1:-1]
        data[key] = raw_val
    return data


def _quote_env_value(value: str) -> str:
    if not value:
        return '""'
    if any(ch in value for ch in [" ", "#", '"', "'"]):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def _write_env_updates(path: Path, updates: dict[str, str]) -> None:
    existing_lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []
    key_to_line_idx: dict[str, int] = {}
    for idx, line in enumerate(existing_lines):
        m = ENV_KEY_PATTERN.match(line)
        if m:
            key_to_line_idx[m.group(1).strip()] = idx

    lines = list(existing_lines)
    for key, value in updates.items():
        rendered = f"{key}={_quote_env_value(value)}"
        if key in key_to_line_idx:
            lines[key_to_line_idx[key]] = rendered
        else:
            lines.append(rendered)

    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(lines).rstrip() + "\n"
    path.write_text(text, encoding="utf-8")


def _load_model_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        cfg = YAML_RW.load(path.read_text(encoding="utf-8", errors="replace")) or {}
    except Exception:
        return {}
    if not isinstance(cfg, dict):
        return {}
    model = cfg.get("model", {})
    return model if isinstance(model, dict) else {}


def render() -> None:
    _page_header(
        "Setup & API",
        "Exchange and LLM credentials",
        "Configure `.env` credentials used by CLI/backtest/live runners. Keys are stored locally on this machine.",
    )
    st.info(
        "Use testnet keys where possible. For exchange keys, keep trading-only permission and disable withdrawal."
    )

    env_values = _read_env(ENV_PATH)
    model_cfg = _load_model_config(CONFIG_PATH)
    cfg_provider = str(model_cfg.get("provider", "openai")).strip().lower() or "openai"
    cfg_model = str(model_cfg.get("name", "gpt-4o-mini")).strip() or "gpt-4o-mini"
    cfg_base_url = model_cfg.get("base_url")
    cfg_base_url = str(cfg_base_url).strip() if cfg_base_url is not None else None

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Exchange account (Binance)</span></div>',
            unsafe_allow_html=True,
        )
        default_ex_key = env_values.get("BINANCE_API_KEY", "")
        default_ex_secret = env_values.get("BINANCE_API_SECRET", "")
        ex_key = st.text_input(
            "BINANCE_API_KEY",
            value=default_ex_key,
            type="password",
            key="setup_binance_api_key",
            help=f"Current: {_mask_secret(default_ex_key)}",
        )
        ex_secret = st.text_input(
            "BINANCE_API_SECRET",
            value=default_ex_secret,
            type="password",
            key="setup_binance_api_secret",
            help=f"Current: {_mask_secret(default_ex_secret)}",
        )
        ex_col1, ex_col2 = st.columns(2)
        with ex_col1:
            if st.button("Save exchange keys", use_container_width=True):
                if not ex_key.strip() or not ex_secret.strip():
                    st.error("Both BINANCE_API_KEY and BINANCE_API_SECRET are required.")
                else:
                    _write_env_updates(
                        ENV_PATH,
                        {
                            "BINANCE_API_KEY": ex_key.strip(),
                            "BINANCE_API_SECRET": ex_secret.strip(),
                        },
                    )
                    st.success(f"Saved exchange credentials to `{ENV_PATH}`.")
        with ex_col2:
            if st.button("Test exchange connectivity", use_container_width=True):
                test_key = ex_key.strip() or default_ex_key.strip()
                test_secret = ex_secret.strip() or default_ex_secret.strip()
                if not test_key or not test_secret:
                    st.error("Set BINANCE_API_KEY and BINANCE_API_SECRET first.")
                else:
                    try:
                        from trading_dag.gateway.binance.client import Client

                        client = Client(api_key=test_key, api_secret=test_secret)
                        _ = client.get_server_time()
                        st.success("Exchange API connectivity test passed.")
                    except Exception as exc:
                        st.error(f"Exchange API test failed: {exc}")

    with c2:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>LLM API</span></div>',
            unsafe_allow_html=True,
        )
        provider_options = list(LLM_PROVIDER_KEY_MAP.keys())
        provider_idx = provider_options.index(cfg_provider) if cfg_provider in provider_options else 0
        llm_provider = st.selectbox(
            "Provider",
            provider_options,
            index=provider_idx,
            key="setup_llm_provider",
            help=f"Default from config.yaml: {cfg_provider}",
        )
        llm_env_key = LLM_PROVIDER_KEY_MAP[llm_provider]
        current_llm_key = env_values.get(llm_env_key, "") if llm_env_key else ""
        llm_key = st.text_input(
            f"{llm_env_key or 'No API key required'}",
            value=current_llm_key,
            type="password",
            key="setup_llm_api_key",
            disabled=not bool(llm_env_key),
            help=f"Current: {_mask_secret(current_llm_key)}" if llm_env_key else "Ollama does not require a cloud API key.",
        )
        st.caption(f"Model from config: `{cfg_model}`")
        llm_col1, llm_col2 = st.columns(2)
        with llm_col1:
            if st.button("Save LLM key", use_container_width=True):
                if not llm_env_key:
                    st.info("No key save needed for provider `ollama`.")
                elif not llm_key.strip():
                    st.error(f"{llm_env_key} cannot be empty.")
                else:
                    _write_env_updates(ENV_PATH, {llm_env_key: llm_key.strip()})
                    st.success(f"Saved {llm_env_key} to `{ENV_PATH}`.")
        with llm_col2:
            if st.button("Test LLM client setup", use_container_width=True):
                if llm_env_key and not (llm_key.strip() or current_llm_key.strip()):
                    st.error(f"Set {llm_env_key} first.")
                else:
                    try:
                        # Dry-run object build to validate provider/model/base_url configuration.
                        get_llm.cache_clear()
                        _ = get_llm(
                            provider=llm_provider,
                            model=cfg_model,
                            base_url=cfg_base_url,
                            temperature=0.0,
                        )
                        st.success("LLM client initialization test passed.")
                    except Exception as exc:
                        st.error(f"LLM client test failed: {exc}")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Environment key status</span></div>',
        unsafe_allow_html=True,
    )
    status_rows = []
    for key in [
        "BINANCE_API_KEY",
        "BINANCE_API_SECRET",
        "OPENAI_API_KEY",
        "GROQ_API_KEY",
        "OPENROUTER_API_KEY",
        "GOOGLE_API_KEY",
        "ANTHROPIC_API_KEY",
    ]:
        val = env_values.get(key, "")
        status_rows.append({"key": key, "configured": bool(val), "preview": _mask_secret(val)})
    st.dataframe(status_rows, use_container_width=True, hide_index=True)

    with st.expander("Security notes"):
        st.markdown(
            """
- This page writes credentials into local `.env` only.
- Avoid sharing terminal logs/screenshots containing full keys.
- Prefer testnet keys for exchange operations.
- Use least-privilege API keys; disable withdrawal on exchange keys.
- Rotate API keys regularly.
            """
        )
