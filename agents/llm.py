"""OpenAI 兼容接口。默认指向 DeepSeek，更换 Base URL 和模型名即可切换。"""

from __future__ import annotations

from typing import Any

from config import LLM_MAX_TOKENS, LLM_TIMEOUT_SECONDS
from errors import LLMCallError


def locked_temperature(base_url: str, model: str) -> float | None:
    """部分模型只接受固定温度。Kimi 当前接口要求温度为 1。"""

    blob = f"{base_url} {model}".lower()
    if "moonshot.ai" in blob or "moonshot.cn" in blob or "kimi" in blob:
        return 1.0
    return None


def _temperature_must_be_one(message: str) -> bool:
    lowered = message.lower()
    if "temperature" in lowered and "only 1 is allowed" in lowered:
        return True
    return "只允许温度为 1" in message


def explain_llm_exception(exc: Exception) -> str:
    """把接口异常收成可直接展示的中文说明。"""

    name = type(exc).__name__.lower()
    message = str(exc).strip()
    lowered = message.lower()
    if "authentication" in name or "401" in lowered or "invalid api key" in lowered:
        return "模型调用失败：API Key 无效或未授权，请检查密钥是否正确。"
    if "ratelimit" in name or "429" in lowered or "rate limit" in lowered:
        return "模型调用失败：请求过于频繁或额度不足，请稍后重试。"
    if "timeout" in name or "timed out" in lowered:
        return "模型调用失败：请求超时，请稍后重试或减少材料体积。"
    if "connection" in name or "connection error" in lowered or "connect" in lowered:
        return "模型调用失败：无法连接到接口，请检查 Base URL 与网络。"
    if "notfound" in name or "404" in lowered or "model_not_found" in lowered:
        return "模型调用失败：模型不存在或 Base URL 不正确，请检查模型名称与接口地址。"
    if _temperature_must_be_one(lowered):
        return "模型调用失败：该模型只允许温度为 1。请把左侧温度调到 1 后重试。"
    if not message:
        return "模型调用失败：接口返回异常，请稍后重试。"
    return f"模型调用失败：{message}"


def chat_complete(
    messages: list[dict[str, str]],
    *,
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout: float = LLM_TIMEOUT_SECONDS,
    client: Any | None = None,
) -> str:
    """发送一次 chat completions 请求。client 仅供自测注入。"""

    if not str(api_key or "").strip():
        raise LLMCallError("未配置 API Key，请在左侧边栏填写后再开始分析。")
    if not str(base_url or "").strip():
        raise LLMCallError("未配置 Base URL，请在左侧边栏填写接口地址。")
    if not str(model or "").strip():
        raise LLMCallError("未配置模型名称，请在左侧边栏填写。")

    # Kimi 等模型会直接拒绝 0.2。先改成它接受的温度，避免整次分析在第一步失败。
    forced = locked_temperature(base_url, model)
    use_temperature = forced if forced is not None else temperature
    try:
        return _request(messages, base_url, api_key, model, use_temperature, timeout, client)
    except LLMCallError as exc:
        if use_temperature != 1 and _temperature_must_be_one(str(exc)):
            return _request(messages, base_url, api_key, model, 1, timeout, client)
        raise


def _request(
    messages: list[dict[str, str]],
    base_url: str,
    api_key: str,
    model: str,
    temperature: float,
    timeout: float,
    client: Any | None,
) -> str:
    try:
        sdk = client or _build_client(base_url.strip(), api_key.strip(), timeout)
        response = sdk.chat.completions.create(
            model=model.strip(),
            temperature=temperature,
            messages=messages,
            max_tokens=LLM_MAX_TOKENS,
        )
        choice = response.choices[0]
        content = (choice.message.content or "").strip()
        if not content:
            raise LLMCallError("模型调用失败：模型返回了空内容，请稍后重试或更换模型。")
        return content
    except LLMCallError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise LLMCallError(explain_llm_exception(exc)) from exc


def _build_client(base_url: str, api_key: str, timeout: float) -> Any:
    from openai import OpenAI

    return OpenAI(api_key=api_key, base_url=base_url, timeout=timeout)
