"""FastAPI 版本的 LIFEE 后端服务

该模块复用 backend 包中的配置、Provider、会话、角色和知识库逻辑，
对外暴露 HTTP API，供前端（Vue/Vite）调用。
"""

from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from backend.config.settings import settings
from backend.providers import (
    LLMProvider,
    Message,
    MessageRole,
    ClaudeProvider,
    SyntheticProvider,
    QwenProvider,
    OllamaProvider,
    OpenCodeZenProvider,
    GeminiProvider,
    SiliconFlowProvider,
    FallbackProvider,
)
from backend.sessions import Session, SessionStore
from backend.roles import RoleManager
from backend.memory import MemoryManager, format_search_results
from backend.debate import Moderator, Participant


app = FastAPI(title="LIFEE Backend", version="1.0.0")

# CORS middleware - 允许前端跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 开发环境允许所有来源
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"],  # 明确列出方法
    allow_headers=["*"],  # 允许所有请求头
    expose_headers=["*"],  # 暴露所有响应头
)

# 全局状态（简单实现：单进程内共用）
store = SessionStore(storage_dir=None)
session: Session = store.create()
role_manager = RoleManager()
knowledge_manager: Optional[MemoryManager] = None
current_role: str = ""


@app.on_event("startup")
async def startup_event():
    """启动时初始化所有角色的知识库（已索引的不重复）"""
    print("\n[启动] 初始化知识库...")
    roles = role_manager.list_roles()
    
    for role_name in roles:
        info = role_manager.get_role_info(role_name)
        if not info.get("has_knowledge"):
            continue
        
        try:
            # 使用 auto_index=True，但内部逻辑会检查是否需要重新索引
            km = await role_manager.get_knowledge_manager(
                role_name,
                google_api_key=settings.google_api_key,
                openai_api_key=getattr(settings, "openai_api_key", None),
                siliconflow_api_key=getattr(settings, "siliconflow_api_key", None),
                siliconflow_base_url=getattr(settings, "siliconflow_base_url", None),
                siliconflow_embedding_model=getattr(settings, "siliconflow_embedding_model", None),
                auto_index=True,  # 启动时自动索引
            )
            if km:
                stats = km.get_stats()
                print(f"  ✓ {role_name}: {stats['chunk_count']} chunks, {stats['file_count']} files")
        except Exception as e:
            print(f"  ✗ {role_name}: 初始化失败 - {e}")
    
    print("[启动] 知识库初始化完成\n")


def _create_single_provider(provider_name: str) -> LLMProvider:
    """根据 provider_name 创建单个 Provider（不含 fallback 逻辑）"""
    name = provider_name.lower()

    if name == "claude":
        api_key = settings.get_anthropic_api_key()
        if not api_key:
            raise HTTPException(
                status_code=500,
                detail="缺少 Claude 的 ANTHROPIC_API_KEY，请在 backend/.env 中配置。",
            )
        return ClaudeProvider(api_key=api_key, model=settings.claude_model)

    if name == "synthetic":
        if not settings.synthetic_api_key:
            raise HTTPException(
                status_code=500,
                detail="缺少 Synthetic 的 SYNTHETIC_API_KEY，请在 backend/.env 中配置。",
            )
        return SyntheticProvider(
            api_key=settings.synthetic_api_key,
            model=settings.synthetic_model,
        )

    if name == "qwen":
        if not settings.qwen_api_key:
            raise HTTPException(
                status_code=500,
                detail="缺少 Qwen 的 QWEN_API_KEY，请在 backend/.env 中配置。",
            )
        return QwenProvider(api_key=settings.qwen_api_key, model=settings.qwen_model)

    if name == "gemini":
        if not settings.google_api_key:
            raise HTTPException(
                status_code=500,
                detail="缺少 Gemini 的 GOOGLE_API_KEY，请在 backend/.env 中配置。",
            )
        return GeminiProvider(api_key=settings.google_api_key, model=settings.gemini_model)

    if name == "ollama":
        # Ollama 本地无需 API Key，但需要正确的 base_url 和 model
        return OllamaProvider(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )

    if name == "opencode":
        if not settings.opencode_api_key:
            raise HTTPException(
                status_code=500,
                detail="缺少 OpenCode 的 OPENCODE_API_KEY，请在 backend/.env 中配置。",
            )
        return OpenCodeZenProvider(
            api_key=settings.opencode_api_key,
            model=settings.opencode_model,
        )

    if name == "siliconflow":
        if not settings.siliconflow_api_key:
            raise HTTPException(
                status_code=500,
                detail="缺少 SiliconFlow 的 SILICONFLOW_API_KEY，请在 backend/.env 中配置。",
            )
        return SiliconFlowProvider(
            api_key=settings.siliconflow_api_key,
            base_url=settings.siliconflow_base_url,
            model=settings.siliconflow_model,
        )

    raise HTTPException(
        status_code=500,
        detail=(
            f"未知的 LLM_PROVIDER: {provider_name}，请在 backend/.env 中设置为 "
            "claude、synthetic、qwen、gemini、ollama、opencode 或 siliconflow。"
        ),
    )


