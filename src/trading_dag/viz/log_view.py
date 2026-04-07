"""Shared helpers for Streamlit run log display (standard backtest + benchmark builders)."""
from __future__ import annotations

import re

REASONING_BLOCK_RE = re.compile(
    r"={10,}\s*\n={5,}\s*.*?Agent\s*={5,}\s*\n[\s\S]*?\n={10,}",
    re.IGNORECASE,
)
_SNAPSHOT_BEFORE_BACKTESTING_RE = re.compile(r"\nBacktesting:\s", re.MULTILINE)

_SNAPSHOT_BANNER = "===== Latest portfolio snapshot (from full log) =====\n"
_PORTFOLIO_REASONING_BANNER = "===== Latest portfolio management reasoning (from full log) =====\n"
_TAIL_BANNER = "\n\n===== Live tail (latest lines) =====\n"


def clean_reasoning_blocks(text: str) -> str:
    """Replace large agent reasoning sections with a short placeholder for tail display."""
    return REASONING_BLOCK_RE.sub("[reasoning block omitted]\n", text)


def extract_latest_portfolio_snapshot(log_text: str, max_lines: int = 56) -> str | None:
    """Last PORTFOLIO SUMMARY block and decision table, up to the next tqdm line."""
    marker = "PORTFOLIO SUMMARY:"
    idx = log_text.rfind(marker)
    if idx < 0:
        return None
    rest = log_text[idx:].lstrip()
    m = _SNAPSHOT_BEFORE_BACKTESTING_RE.search(rest)
    if m:
        rest = rest[: m.start()].rstrip()
    lines = rest.splitlines()
    if not lines:
        return None
    if len(lines) > max_lines:
        body = "\n".join(lines[:max_lines]) + "\n... (truncated for display; see full log tail below)"
    else:
        body = "\n".join(lines)
    return body.strip()


def _extract_latest_agent_block(log_text: str, agent_name: str, max_lines: int = 180) -> str | None:
    """Extract the latest full agent print block bounded by ===== lines."""
    pattern = re.compile(
        rf"={10,}\s*{re.escape(agent_name)}\s*={10,}\s*\n[\s\S]*?\n={10,}",
        re.IGNORECASE,
    )
    matches = list(pattern.finditer(log_text))
    if not matches:
        return None
    block = matches[-1].group(0).strip()
    lines = block.splitlines()
    if len(lines) > max_lines:
        return "\n".join(lines[:max_lines]) + "\n... (truncated for display; see full log tail below)"
    return block


def prepend_latest_snapshot_to_tail(
    log_tail_text: str,
    full_log_text: str,
    *,
    max_lines: int = 56,
    include_live_tail: bool = True,
) -> str:
    """
    If the latest portfolio snapshot from the full log is absent from the tail window,
    prepend it so one ``st.code`` panel can show both the summary table and the live tail.
    """
    sections: list[str] = []

    snapshot = extract_latest_portfolio_snapshot(full_log_text, max_lines=max_lines)
    if snapshot and snapshot not in log_tail_text:
        sections.append(_SNAPSHOT_BANNER + snapshot)

    portfolio_reasoning = _extract_latest_agent_block(full_log_text, "Portfolio Management Agent")
    if portfolio_reasoning and portfolio_reasoning not in log_tail_text:
        sections.append(_PORTFOLIO_REASONING_BANNER + portfolio_reasoning)

    if not sections:
        return log_tail_text
    if include_live_tail:
        return "\n\n".join(sections) + _TAIL_BANNER + log_tail_text
    return "\n\n".join(sections)


def estimate_log_view_height(log_text: str, min_height: int = 260, max_height: int = 900) -> int:
    """Pick a readable ``st.code`` height from approximate line count."""
    line_count = max(1, len(log_text.splitlines()))
    estimated = line_count * 18 + 32
    return max(min_height, min(max_height, estimated))
