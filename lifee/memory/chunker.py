"""
文档分块模块

参考 clawdbot internal.js chunkMarkdown
"""

import hashlib
from dataclasses import dataclass


@dataclass
class Chunk:
    """文档分块"""
    text: str
    start_line: int
    end_line: int
    hash: str

    @staticmethod
    def compute_hash(text: str) -> str:
        """计算文本的 SHA256 哈希"""
        return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def chunk_markdown(
    content: str,
    max_tokens: int = 400,
    overlap_tokens: int = 80,
) -> list[Chunk]:
    """
    将 Markdown 文档分块

    Args:
        content: 文档内容
        max_tokens: 每块最大 token 数（估算 4 chars/token）
        overlap_tokens: 块之间重叠的 token 数

    Returns:
        分块列表
    """
    # 估算字符数（4 chars/token）
    max_chars = max(32, max_tokens * 4)
    overlap_chars = max(0, overlap_tokens * 4)

    lines = content.split("\n")
    if not lines:
        return []

    chunks = []
    current_lines: list[str] = []
    current_chars = 0
    start_line = 0

    for i, line in enumerate(lines):
        line_chars = len(line) + 1  # +1 for newline

        # 如果当前块加上这行会超过限制
        if current_chars + line_chars > max_chars and current_lines:
            # 保存当前块
            chunk_text = "\n".join(current_lines)
            if chunk_text.strip():
                chunks.append(Chunk(
                    text=chunk_text,
                    start_line=start_line,
                    end_line=i - 1,
                    hash=Chunk.compute_hash(chunk_text),
                ))

            # 计算重叠：保留最后几行
            overlap_lines = []
            overlap_total = 0
            for prev_line in reversed(current_lines):
                prev_chars = len(prev_line) + 1
                if overlap_total + prev_chars <= overlap_chars:
                    overlap_lines.insert(0, prev_line)
                    overlap_total += prev_chars
                else:
                    break

            # 开始新块
            current_lines = overlap_lines
            current_chars = overlap_total
            start_line = i - len(overlap_lines)

        current_lines.append(line)
        current_chars += line_chars

    # 处理最后一块
    if current_lines:
        chunk_text = "\n".join(current_lines)
        if chunk_text.strip():
            chunks.append(Chunk(
                text=chunk_text,
                start_line=start_line,
                end_line=len(lines) - 1,
                hash=Chunk.compute_hash(chunk_text),
            ))

    return chunks


def chunk_file(
    path: str,
    max_tokens: int = 400,
    overlap_tokens: int = 80,
) -> list[Chunk]:
    """
    读取文件并分块

    Args:
        path: 文件路径
        max_tokens: 每块最大 token 数
        overlap_tokens: 重叠 token 数

    Returns:
        分块列表
    """
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()

    return chunk_markdown(content, max_tokens, overlap_tokens)
