"""
Streamlit UI entry (thin wrapper).

Run from repo root::
    uv run streamlit run src/trading_dag/viz/streamlit_app.py

Implementation modules live under ``trading_dag.viz``.
"""
from trading_dag.viz.app import main

if __name__ == "__main__":
    main()