def create_provider_with_fallback(provider_name: str | None = None) -> LLMProvider:
    """创建带 fallback 的 Provider

    如果 settings.llm_fallback 配置了备用 Provider 列表，会按顺序依次创建，
    并由 FallbackProvider 负责在运行时自动降级。
    """
    primary_name = (provider_name or settings.llm_provider).lower()
    providers: list[LLMProvider] = []

    # 主 Provider
    providers.append(_create_single_provider(primary_name))

    # 备用 Provider 列表，逗号分隔，例如: "qwen,ollama"
    fallback_str = (settings.llm_fallback or "").strip()
    if fallback_str:
        for name in [s.strip() for s in fallback_str.split(",") if s.strip()]:
            lname = name.lower()
            if lname == primary_name:
                continue
            try:
                providers.append(_create_single_provider(lname))
            except HTTPException as e:
                # 配置有问题时打印提示，但不中断主流程
                print(f"[警告] 无法创建 fallback provider '{lname}': {e.detail}")

    if not providers:
        # 理论上不会发生，因为主 Provider 已经加入
        raise HTTPException(status_code=500, detail="未能创建任何可用的 LLM Provider")

    if len(providers) == 1:
        return providers[0]

    return FallbackProvider(providers)


def create_provider_for_api(provider_name: str | None = None) -> LLMProvider:
    """为 API 创建 LLM Provider（支持 llm_fallback 自动降级）"""
    return create_provider_with_fallback(provider_name)


class ChatRequest(BaseModel):
    message: str
    role: Optional[str] = None


class ChatResponse(BaseModel):
    reply: str
    provider: str
    model: str
    role: Optional[str] = None


class RolesResponse(BaseModel):
    roles: list[str]


class MemoryStatus(BaseModel):
    enabled: bool
    file_count: int = 0
    chunk_count: int = 0
    embedding_provider: Optional[str] = None
    embedding_model: Optional[str] = None


async def get_or_init_knowledge(role_name: str) -> Optional[MemoryManager]:
    """根据角色名称初始化（或复用）知识库管理器"""
    global knowledge_manager, current_role

    if not role_name:
        return None

    info = role_manager.get_role_info(role_name)
    if not info.get("has_knowledge"):
        return None

    # 如果角色切换了，需要重建 manager
    if knowledge_manager is None or role_name != current_role:
        try:
            knowledge_manager = await role_manager.get_knowledge_manager(
                role_name,
                google_api_key=settings.google_api_key,
                openai_api_key=getattr(settings, "openai_api_key", None),
                siliconflow_api_key=getattr(settings, "siliconflow_api_key", None),
                siliconflow_base_url=getattr(settings, "siliconflow_base_url", None),
                siliconflow_embedding_model=getattr(settings, "siliconflow_embedding_model", None),
            )
            current_role = role_name
        except Exception as e:  # pragma: no cover - 防御性
            if settings.debug:
                print(f"[知识库初始化失败] {e}")
            knowledge_manager = None

    return knowledge_manager


@app.get("/roles", response_model=RolesResponse)
async def list_roles_api() -> RolesResponse:
    """列出可用角色名称"""
    return RolesResponse(roles=role_manager.list_roles())


@app.get("/memory/status", response_model=MemoryStatus)
async def memory_status(role: Optional[str] = None) -> MemoryStatus:
    """查看指定角色（或当前默认角色）的知识库状态"""
    role_name = role or ""
    km = await get_or_init_knowledge(role_name)
    if not km:
        return MemoryStatus(enabled=False)

    stats = km.get_stats()
    return MemoryStatus(
        enabled=True,
        file_count=stats["file_count"],
        chunk_count=stats["chunk_count"],
        embedding_provider=stats["embedding_provider"],
        embedding_model=stats["embedding_model"],
    )


