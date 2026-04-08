"""Setup & API screen."""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import streamlit as st
from ruamel.yaml import YAML

from trading_dag.llm import llm as llm_module
from trading_dag.viz.helpers import _page_header, project_root

ENV_PATH = project_root() / ".env"
CONFIG_PATH = project_root() / "config" / "config.yaml"
YAML_RW = YAML(typ="safe")
ENV_KEY_PATTERN = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)$")
ENV_KEY_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
LLM_PROVIDER_KEY_MAP = {
    "openai": "OPENAI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "gemini": "GOOGLE_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "ollama": "",
}
# Written by this page; not secret values — excluded from key preview tables and key manager lists.
ENV_RUNTIME_MARKER_KEYS = frozenset({"ACTIVE_LLM_KEY_SOURCE"})

get_llm = llm_module.get_llm


def _set_flash_message(level: str, message: str) -> None:
    st.session_state["setup_flash_message"] = {"level": level, "message": message}


def _render_flash_message() -> None:
    payload = st.session_state.pop("setup_flash_message", None)
    if not isinstance(payload, dict):
        return
    level = str(payload.get("level", "info")).strip().lower()
    message = str(payload.get("message", "")).strip()
    if not message:
        return
    if level == "success":
        st.success(message)
    elif level == "error":
        st.error(message)
    elif level == "warning":
        st.warning(message)
    else:
        st.info(message)


def _clear_llm_cache_safe() -> None:
    """Clear LLM cache across old/new module layouts without import-time breakage."""
    clear_fn = getattr(llm_module, "clear_llm_cache", None)
    if callable(clear_fn):
        clear_fn()
        return
    legacy_clear = getattr(get_llm, "cache_clear", None)
    if callable(legacy_clear):
        legacy_clear()


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


def _apply_process_env(updates: dict[str, str]) -> None:
    """Expose `.env` writes to this process so ``os.getenv`` matches the file (overrides shell defaults)."""
    for name, value in updates.items():
        os.environ[name] = value


def _pop_process_env(names: set[str]) -> None:
    for name in names:
        os.environ.pop(name, None)


def _delete_env_keys(path: Path, keys: set[str]) -> None:
    if not keys:
        return
    existing_lines = path.read_text(encoding="utf-8", errors="replace").splitlines() if path.is_file() else []
    kept: list[str] = []
    for line in existing_lines:
        m = ENV_KEY_PATTERN.match(line)
        if not m:
            kept.append(line)
            continue
        key = m.group(1).strip()
        if key not in keys:
            kept.append(line)
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "\n".join(kept).rstrip()
    path.write_text((text + "\n") if text else "", encoding="utf-8")


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


def _llm_cache_key_names() -> set[str]:
    return {v for v in LLM_PROVIDER_KEY_MAP.values() if v}


def _touch_affects_llm(names: set[str]) -> bool:
    llm_keys = _llm_cache_key_names()
    if names & llm_keys:
        return True
    return any(
        n.endswith("_API_KEY") and n not in {"BINANCE_API_KEY"} and n not in ENV_RUNTIME_MARKER_KEYS
        for n in names
    )


