"""Setup & API screen."""
import streamlit as st

from trading_dag.viz.helpers import _page_header


def render() -> None:
    _page_header(
        "Security & privacy",
        "Exchange & LLM credentials",
        "The desktop prototype collects keys in-session. **This lab app does not persist secrets.** "
        "Use `.env` / your exchange config for real runs.",
    )
    st.info(
        "Please use **testnet** API keys where possible; simulation is the default—no live orders "
        "from this dashboard."
    )
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>Exchange account (Binance)</span></div>',
            unsafe_allow_html=True,
        )
        st.text_input("API Key", value="", type="default", key="ex_key", disabled=True)
        st.text_input("API Secret", value="", type="password", key="ex_sec", disabled=True)
        st.caption("Enable inputs only after wiring session-secure storage; defaults are disabled.")
        st.button("Save", key="ex_save", disabled=True)
        st.button("Test", key="ex_test", disabled=True)
    with c2:
        st.markdown(
            '<div class="viz-panel-title"><span></span><span>LLM API</span></div>',
            unsafe_allow_html=True,
        )
        st.text_input("API Key ", value="", type="default", key="llm_key", disabled=True)
        st.text_input("API Secret ", value="", type="password", key="llm_sec", disabled=True)
        st.button("Save ", key="llm_save", disabled=True)
        st.button("Test ", key="llm_test", disabled=True)
    with st.expander("Security & privacy (copy from prototype)"):
        st.markdown(
            """
- API secrets are not kept in plain text in the browser long-term; they are only used for the session.
- Default is testnet / simulation—no real trading.
- Live mode should require explicit confirmation and additional verification.
- Use API keys with trading permissions only; disable withdrawal.
- Rotate keys regularly.
            """
        )