@app.post("/chat", response_model=ChatResponse)
async def chat_api(body: ChatRequest) -> ChatResponse:
    """单轮对话接口（会在后端维护对话历史）"""
    provider = create_provider_for_api()

    # 更新会话历史
    session.add_user_message(body.message)

    # 基础 system 提示词
    base_prompt = """你是 LIFEE 的 AI 助手，一个辩论式决策助手。
你的职责是帮助用户思考人生决策问题，提供多角度的观点和建议。
保持友好、专业的态度，用中文回复。"""

    system_prompt = base_prompt

    # 角色提示词
    role_name = body.role or ""
    if role_name:
        role_prompt = role_manager.load_role(role_name)
        if role_prompt:
            system_prompt = role_prompt + "\n\n---\n\n" + base_prompt

    # 知识库搜索并注入
    km = await get_or_init_knowledge(role_name)
    if km:
        try:
            results = await km.search(
                body.message,
                max_results=3,
                min_score=0.35,
            )
            if results:
                knowledge_context = format_search_results(results)
                system_prompt = (
                    system_prompt
                    + "\n\n---\n\n## 相关知识（供参考）\n\n"
                    + knowledge_context
                )
        except Exception as e:  # pragma: no cover - 防御性
            if settings.debug:
                print(f"[知识库搜索失败] {e}")

    messages = session.get_messages()

    # 非流式调用，直接返回完整文本
    resp = await provider.chat(
        messages=messages,
        system=system_prompt,
        temperature=0.7,
    )

    session.add_assistant_message(resp.content)

    return ChatResponse(
        reply=resp.content,
        provider=provider.name,
        model=provider.model,
        role=role_name or None,
    )


class HistoryResponse(BaseModel):
    messages: list[dict]  # [{role: "user"/"assistant", content: "..."}]


class RoleInfo(BaseModel):
    name: str
    display_name: Optional[str] = None
    emoji: Optional[str] = None
    has_knowledge: bool = False


class RolesInfoResponse(BaseModel):
    roles: list[RoleInfo]


class MemorySearchRequest(BaseModel):
    query: str
    role: Optional[str] = None
    max_results: int = 5
    min_score: float = 0.35


class MemorySearchResult(BaseModel):
    path: str
    start_line: int
    end_line: int
    text: str
    score: float


class MemorySearchResponse(BaseModel):
    results: list[MemorySearchResult]


class DebatePersona(BaseModel):
    id: str  # 角色名称（role_name，对应 backend/roles/ 下的目录名）
    name: Optional[str] = None  # 显示名称（可选，如果不提供则使用角色的 display_name）


class DebateRoundRequest(BaseModel):
    """多智能体辩论一轮请求"""

    user_input: str = Field(
        description="本轮用户输入"
    )
    role_names: list[str] = Field(
        default_factory=list,
        description="参与辩论的角色名称列表（如果为空则使用所有可用角色）",
    )


class DebateMessage(BaseModel):
    persona_id: str
    text: str


class DebateRoundResponse(BaseModel):
    messages: list[DebateMessage]
    options: list[str]


@app.get("/")
async def root():
    return {
        "name": "LIFEE Backend",
        "provider": settings.llm_provider,
        "debug": settings.debug,
    }


@app.get("/history", response_model=HistoryResponse)
async def get_history() -> HistoryResponse:
    """获取对话历史"""
    messages = []
    for msg in session.history:
        messages.append({
            "role": "user" if msg.role == MessageRole.USER else "assistant",
            "content": msg.content,
        })
    return HistoryResponse(messages=messages)


@app.post("/clear")
async def clear_history():
    """清空对话历史"""
    session.clear_history()
    return {"message": "对话历史已清空"}


@app.get("/roles/info", response_model=RolesInfoResponse)
async def get_roles_info() -> RolesInfoResponse:
    """获取角色详细信息列表（用于交互式选择）"""
    roles = role_manager.list_roles()
    role_infos = []
    for role_name in roles:
        info = role_manager.get_role_info(role_name)
        role_infos.append(RoleInfo(
            name=role_name,
            display_name=info.get("display_name"),
            emoji=info.get("emoji"),
            has_knowledge=info.get("has_knowledge", False),
        ))
    return RolesInfoResponse(roles=role_infos)


