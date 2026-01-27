"""LLM Providers"""
from .base import ChatResponse, LLMProvider, Message, MessageRole
from .claude import ClaudeProvider
from .openai_compat import QwenProvider, OllamaProvider, OpenCodeZenProvider
from .gemini import GeminiProvider
from .auth import (
    OAuthCredentials,
    read_claude_code_credentials,
    get_api_key_from_credentials,
    get_auth_info,
)

__all__ = [
    # 基类
    "LLMProvider",
    "Message",
    "MessageRole",
    "ChatResponse",
    # Providers
    "ClaudeProvider",
    "QwenProvider",
    "OllamaProvider",
    "OpenCodeZenProvider",
    "GeminiProvider",
    # 认证
    "OAuthCredentials",
    "read_claude_code_credentials",
    "get_api_key_from_credentials",
    "get_auth_info",
]
