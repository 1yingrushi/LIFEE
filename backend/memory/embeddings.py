"""
嵌入提供者模块

支持 Gemini（默认）和 OpenAI 嵌入 API
参考 clawdbot embeddings-gemini.js / embeddings-openai.js
"""

from abc import ABC, abstractmethod
from typing import Optional

from google import genai


class EmbeddingProvider(ABC):
    """嵌入提供者抽象基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """提供者名称"""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """模型名称"""
        ...

    @property
    @abstractmethod
    def dimensions(self) -> int:
        """向量维度"""
        ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        """生成单个文本的嵌入向量"""
        ...

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入向量（默认逐个处理）"""
        results = []
        for text in texts:
            embedding = await self.embed(text)
            results.append(embedding)
        return results


class GeminiEmbedding(EmbeddingProvider):
    """
    Gemini 嵌入提供者

    使用 gemini-embedding-001 模型（免费）
    维度：768
    """

    DEFAULT_MODEL = "gemini-embedding-001"
    DIMENSIONS = 768

    def __init__(self, api_key: str, model: str = None):
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._client = genai.Client(api_key=api_key)

    @property
    def provider_name(self) -> str:
        return "gemini"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS

    async def embed(self, text: str) -> list[float]:
        """生成文本嵌入"""
        # Gemini embedding API 使用 embed_content 方法
        # task_type: RETRIEVAL_QUERY (查询) / RETRIEVAL_DOCUMENT (文档)
        result = await self._client.aio.models.embed_content(
            model=self._model,
            contents=text,
        )
        # 返回第一个嵌入向量
        return list(result.embeddings[0].values)

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入"""
        # Gemini 支持批量嵌入
        results = []
        for text in texts:
            embedding = await self.embed(text)
            results.append(embedding)
        return results


class OpenAIEmbedding(EmbeddingProvider):
    """
    OpenAI 嵌入提供者

    使用 text-embedding-3-small 模型
    维度：1536
    """

    DEFAULT_MODEL = "text-embedding-3-small"
    DEFAULT_BASE_URL = "https://api.openai.com/v1"
    DIMENSIONS = 1536

    def __init__(
        self,
        api_key: str,
        model: str = None,
        base_url: str = None,
    ):
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._base_url = base_url or self.DEFAULT_BASE_URL

        # 延迟导入 openai
        from openai import AsyncOpenAI
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=self._base_url,
        )

    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def dimensions(self) -> int:
        return self.DIMENSIONS

    async def embed(self, text: str) -> list[float]:
        """生成文本嵌入"""
        response = await self._client.embeddings.create(
            model=self._model,
            input=text,
        )
        return response.data[0].embedding

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量生成嵌入（OpenAI 原生支持批量）"""
        response = await self._client.embeddings.create(
            model=self._model,
            input=texts,
        )
        return [item.embedding for item in response.data]


class SiliconFlowEmbedding(OpenAIEmbedding):
    """SiliconFlow 嵌入提供者（OpenAI 兼容）

    说明：SiliconFlow 的向量模型维度随模型而异，这里在第一次调用后动态记录维度。
    """

    def __init__(self, api_key: str, model: str, base_url: str):
        super().__init__(api_key=api_key, model=model, base_url=base_url)
        self._dims: int = 0

    @property
    def provider_name(self) -> str:
        return "siliconflow"

    @property
    def dimensions(self) -> int:
        return self._dims or 0

    async def embed(self, text: str) -> list[float]:
        emb = await super().embed(text)
        if not self._dims:
            self._dims = len(emb)
        return emb

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        embs = await super().embed_batch(texts)
        if embs and not self._dims:
            self._dims = len(embs[0])
        return embs


def create_embedding_provider(
    google_api_key: Optional[str] = None,
    openai_api_key: Optional[str] = None,
    siliconflow_api_key: Optional[str] = None,
    siliconflow_base_url: Optional[str] = None,
    siliconflow_embedding_model: Optional[str] = None,
) -> EmbeddingProvider:
    """
    创建嵌入提供者

    优先级：Gemini > OpenAI

    Args:
        google_api_key: Google API Key（用于 Gemini）
        openai_api_key: OpenAI API Key

    Returns:
        嵌入提供者实例

    Raises:
        ValueError: 如果没有可用的 API Key
    """
    # 优先使用 Gemini（免费）
    if google_api_key:
        return GeminiEmbedding(api_key=google_api_key)

    # 其次使用 SiliconFlow（OpenAI 兼容）
    if siliconflow_api_key:
        return SiliconFlowEmbedding(
            api_key=siliconflow_api_key,
            base_url=siliconflow_base_url or "https://api.siliconflow.cn/v1",
            model=siliconflow_embedding_model or "BAAI/bge-large-zh-v1.5",
        )

    # 备选 OpenAI
    if openai_api_key:
        return OpenAIEmbedding(api_key=openai_api_key)

    raise ValueError(
        "没有可用的嵌入 API Key。"
        "请设置 GOOGLE_API_KEY（推荐）或 SILICONFLOW_API_KEY 或 OPENAI_API_KEY。"
    )