@app.post("/memory/search", response_model=MemorySearchResponse)
async def search_memory(body: MemorySearchRequest) -> MemorySearchResponse:
    """搜索知识库"""
    role_name = body.role or ""
    km = await get_or_init_knowledge(role_name)

    if not km:
        return MemorySearchResponse(results=[])

    try:
        results = await km.search(
            body.query,
            max_results=body.max_results,
            min_score=body.min_score,
        )
        search_results = [
            MemorySearchResult(
                path=r.path,
                start_line=r.start_line,
                end_line=r.end_line,
                text=r.text,
                score=r.score,
            )
            for r in results
        ]
        return MemorySearchResponse(results=search_results)
    except Exception as e:
        if settings.debug:
            print(f"[知识库搜索失败] {e}")
        return MemorySearchResponse(results=[])


def _extract_json_object(text: str) -> Optional[dict]:
    """从 LLM 输出中尽量提取出一个 JSON 对象"""
    import json

    text = text.strip()
    if not text:
        return None

    # 先尝试整体解析
    try:
        return json.loads(text)
    except Exception:
        pass

    # 退而求其次：截取第一个 { 到最后一个 } 之间的内容
    first = text.find("{")
    last = text.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return None

    candidate = text[first : last + 1].strip()
    try:
        return json.loads(candidate)
    except Exception:
        return None


@app.post("/debate/round", response_model=DebateRoundResponse)
async def debate_round(body: DebateRoundRequest) -> DebateRoundResponse:
    """多智能体辩论一轮（使用 Moderator 和 Participant）"""
    provider = create_provider_for_api()

    # 获取可用的角色列表
    available_roles = role_manager.list_roles()
    if not available_roles:
        raise HTTPException(
            status_code=400,
            detail="没有可用的角色，请在 backend/roles/ 下创建角色",
        )

    # 确定要使用的角色
    selected_role_names = body.role_names if body.role_names else available_roles
    if len(selected_role_names) < 2:
        raise HTTPException(
            status_code=400,
            detail="辩论需要至少 2 个角色",
        )

    # 验证角色是否存在
    invalid_roles = [r for r in selected_role_names if r not in available_roles]
    if invalid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"以下角色不存在: {', '.join(invalid_roles)}",
        )

    # 创建参与者列表
    participants = []
    for role_name in selected_role_names:
        # 获取知识库管理器（禁用自动索引，避免阻塞 API）
        try:
            km = await role_manager.get_knowledge_manager(
                role_name,
                google_api_key=settings.google_api_key,
                openai_api_key=getattr(settings, "openai_api_key", None),
                siliconflow_api_key=getattr(settings, "siliconflow_api_key", None),
                siliconflow_base_url=getattr(settings, "siliconflow_base_url", None),
                siliconflow_embedding_model=getattr(settings, "siliconflow_embedding_model", None),
                auto_index=False,  # 禁用自动索引，避免阻塞 API 响应
            )
        except Exception:
            km = None

        p = Participant(
            role_name=role_name,
            provider=provider,
            role_manager=role_manager,
            knowledge_manager=km,
        )
        participants.append(p)

    # 创建新的会话（每轮辩论使用独立会话）
    debate_session = store.create()

    # 创建主持者（暂时不使用用户记忆上下文）
    moderator = Moderator(participants, debate_session, user_memory_context=None)

    # 运行一轮辩论
    # 使用字典来累积每个参与者的完整发言
    participant_texts: dict[str, str] = {}
    
    async for participant, chunk, is_skip in moderator.run(
        user_input=body.user_input,
        max_turns=len(participants),  # 每个参与者发言一次
    ):
        if is_skip:
            # 跳过（保持沉默），不添加到结果中
            continue

        # 累积每个参与者的发言
        role_name = participant.info.name
        if role_name not in participant_texts:
            participant_texts[role_name] = ""
        participant_texts[role_name] += chunk

    # 转换为消息列表
    messages_list = [
        DebateMessage(persona_id=role_name, text=text.strip())
        for role_name, text in participant_texts.items()
        if text.strip()  # 只包含非空发言
    ]

    # 生成建议选项（简化版：基于对话历史）
    # TODO: 可以使用 SuggestionGenerator，但先简化
    options = [
        "继续讨论这个话题",
        "我想了解更多细节",
        "换个角度思考",
    ]

    return DebateRoundResponse(messages=messages_list, options=options)


