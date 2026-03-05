"""
LLM integration for portfolio management decisions.
"""
import os
from typing import Optional
from functools import lru_cache
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


@lru_cache(maxsize=None)
def get_llm(provider: str, model: str, base_url: Optional[str] = None):
    """
    Return a cached LLM instance based on provider and model.
    Supported providers: openai, groq, openrouter, gemini, anthropic, ollama
    """
    timeout = 120
    max_retries = 3

    if provider == "openai":
        base_url = base_url or "https://api.openai.com/v1"
        return ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "groq":
        base_url = base_url or "https://api.groq.com/v1"
        return ChatGroq(
            api_key=os.getenv("GROQ_API_KEY"),
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "openrouter":
        base_url = base_url or "https://openrouter.ai/api/v1"
        return ChatOpenAI(
            api_key=os.getenv("OPENROUTER_API_KEY"),
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "gemini":
        base_url = base_url or "https://generativelanguage.googleapis.com/v1beta"
        return ChatGoogleGenerativeAI(
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "anthropic":
        base_url = base_url or "https://api.anthropic.com"
        return ChatAnthropic(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            base_url=base_url,
            model=model,
            timeout=timeout,
            max_retries=max_retries,
        )
    elif provider == "ollama":
        base_url = base_url or "http://localhost:11434"
        return ChatOllama(
            model=model,
            base_url=base_url,
            timeout=timeout,
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
