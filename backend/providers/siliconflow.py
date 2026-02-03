"""SiliconFlow Provider

硅基流动通常提供 OpenAI 兼容接口（chat/completions、embeddings 等）。
这里复用项目内已有的 OpenAICompatProvider，以最小改动接入。

注意：base_url / model 以配置为准，默认值仅作合理猜测。
"""

from .openai_compat import OpenAICompatProvider


class SiliconFlowProvider(OpenAICompatProvider):
    """SiliconFlow Provider (OpenAI Compatible)"""

    DEFAULT_BASE_URL = "https://api.siliconflow.cn/v1"

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
    ):
        super().__init__(
            api_key=api_key,
            base_url=base_url or self.DEFAULT_BASE_URL,
            model=model,
            provider_name="siliconflow",
        )


