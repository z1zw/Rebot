from __future__ import annotations


OFFICIAL_PROVIDER_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "openai_compatible": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "deepseek": "https://api.deepseek.com/v1",
    "moonshot": "https://api.moonshot.cn/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta/openai",
    "openrouter": "https://openrouter.ai/api/v1",
    "dashscope": "https://dashscope.aliyuncs.com/compatible-mode/v1",
    "qianfan": "https://qianfan.baidubce.com/v2",
    "ollama": "http://localhost:11434/v1",
    "bedrock": "https://bedrock-runtime.us-east-1.amazonaws.com",
}


def infer_provider_from_model(model: str) -> str | None:
    model_l = (model or "").strip().lower()
    if not model_l:
        return None
    if model_l.startswith("deepseek-"):
        return "deepseek"
    if model_l.startswith("claude-"):
        return "anthropic"
    if model_l.startswith("gemini-"):
        return "gemini"
    if model_l.startswith("moonshot-") or "kimi" in model_l:
        return "moonshot"
    if model_l.startswith("qwen-"):
        return "dashscope"
    if model_l.startswith("ernie-"):
        return "qianfan"
    if "/" in model_l and model_l.split("/", 1)[0] in {"openai", "google", "anthropic", "meta", "deepseek"}:
        return "openrouter"
    return None


def normalize_llm_selection(
    *,
    provider: str | None,
    model: str,
    base_url: str | None,
) -> tuple[str | None, str]:
    provider_norm = (provider or "").strip().lower()
    model_norm = (model or "").strip()
    base_norm = (base_url or "").strip()

    inferred = infer_provider_from_model(model_norm)
    if inferred and (
        not provider_norm
        or provider_norm in {"openai", "openai_compatible", "custom"}
        or provider_norm != inferred
    ):
        provider_norm = inferred

    official_base = OFFICIAL_PROVIDER_BASE_URLS.get(provider_norm)
    if official_base:
        return (provider_norm or None, official_base)
    if base_norm:
        return (provider_norm or None, base_norm)
    return (provider_norm or None, OFFICIAL_PROVIDER_BASE_URLS["openai"])

