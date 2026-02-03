"""
建议回复生成器 - 根据讨论内容生成用户可能的回复建议
"""
import json
import re
from typing import List

from lifee.providers.base import LLMProvider, Message


SUGGESTION_SYSTEM_PROMPT = """你是一个对话建议生成器。根据当前讨论的上下文，生成 3 个用户可能想说的回复建议。

要求：
1. 建议应该多样化：
   - 一个深入追问或请求澄清的建议
   - 一个表达自己观点或看法的建议
   - 一个转向新话题或新角度的建议
2. 每个建议简短（10-30 字）
3. 语气自然，像真人说话，用第一人称
4. 用 JSON 数组格式返回：["建议1", "建议2", "建议3"]
5. 只返回 JSON 数组，不要有其他内容"""


class SuggestionGenerator:
    """生成用户回复建议"""

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def generate(
        self,
        messages: List[Message],
        num_suggestions: int = 3,
    ) -> List[str]:
        """
        根据对话历史生成回复建议

        Args:
            messages: 对话历史
            num_suggestions: 建议数量

        Returns:
            建议列表，失败时返回空列表
        """
        try:
            # 将对话历史转换为摘要文本，作为单个 user 消息发送
            # 这样可以避免消息格式不符合 API 要求的问题
            context = self._format_context(messages)
            if not context:
                return []

            from lifee.providers.base import MessageRole
            request_messages = [
                Message(
                    role=MessageRole.USER,
                    content=f"以下是当前的讨论内容：\n\n{context}\n\n请根据这个讨论生成 3 个用户可能想说的回复建议。",
                )
            ]

            response = await self.provider.chat(
                messages=request_messages,
                system=SUGGESTION_SYSTEM_PROMPT,
                max_tokens=200,
                temperature=0.8,
            )

            # 解析 JSON 响应
            suggestions = self._parse_suggestions(response.content)
            return suggestions[:num_suggestions]

        except Exception as e:
            # 任何错误都降级到空列表
            print(f"\n[建议生成失败: {e}]")
            return []

    def _format_context(self, messages: List[Message], max_messages: int = 6) -> str:
        """将消息列表格式化为上下文文本"""
        if not messages:
            return ""

        # 只取最近的几条消息
        recent = messages[-max_messages:]
        lines = []
        for msg in recent:
            if msg.role.value == "user":
                speaker = "用户"
            else:
                speaker = msg.name or "AI"
            lines.append(f"{speaker}: {msg.content[:200]}")  # 限制长度

        return "\n".join(lines)

    def _parse_suggestions(self, content: str) -> List[str]:
        """解析 LLM 返回的建议"""
        # 尝试直接解析 JSON
        try:
            suggestions = json.loads(content.strip())
            if isinstance(suggestions, list):
                return [str(s) for s in suggestions if s]
        except json.JSONDecodeError:
            pass

        # 尝试提取 JSON 数组部分
        match = re.search(r'\[.*?\]', content, re.DOTALL)
        if match:
            try:
                suggestions = json.loads(match.group())
                if isinstance(suggestions, list):
                    return [str(s) for s in suggestions if s]
            except json.JSONDecodeError:
                pass

        return []