def render() -> None:
    _page_header(
        "Setup & API",
        "Exchange and LLM credentials",
        "Configure `.env` credentials used by CLI/backtest/live runners. Keys are stored locally on this machine.",
    )
    st.info(
        "Use testnet keys where possible. For exchange keys, keep trading-only permission and disable withdrawal."
    )
    _render_flash_message()

    env_values = _read_env(ENV_PATH)
    model_cfg = _load_model_config(CONFIG_PATH)
    cfg_provider = str(model_cfg.get("provider", "openai")).strip().lower() or "openai"
    cfg_model = str(model_cfg.get("name", "gpt-4o-mini")).strip() or "gpt-4o-mini"
    cfg_base_url = model_cfg.get("base_url")
    cfg_base_url = str(cfg_base_url).strip() if cfg_base_url is not None else None

    st.caption(f"Local env file path: `{ENV_PATH}`")
    st.caption("All add/edit/delete actions in this page write directly to that local `.env` file.")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Binance API</span></div>',
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
                    blob = {
                        "BINANCE_API_KEY": ex_key.strip(),
                        "BINANCE_API_SECRET": ex_secret.strip(),
                    }
                    _write_env_updates(ENV_PATH, blob)
                    _apply_process_env(blob)
                    _set_flash_message(
                        "success",
                        f"Saved exchange credentials to `{ENV_PATH}` and applied them to this process.",
                    )
                    st.rerun()
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
        active_source_key = env_values.get("ACTIVE_LLM_KEY_SOURCE", "").strip()
        llm_key = st.text_input(
            f"{llm_env_key or 'No API key required'}",
            value=current_llm_key,
            type="password",
            key="setup_llm_api_key",
            disabled=not bool(llm_env_key),
            help=f"Current: {_mask_secret(current_llm_key)}" if llm_env_key else "Ollama does not require a cloud API key.",
        )
        st.caption(f"Model from config: `{cfg_model}`")

        key_source_options = [
            k
            for k in sorted(env_values.keys())
            if k.endswith("_API_KEY") and k not in ENV_RUNTIME_MARKER_KEYS and k != "BINANCE_API_KEY"
        ]
        if llm_env_key and llm_env_key not in key_source_options:
            key_source_options.insert(0, llm_env_key)
        selected_source_idx = 0
        if active_source_key in key_source_options:
            selected_source_idx = key_source_options.index(active_source_key)
        elif llm_env_key and llm_env_key in key_source_options:
            selected_source_idx = key_source_options.index(llm_env_key)
        selected_source_key = st.selectbox(
            "Key source used for runtime",
            options=key_source_options if key_source_options else ["(no *_API_KEY found)"],
            index=selected_source_idx if key_source_options else 0,
            disabled=not bool(key_source_options) or not bool(llm_env_key),
            key="setup_llm_runtime_key_source",
            help="Selected key value will be copied to the provider runtime key in `.env`.",
        )
        selected_source_value = env_values.get(selected_source_key, "").strip() if key_source_options else ""
        if llm_env_key and key_source_options:
            st.caption(
                f"Runtime target: `{llm_env_key}` <= `{selected_source_key}` "
                f"(preview: `{_mask_secret(selected_source_value)}`)"
            )
            if not selected_source_value:
                st.warning("Selected runtime key source is empty. Fill that key first, then apply.")
        elif not llm_env_key:
            st.caption("Provider `ollama` does not require runtime API-key mapping.")
        llm_col1, llm_col2, llm_col3 = st.columns(3)
        with llm_col1:
            if st.button("Save LLM key", use_container_width=True):
                if not llm_env_key:
                    st.info("No key save needed for provider `ollama`.")
                elif not llm_key.strip():
                    st.error(f"{llm_env_key} cannot be empty.")
                else:
                    blob = {llm_env_key: llm_key.strip()}
                    _write_env_updates(ENV_PATH, blob)
                    _apply_process_env(blob)
                    _clear_llm_cache_safe()
                    _set_flash_message(
                        "success",
                        f"Saved {llm_env_key} to `{ENV_PATH}` and applied it to this process (overrides shell for this app)."
                    )
                    st.rerun()
        with llm_col2:
            disable_apply_runtime = not llm_env_key or not bool(key_source_options) or not bool(selected_source_value)
            if st.button("Apply runtime LLM selection", use_container_width=True, disabled=disable_apply_runtime):
                if not llm_env_key:
                    blob = {"ACTIVE_LLM_KEY_SOURCE": ""}
                    _write_env_updates(ENV_PATH, blob)
                    _apply_process_env(blob)
                    _set_flash_message("success", "Saved runtime key source marker for `ollama`.")
                    st.rerun()
                elif not key_source_options:
                    st.error("No API key candidates found. Add at least one `*_API_KEY` key first.")
                else:
                    source_key = selected_source_key
                    source_val = env_values.get(source_key, "")
                    if not source_val.strip():
                        st.error(f"Selected source key `{source_key}` is empty.")
                    else:
                        blob = {
                            llm_env_key: source_val.strip(),
                            "ACTIVE_LLM_KEY_SOURCE": source_key,
                        }
                        _write_env_updates(ENV_PATH, blob)
                        _apply_process_env(blob)
                        _clear_llm_cache_safe()
                        _set_flash_message(
                            "success",
                            f"Runtime LLM updated: provider `{llm_provider}`, "
                            f"`{llm_env_key}` now follows `{source_key}` (also applied to this process)."
                        )
                        st.rerun()
        with llm_col3:
            if st.button("Test LLM client setup", use_container_width=True):
                proc_llm_secret = (os.getenv(llm_env_key) or "").strip() if llm_env_key else ""
                from_file = (current_llm_key or "").strip()
                from_widget = (llm_key or "").strip()
                effective_secret = from_widget or from_file or proc_llm_secret
                if llm_env_key and not effective_secret:
                    st.error(
                        f"No value for {llm_env_key} in this page, in `{ENV_PATH}`, or in the process environment."
                    )
                else:
                    try:
                        # Builds the client only; providers usually do not validate the key until the first API call.
                        # Widget > file > shell so an unsaved new key still wins over a stale shell export.
                        if llm_env_key:
                            _apply_process_env({llm_env_key: effective_secret})
                            _clear_llm_cache_safe()
                        _ = get_llm(
                            provider=llm_provider,
                            model=cfg_model,
                            base_url=cfg_base_url,
                            temperature=0.0,
                        )
                        st.success(
                            "LLM client object built successfully (no API call; key not verified with the provider)."
                        )
                        if llm_env_key and from_widget:
                            st.info(
                                "This test applied the text box value to **this Streamlit process** "
                                f"(`{llm_env_key}`). Save if you also want it in `.env`."
                            )
                        elif llm_env_key and not from_file and not from_widget and proc_llm_secret:
                            st.warning(
                                f"`{llm_env_key}` is set in the **process environment** (shell, IDE, or parent "
                                f"process), not in `{ENV_PATH}`. Runs use `os.environ` after `load_dotenv()`, so "
                                f"they can still work without a project `.env` line."
                            )
                    except Exception as exc:
                        st.error(f"LLM client test failed: {exc}")

    st.markdown('<div class="viz-panel-title"><span></span><span>Key manager</span></div>', unsafe_allow_html=True)
    existing_keys = sorted(k for k in env_values.keys() if k not in ENV_RUNTIME_MARKER_KEYS)
    editor_col1, editor_col2, editor_col3 = st.columns(3)
    with editor_col1:
        edit_target = st.selectbox(
            "Select key to edit",
            options=existing_keys if existing_keys else ["(no keys found)"],
            index=0,
            disabled=not bool(existing_keys),
            key="setup_env_edit_target",
        )
        current_val = env_values.get(edit_target, "") if edit_target in env_values else ""
        edit_value = st.text_input(
            "New value for selected key",
            value=current_val,
            type="password",
            disabled=not bool(existing_keys),
            key="setup_env_edit_value",
        )
        if st.button("Update selected key", use_container_width=True, disabled=not bool(existing_keys)):
            if edit_target in env_values:
                _write_env_updates(ENV_PATH, {edit_target: edit_value})
                _apply_process_env({edit_target: edit_value})
                if _touch_affects_llm({edit_target}):
                    _clear_llm_cache_safe()
                _set_flash_message(
                    "success", f"Updated `{edit_target}` in `{ENV_PATH}` and applied it to this process."
                )
                st.rerun()

    with editor_col2:
        new_key_name = st.text_input(
            "New key name",
            value="",
            key="setup_env_new_key_name",
            help="Example: CUSTOM_PROVIDER_API_KEY",
        ).strip()
        new_key_value = st.text_input(
            "New key value",
            value="",
            type="password",
            key="setup_env_new_key_value",
        )
        if st.button("Add new key", use_container_width=True):
            if not new_key_name:
                st.error("Key name is required.")
            elif not ENV_KEY_NAME_PATTERN.match(new_key_name):
                st.error("Invalid key name. Use letters, numbers, and underscores; do not start with a number.")
            else:
                _write_env_updates(ENV_PATH, {new_key_name: new_key_value})
                _apply_process_env({new_key_name: new_key_value})
                if _touch_affects_llm({new_key_name}):
                    _clear_llm_cache_safe()
                _set_flash_message(
                    "success", f"Added/updated `{new_key_name}` in `{ENV_PATH}` and applied it to this process."
                )
                st.rerun()

    with editor_col3:
        delete_targets = st.multiselect(
            "Delete key(s)",
            options=existing_keys,
            default=[],
            key="setup_env_delete_targets",
        )
        if st.button("Delete selected key(s)", use_container_width=True, disabled=not bool(delete_targets)):
            dt = set(delete_targets)
            _delete_env_keys(ENV_PATH, dt)
            _pop_process_env(dt)
            if _touch_affects_llm(dt):
                _clear_llm_cache_safe()
            _set_flash_message(
                "success",
                f"Deleted {len(delete_targets)} key(s) from `{ENV_PATH}` and removed them from this process.",
            )
            st.rerun()

    env_values = _read_env(ENV_PATH)
    active_source_key = env_values.get("ACTIVE_LLM_KEY_SOURCE", "").strip() or (
        os.getenv("ACTIVE_LLM_KEY_SOURCE", "").strip()
    )

    def _preview_row(k: str) -> dict[str, str]:
        return {"key": k, "preview": _mask_secret(env_values.get(k, ""))}

    exchange_order = ["BINANCE_API_KEY", "BINANCE_API_SECRET"]
    exchange_rows = [_preview_row(k) for k in exchange_order if k in env_values]

    llm_key_names = sorted(
        k
        for k in env_values
        if k.endswith("_API_KEY")
        and k not in ENV_RUNTIME_MARKER_KEYS
        and k != "BINANCE_API_KEY"
    )
    llm_rows = [_preview_row(k) for k in llm_key_names]

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Binance API keys (from local .env)</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("Runs use `BINANCE_API_KEY` and `BINANCE_API_SECRET` from this file.")
    if exchange_rows:
        st.dataframe(exchange_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No Binance API keys found in `.env`.")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>Runtime LLM selection (from local .env)</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("This is a non-secret marker: which key name the UI last applied for runtime.")
    st.markdown(f"`ACTIVE_LLM_KEY_SOURCE`: `{active_source_key or '(not set)'}`")

    st.markdown(
        '<div class="viz-panel-title"><span></span><span>LLM API keys (from local .env)</span></div>',
        unsafe_allow_html=True,
    )
    st.caption("Masked values only; `ACTIVE_LLM_*` rows are omitted here.")
    if llm_rows:
        st.dataframe(llm_rows, use_container_width=True, hide_index=True)
    else:
        st.info("No LLM API keys found in `.env`.")

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
