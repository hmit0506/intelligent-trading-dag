"""Streamlit theme (CSS)."""
import streamlit as st


def inject_theme_css() -> None:
    """Inject design tokens derived from the FYP Prototype PDF export."""
    THEME = {
        "bg": "#e8edf5",
        "surface": "#c8dcf2",
        "surface_card": "#f5f8fd",
        "surface_alt": "#a8bcd4",
        "text": "#1c2230",
        "muted": "#5a6578",
        "accent": "#0048f0",
        "accent_soft": "#3078f0",
        "success": "#18a838",
        "danger": "#d82020",
        "button_bg": "#2a3344",
        "button_bg_hover": "#3d4a5f",
        "button_text": "#ffffff",
        "button_border": "rgba(28, 34, 48, 0.22)",
        "font_ui": "'IBM Plex Sans', 'Segoe UI', sans-serif",
        "font_mono": "'IBM Plex Mono', 'Consolas', monospace",
        "radius": "8px",
    }
    st.markdown(
        """
        <link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@400;600&display=swap" rel="stylesheet">
        """,
        unsafe_allow_html=True,
    )
    st.markdown(
        f"""
        <style>
            :root {{
                --viz-bg: {THEME["bg"]};
                --viz-surface: {THEME["surface"]};
                --viz-surface-card: {THEME["surface_card"]};
                --viz-surface-alt: {THEME["surface_alt"]};
                --viz-text: {THEME["text"]};
                --viz-muted: {THEME["muted"]};
                --viz-accent: {THEME["accent"]};
                --viz-accent-soft: {THEME["accent_soft"]};
                --viz-success: {THEME["success"]};
                --viz-danger: {THEME["danger"]};
                --viz-button-bg: {THEME["button_bg"]};
                --viz-button-bg-hover: {THEME["button_bg_hover"]};
                --viz-button-text: {THEME["button_text"]};
                --viz-button-border: {THEME["button_border"]};
                --viz-font-ui: {THEME["font_ui"]};
                --viz-font-mono: {THEME["font_mono"]};
                --viz-radius: {THEME["radius"]};
            }}
            html, body, [data-testid="stAppViewContainer"] {{
                background-color: var(--viz-bg) !important;
                color: var(--viz-text);
                font-family: var(--viz-font-ui);
            }}
            [data-testid="stSidebar"] {{
                background-color: var(--viz-surface-card) !important;
                border-right: 1px solid var(--viz-surface-alt);
                color: var(--viz-text) !important;
            }}
            h1, h2, h3 {{ color: var(--viz-text) !important; font-weight: 600; letter-spacing: -0.02em; }}
            [data-testid="stMarkdownContainer"] p {{ color: var(--viz-muted); }}
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] span,
            [data-testid="stMarkdownContainer"] label {{
                color: var(--viz-text) !important;
            }}
            .stRadio label, .stCheckbox label, .stSelectbox label, .stTextInput label,
            .stMultiSelect label, .stDateInput label {{ color: var(--viz-text) !important; }}
            [data-baseweb="select"] *,
            [data-baseweb="popover"] *,
            [role="listbox"] *,
            [role="option"] *,
            .stSelectbox div,
            .stMultiSelect div {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stMetricValue"] {{ color: var(--viz-accent) !important; }}
            [data-testid="stMarkdownContainer"] a {{ color: var(--viz-accent); }}
            div[data-baseweb="tab-list"] button {{
                font-family: var(--viz-font-ui);
                color: var(--viz-text) !important;
            }}
            div[data-baseweb="tab-list"] button[aria-selected="true"] {{
                color: var(--viz-accent) !important;
                font-weight: 600;
            }}
            .stButton > button {{
                background-color: var(--viz-button-bg) !important;
                color: var(--viz-button-text) !important;
                border: 1px solid var(--viz-button-border) !important;
                border-radius: var(--viz-radius);
                font-weight: 600;
                box-shadow: 0 1px 2px rgba(28, 34, 48, 0.06);
            }}
            .stButton > button *,
            .stButton > button span,
            .stButton > button p,
            .stButton > button div {{
                color: var(--viz-button-text) !important;
            }}
            .stButton > button:hover,
            .stButton > button:hover * {{
                color: var(--viz-button-text) !important;
            }}
            .stButton > button:hover {{
                background-color: var(--viz-button-bg-hover) !important;
                border-color: rgba(28, 34, 48, 0.28) !important;
            }}
            .stButton > button:focus-visible {{
                outline: 2px solid var(--viz-accent-soft);
                outline-offset: 2px;
            }}
            [data-testid="stMetricContainer"] {{
                background: var(--viz-surface-card) !important;
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                padding: 0.75rem 1rem;
            }}
            [data-testid="stMetricLabel"] {{ color: var(--viz-muted) !important; }}
            div[data-testid="stTabs"] [data-baseweb="tab-panel"] {{ padding-top: 1rem; }}
            .viz-page-title {{
                margin: 0 0 0.25rem 0;
                font-size: 1.65rem;
                font-weight: 600;
                color: var(--viz-text);
            }}
            .viz-kicker {{
                color: var(--viz-accent);
                font-size: 0.68rem;
                font-weight: 600;
                letter-spacing: 0.12em;
                text-transform: uppercase;
                margin-bottom: 0.35rem;
            }}
            .viz-panel-title {{
                display: flex;
                align-items: center;
                gap: 0.6rem;
                margin: 1rem 0 0.75rem 0;
                padding-bottom: 0.45rem;
                border-bottom: 1px solid var(--viz-surface-alt);
            }}
            .viz-panel-title span:first-child {{
                width: 3px;
                height: 1.05rem;
                border-radius: 2px;
                background: var(--viz-accent);
            }}
            .viz-panel-title span:last-child {{
                color: var(--viz-text);
                font-weight: 600;
                font-size: 1.02rem;
            }}
            .viz-banner {{
                background: linear-gradient(90deg, var(--viz-surface) 0%, var(--viz-surface-card) 100%);
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                padding: 0.85rem 1.1rem;
                margin-bottom: 1rem;
                color: var(--viz-text);
            }}
            .viz-banner strong {{ color: var(--viz-accent); }}
            [data-testid="stDataFrame"] {{
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                background: var(--viz-surface-card);
                padding: 0.35rem;
            }}
            [data-testid="stDataFrame"] * {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stPlotlyChart"] {{
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                background: var(--viz-surface-card);
                padding: 0.5rem;
            }}
            [data-testid="stImage"] {{
                border: 1px solid var(--viz-surface-alt);
                border-radius: var(--viz-radius);
                background: var(--viz-surface-card);
                padding: 0.5rem;
            }}
            [data-testid="stImage"] figcaption,
            [data-testid="stImage"] [data-testid="stCaption"],
            [data-testid="stImage"] p {{
                color: var(--viz-text) !important;
            }}
            /* Code/JSON: force high-contrast light panel + dark text. */
            [data-testid="stCodeBlock"],
            [data-testid="stCode"],
            [data-testid="stJson"] {{
                background: var(--viz-surface-card) !important;
                border: 1px solid var(--viz-surface-alt) !important;
                border-radius: var(--viz-radius) !important;
            }}
            [data-testid="stCodeBlock"] pre,
            [data-testid="stCode"] pre {{
                background: var(--viz-surface-card) !important;
                color: var(--viz-text) !important;
            }}
            [data-testid="stCodeBlock"] code,
            [data-testid="stCode"] code,
            [data-testid="stCodeBlock"] span,
            [data-testid="stCode"] span,
            [data-testid="stJson"] span,
            [data-testid="stJson"] code,
            [data-testid="stJson"] pre {{
                color: var(--viz-text) !important;
                -webkit-text-fill-color: var(--viz-text) !important;
            }}
            [data-testid="stJson"] *,
            [data-testid="stText"] *,
            [data-testid="stAlert"] *,
            [data-testid="stExpander"] * {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stCaption"],
            [data-testid="stCaption"] *,
            .stCaption,
            .stCaption * {{
                color: var(--viz-muted) !important;
            }}
            [data-testid="stFileUploader"] *,
            [data-testid="stTextInput"] *,
            [data-testid="stTextArea"] *,
            [data-testid="stNumberInput"] *,
            [data-testid="stSlider"] * {{
                color: var(--viz-text) !important;
            }}
            /* Select/input controls: avoid dark bg + dark text combos. */
            [data-baseweb="select"] > div,
            [data-baseweb="input"] > div,
            [data-baseweb="textarea"] > div {{
                background: var(--viz-surface-card) !important;
                border-color: var(--viz-surface-alt) !important;
            }}
            [data-baseweb="select"] input,
            [data-baseweb="input"] input,
            [data-baseweb="textarea"] textarea,
            [data-baseweb="select"] [role="combobox"],
            [data-baseweb="select"] [role="combobox"] * {{
                color: var(--viz-text) !important;
                -webkit-text-fill-color: var(--viz-text) !important;
            }}
            /* NumberInput stepper (+/-): keep strong foreground contrast. */
            [data-testid="stNumberInput"] button {{
                background-color: var(--viz-button-bg) !important;
                color: var(--viz-button-text) !important;
                border-color: var(--viz-button-border) !important;
            }}
            [data-testid="stNumberInput"] button:hover {{
                background-color: var(--viz-button-bg-hover) !important;
            }}
            [data-testid="stNumberInput"] button *,
            [data-testid="stNumberInput"] button span,
            [data-testid="stNumberInput"] button div {{
                color: var(--viz-button-text) !important;
                -webkit-text-fill-color: var(--viz-button-text) !important;
            }}
            [data-testid="stNumberInput"] button svg,
            [data-testid="stNumberInput"] button svg path {{
                fill: var(--viz-button-text) !important;
                stroke: var(--viz-button-text) !important;
            }}
            /* Plotly labels/ticks: force dark text on light chart background. */
            [data-testid="stPlotlyChart"] svg text,
            [data-testid="stPlotlyChart"] .xtick text,
            [data-testid="stPlotlyChart"] .ytick text,
            [data-testid="stPlotlyChart"] .gtitle,
            [data-testid="stPlotlyChart"] .legendtext,
            [data-testid="stPlotlyChart"] .infolayer text {{
                fill: var(--viz-text) !important;
                color: var(--viz-text) !important;
            }}
            input, textarea, [contenteditable="true"] {{
                color: var(--viz-text) !important;
                -webkit-text-fill-color: var(--viz-text) !important;
            }}
            /*
             * Sidebar: Streamlit themes often set light-on-light (white/gray text on white).
             * Force readable foreground on our light panel, then restore white on buttons.
             */
            [data-testid="stSidebar"] p,
            [data-testid="stSidebar"] li,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] p,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] span,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] li,
            [data-testid="stSidebar"] [data-testid="stCaption"],
            [data-testid="stSidebar"] [data-testid="stCaption"] p,
            [data-testid="stSidebar"] [data-testid="stCaption"] span,
            [data-testid="stSidebar"] [data-testid="stCaption"] div {{
                color: var(--viz-muted) !important;
            }}
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong,
            [data-testid="stSidebar"] [data-testid="stMarkdownContainer"] code,
            [data-testid="stSidebar"] [data-testid="stCaption"] code,
            [data-testid="stSidebar"] [data-testid="stCaption"] strong {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stSidebar"] summary,
            [data-testid="stSidebar"] summary span {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stSidebar"] [data-testid="stAlert"],
            [data-testid="stSidebar"] [data-testid="stAlert"] p,
            [data-testid="stSidebar"] [data-testid="stAlert"] span,
            [data-testid="stSidebar"] [data-testid="stAlert"] div,
            [data-testid="stSidebar"] [data-testid="stNotification"],
            [data-testid="stSidebar"] [data-testid="stNotification"] p,
            [data-testid="stSidebar"] [data-testid="stNotification"] span {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stSidebar"] .stRadio label,
            [data-testid="stSidebar"] .stSelectbox label,
            [data-testid="stSidebar"] .stTextInput label,
            [data-testid="stSidebar"] .stMultiSelect label,
            [data-testid="stSidebar"] .stDateInput label {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stSidebar"] input[type="text"],
            [data-testid="stSidebar"] textarea {{
                color: var(--viz-text) !important;
            }}
            [data-testid="stSidebar"] .stButton > button,
            [data-testid="stSidebar"] .stButton > button *,
            [data-testid="stSidebar"] .stButton > button:hover,
            [data-testid="stSidebar"] .stButton > button:hover * {{
                color: var(--viz-button-text) !important;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )
