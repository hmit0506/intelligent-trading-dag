"""Live mode decision dumps (``output/<live_subdir>/``)."""
from pathlib import Path

import json
import streamlit as st

from trading_dag.viz.helpers import _page_header, _preview_json, list_live_decision_jsons


def render(live_dir: Path) -> None:
    paths = list_live_decision_jsons(live_dir)

    _page_header(
        "Live mode",
        "Decision history files",
        "JSON snapshots from `TradingSystemRunner` when `save_decision_history` is enabled "
        "(`live_decisions_*.json` under the **live** subfolder).",
    )
    st.metric("Decision JSON files", len(paths))
    if not paths:
        st.info("No `live_decisions_*.json` in the live folder. Run live mode or check `output_layout` paths.")
        return

    choice = st.selectbox(
        "Snapshot",
        paths,
        format_func=lambda p: p.name,
        key="live_dec_json",
    )
    try:
        raw = Path(choice).read_text(encoding="utf-8")
        data = json.loads(raw)
        st.json(data if isinstance(data, (dict, list)) else {"_": data})
        with st.expander("Raw text"):
            st.code(raw[:48000] + ("…" if len(raw) > 48000 else ""), language="json")
    except json.JSONDecodeError:
        st.code(_preview_json(Path(choice)), language="json")
    except Exception as exc:
        st.warning(str(exc))
