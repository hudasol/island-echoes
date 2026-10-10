from __future__ import annotations

from ..config import Settings
from .base import AnswerLLM, LLMError

HF_BASE = "https://router.huggingface.co/v1"


def build_llm(s: Settings) -> AnswerLLM | None:
    """Pick the answer model from settings. Returns None when chat is off.

    LLM_PROVIDER: off | extractive | ollama | llamacpp | huggingface | openai-compat | anthropic.
    When unset, chat stays off unless ANTHROPIC_API_KEY is present (the earlier behaviour).
    """
    p = (s.llm_provider or ("anthropic" if s.anthropic_api_key else "off")).lower()
    if p == "off":
        return None
    if p == "extractive":
        from .extractive import ExtractiveAnswerLLM

        return ExtractiveAnswerLLM()
    if p == "ollama":
        from .ollama import OllamaAnswerLLM

        return OllamaAnswerLLM(s.llm_model or "qwen2.5:3b-instruct", s.ollama_url)
    if p == "llamacpp":
        from .llamacpp import LlamaCppAnswerLLM

        if not s.llamacpp_model_path:
            raise LLMError("LLAMACPP_MODEL_PATH is not set")
        return LlamaCppAnswerLLM(str(s.llamacpp_model_path))
    if p in ("huggingface", "hf"):
        from .openai_compat import OpenAICompatAnswerLLM

        if not s.hf_token:
            raise LLMError("HF_TOKEN is not set (a free Hugging Face token works)")
        return OpenAICompatAnswerLLM(HF_BASE, s.llm_model or "Qwen/Qwen2.5-7B-Instruct", s.hf_token, provider="huggingface")
    if p in ("openai-compat", "openai"):
        from .openai_compat import OpenAICompatAnswerLLM

        if not s.openai_base_url:
            raise LLMError("OPENAI_BASE_URL is not set")
        return OpenAICompatAnswerLLM(s.openai_base_url, s.llm_model or "default", s.openai_api_key, provider="openai-compat")
    if p == "anthropic":
        from .anthropic_llm import AnthropicAnswerLLM

        if not s.anthropic_api_key:
            raise LLMError("ANTHROPIC_API_KEY is not set")
        return AnthropicAnswerLLM(s.anthropic_api_key, s.llm_model or s.anthropic_model)
    raise LLMError(f"unknown LLM_PROVIDER {p!r}")
