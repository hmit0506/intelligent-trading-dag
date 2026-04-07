"""
LLM integration for portfolio management decisions.
"""
import os
from functools import lru_cache
from typing import Optional

from langchain_openai import ChatOpenAI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_anthropic import ChatAnthropic
from langchain_ollama import ChatOllama

try:
    from langchain_core.output_parsers import JsonOutputParser
    json_parser = JsonOutputParser()
except ImportError:
    try:
        from langchain.output_parsers.json import SimpleJsonOutputParser
        json_parser = SimpleJsonOutputParser()
    except ImportError:
        from langchain_core.output_parsers import BaseOutputParser
        import json

        class SimpleJsonParser(BaseOutputParser):
            def parse(self, text: str):
                text = text.strip()
                if text.startswith("```json"):
                    text = text[7:]
                if text.startswith("```"):
                    text = text[3:]
                if text.endswith("```"):
                    text = text[:-3]
                text = text.strip()
                return json.loads(text)

        json_parser = SimpleJsonParser()


def _provider_api_key_env(provider: str) -> str:
    if provider == "openai":
        return os.getenv("OPENAI_API_KEY") or ""
    if provider == "groq":
        return os.getenv("GROQ_API_KEY") or ""
    if provider == "openrouter":
        return os.getenv("OPENROUTER_API_KEY") or ""
    if provider == "gemini":
        return os.getenv("GOOGLE_API_KEY") or ""
    if provider == "anthropic":
        return os.getenv("ANTHROPIC_API_KEY") or ""
    if provider == "ollama":
        return ""
    raise ValueError(f"Unsupported provider: {provider}")


@lru_cache(maxsize=None)
def _get_llm_cached(
    provider: str,
    model: str,
    base_url_norm: str,
    temperature: float,
    api_key_material: str,
):
    """
    Cached LLM constructor. ``api_key_material`` must reflect the current secret
    so cache invalidates when the key rotates in-process (e.g. Streamlit Save).
    """
    timeout = 120
    max_retries = 3
    base_url: Optional[str] = base_url_norm or None

    if provider == "openai":
        resolved_base = base_url or "https://api.openai.com/v1"
        return ChatOpenAI(
            api_key=api_key_material or None,
            base_url=resolved_base,
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
        )
    if provider == "groq":
        resolved_base = base_url or "https://api.groq.com/v1"
        return ChatGroq(
            api_key=api_key_material or None,
            base_url=resolved_base,
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
        )
    if provider == "openrouter":
        resolved_base = base_url or "https://openrouter.ai/api/v1"
        return ChatOpenAI(
            api_key=api_key_material or None,
            base_url=resolved_base,
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
        )
    if provider == "gemini":
        resolved_base = base_url or "https://generativelanguage.googleapis.com/v1beta"
        return ChatGoogleGenerativeAI(
            google_api_key=api_key_material or None,
            base_url=resolved_base,
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
        )
    if provider == "anthropic":
        resolved_base = base_url or "https://api.anthropic.com"
        return ChatAnthropic(
            api_key=api_key_material or None,
            base_url=resolved_base,
            model=model,
            temperature=temperature,
            timeout=timeout,
            max_retries=max_retries,
        )
    if provider == "ollama":
        resolved_base = base_url or "http://localhost:11434"
        return ChatOllama(
            model=model,
            base_url=resolved_base,
            temperature=temperature,
            timeout=timeout,
        )
    raise ValueError(f"Unsupported provider: {provider}")


def clear_llm_cache() -> None:
    """Invalidate cached LLM clients (e.g. after updating API keys in the same process)."""
    _get_llm_cached.cache_clear()


def get_llm(
    provider: str,
    model: str,
    base_url: Optional[str],
    temperature: float,
):
    """
    Return a cached LLM instance based on provider and model.

    ``api_key_material`` is read from ``os.environ`` on each call and included in
    the cache key so a new key applied in-process (without restarting the app)
    produces a new client. Call :func:`clear_llm_cache` after bulk env changes if needed.

    ``temperature`` is passed through to the provider client (portfolio LLM path).
    Use ``0.0`` for minimum sampling variance where the API supports it.

    Supported providers: openai, groq, openrouter, gemini, anthropic, ollama
    """
    api_key_material = _provider_api_key_env(provider)
    base_url_norm = (base_url or "").strip()
    return _get_llm_cached(provider, model, base_url_norm, float(temperature), api_key_material)
