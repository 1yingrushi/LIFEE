"""LIFEE CLI 入口"""
import asyncio
import sys
from pathlib import Path

# Windows 控制台 UTF-8 编码支持
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

from lifee.config.settings import settings


def save_api_key_to_env(key_name: str, key_value: str) -> bool:
    """保存 API Key 到 .env 文件"""
    env_path = Path(".env")

    # 如果 .env 不存在，从 .env.example 复制
    if not env_path.exists():
        example_path = Path(".env.example")
        if example_path.exists():
            env_path.write_text(example_path.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            # 创建基础 .env
            env_path.write_text(f"LLM_PROVIDER=qwen\n{key_name}={key_value}\n", encoding="utf-8")
            return True

    # 读取现有内容
    content = env_path.read_text(encoding="utf-8")
    lines = content.split("\n")

    # 查找并更新 key
    found = False
    for i, line in enumerate(lines):
        if line.startswith(f"{key_name}="):
            lines[i] = f"{key_name}={key_value}"
            found = True
            break

    if not found:
        # 添加新的 key
        lines.append(f"{key_name}={key_value}")

    # 写回文件
    env_path.write_text("\n".join(lines), encoding="utf-8")
    return True


import httpx


def get_ollama_models() -> list:
    """获取 Ollama 已安装的模型列表"""
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            data = response.json()
            models = data.get("models", [])
            return [m["name"] for m in models]
    except Exception:
        pass
    return []


# 各供应商的模型列表
PROVIDER_MODELS = {
    "qwen": {
        "env_key": "QWEN_MODEL",
        "models": [
            ("qwen-plus", "通用对话，性价比高"),
            ("qwen-max", "最强模型，复杂任务"),
            ("qwen-turbo", "快速响应，简单任务"),
            ("qwen-long", "超长上下文"),
        ],
    },
    "gemini": {
        "env_key": "GEMINI_MODEL",
        "models": [
            ("gemini-3-flash-preview", "Gemini 3 快速"),
            ("gemini-3-pro-preview", "Gemini 3 最强"),
            ("gemini-2.5-pro", "2.5 最强"),
            ("gemini-2.5-flash", "2.5 快速"),
            ("gemini-2.5-flash-lite", "2.5 轻量"),
            ("gemini-2.0-flash", "2.0 推荐"),
            ("gemini-2.0-flash-lite", "2.0 轻量"),
        ],
    },
    "opencode": {
        "env_key": "OPENCODE_MODEL",
        "models": [
            ("big-pickle", "OpenCode 免费"),
        ],
    },
    "claude": {
        "env_key": "CLAUDE_MODEL",
        "models": [
            ("claude-opus-4-5", "最强模型"),
            ("claude-sonnet-4", "平衡能力和速度"),
            ("claude-3-5-haiku", "快速响应"),
        ],
    },
}


def select_model_for_provider(provider_id: str, current_model: str) -> str:
    """交互式选择供应商模型"""
    if provider_id == "ollama":
        return select_ollama_model()

    if provider_id not in PROVIDER_MODELS:
        print(f"\n{provider_id} 不支持模型切换")
        return ""

    config = PROVIDER_MODELS[provider_id]
    models = config["models"]
    env_key = config["env_key"]

    print(f"\n可用模型:\n")
    for i, (model_id, desc) in enumerate(models, 1):
        current = " (当前)" if model_id == current_model else ""
        print(f"  {i}. {model_id}{current}")
        print(f"     {desc}")
        print()

    while True:
        choice = input(f"请选择模型 (1-{len(models)}，或 q 取消): ").strip()

        if choice.lower() == 'q':
            print("已取消")
            return ""

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx][0]
                save_api_key_to_env(env_key, selected)
                print(f"\n已选择: {selected}")
                return selected
        except ValueError:
            pass

        print("无效选择，请重新输入")


OLLAMA_RECOMMENDED_MODELS = [
    ("qwen2.5", "7B, 4.4GB", "通用对话，中英文"),
    ("llama3.3", "70B, 43GB", "强大，需大显存"),
    ("deepseek-r1", "7B, 4.7GB", "推理能力强"),
    ("gemma2", "9B, 5.4GB", "Google 开源"),
    ("phi3", "3.8B, 2.3GB", "微软，轻量快速"),
    ("mistral", "7B, 4.1GB", "欧洲开源"),
]


def show_ollama_recommended_models():
    """显示 Ollama 推荐模型列表"""
    print("\n推荐模型:\n")
    for i, (name, size, desc) in enumerate(OLLAMA_RECOMMENDED_MODELS, 1):
        print(f"  {i}. {name}")
        print(f"     {size} | {desc}")
        print()
    print(f"  0. 手动输入模型名")
    print()


def select_ollama_model() -> str:
    """交互式选择 Ollama 模型"""
    print("\n正在检查 Ollama 模型...")

    models = get_ollama_models()

    if not models:
        print("\n未找到已安装的 Ollama 模型")
        show_ollama_recommended_models()

        while True:
            choice = input(f"请选择模型 (1-{len(OLLAMA_RECOMMENDED_MODELS)}，或 0 手动输入): ").strip()

            if choice == "0":
                model = input("输入模型名: ").strip()
                if model:
                    break
                continue

            try:
                idx = int(choice) - 1
                if 0 <= idx < len(OLLAMA_RECOMMENDED_MODELS):
                    model = OLLAMA_RECOMMENDED_MODELS[idx][0]
                    break
            except ValueError:
                pass
            print("无效选择，请重新输入")

        print(f"\n已选择 {model}，首次使用会自动下载")
        save_api_key_to_env("OLLAMA_MODEL", model)
        return model

    print(f"\n已安装的 Ollama 模型:\n")
    for i, model in enumerate(models, 1):
        # 标记当前使用的模型
        current = " (当前)" if model == settings.ollama_model else ""
        print(f"  {i}. {model}{current}")

    print()
    print("  0. 下载新模型")
    print()

    while True:
        choice = input(f"请选择模型 (1-{len(models)}，或 0 下载新模型): ").strip()

        if choice == "0":
            # 显示推荐模型列表
            show_ollama_recommended_models()

            while True:
                sub_choice = input(f"请选择模型 (1-{len(OLLAMA_RECOMMENDED_MODELS)}，或 0 手动输入): ").strip()

                if sub_choice == "0":
                    model = input("输入模型名: ").strip()
                    if model:
                        save_api_key_to_env("OLLAMA_MODEL", model)
                        print(f"\n已选择 {model}，首次使用会自动下载")
                        return model
                    continue

                try:
                    idx = int(sub_choice) - 1
                    if 0 <= idx < len(OLLAMA_RECOMMENDED_MODELS):
                        model = OLLAMA_RECOMMENDED_MODELS[idx][0]
                        save_api_key_to_env("OLLAMA_MODEL", model)
                        print(f"\n已选择 {model}，首次使用会自动下载")
                        return model
                except ValueError:
                    pass
                print("无效选择，请重新输入")

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(models):
                selected = models[idx]
                save_api_key_to_env("OLLAMA_MODEL", selected)
                print(f"\n已选择: {selected}")
                return selected
        except ValueError:
            pass

        print("无效选择，请重新输入")


def prompt_for_api_key(provider_name: str, key_name: str, get_url: str) -> str:
    """提示用户输入 API Key"""
    print(f"\n{'='*50}")
    print(f"首次使用 {provider_name}，需要配置 API Key")
    print(f"{'='*50}")
    print(f"获取地址: {get_url}")
    print()

    while True:
        api_key = input("请粘贴你的 API Key (输入 q 退出): ").strip()

        if api_key.lower() == 'q':
            print("已取消")
            sys.exit(0)

        if not api_key:
            print("API Key 不能为空，请重新输入")
            continue

        # 保存到 .env
        if save_api_key_to_env(key_name, api_key):
            print(f"\n已保存到 .env 文件")
            return api_key
        else:
            print("保存失败，请手动编辑 .env 文件")
            sys.exit(1)


# Provider 选项配置
PROVIDER_OPTIONS = [
    {
        "id": "qwen",
        "name": "Qwen (通义千问)",
        "desc": "免费 2000 请求/天 | 模型: qwen-plus, qwen-max, qwen-turbo",
        "needs_key": True,
    },
    {
        "id": "gemini",
        "name": "Google Gemini",
        "desc": "免费 | 模型: gemini-3-flash, gemini-2.5-pro, gemini-2.0-flash",
        "needs_key": True,
    },
    {
        "id": "ollama",
        "name": "Ollama (本地)",
        "desc": "完全免费 | 推荐: qwen2.5, llama3.3, deepseek-r1",
        "needs_key": False,
    },
    {
        "id": "opencode",
        "name": "OpenCode Zen",
        "desc": "Big Pickle 免费 | 其他模型需订阅",
        "needs_key": True,
    },
    {
        "id": "claude",
        "name": "Claude",
        "desc": "需要会员 | 模型: claude-opus-4-5, claude-sonnet-4",
        "needs_key": True,
    },
]


def get_provider_key_status(provider_id: str) -> str:
    """检查 Provider 是否已配置 API Key，返回状态标记"""
    env_path = Path(".env")
    if not env_path.exists():
        return ""

    content = env_path.read_text(encoding="utf-8")

    # 各 Provider 对应的 KEY 名称
    key_mapping = {
        "qwen": "QWEN_API_KEY",
        "gemini": "GOOGLE_API_KEY",
        "opencode": "OPENCODE_API_KEY",
        "synthetic": "SYNTHETIC_API_KEY",
        "claude": "ANTHROPIC_API_KEY",
    }

    # 不需要 Key 的 Provider
    if provider_id == "ollama":
        return " ✓"

    key_name = key_mapping.get(provider_id)
    if not key_name:
        return ""

    for line in content.split("\n"):
        if line.startswith(f"{key_name}="):
            value = line.split("=", 1)[1].strip()
            if value:
                return " ✓"
    return ""


def select_provider_interactive(show_welcome: bool = True) -> str:
    """交互式选择 LLM Provider"""
    if show_welcome:
        print("\n" + "=" * 50)
        print("欢迎使用 LIFEE - 辩论式 AI 决策助手")
        print("=" * 50)
    else:
        print("\n" + "=" * 50)
        print("切换 LLM Provider")
        print("=" * 50)

    print("\n请选择 LLM Provider (✓ 表示已配置):\n")

    for i, opt in enumerate(PROVIDER_OPTIONS, 1):
        status = get_provider_key_status(opt["id"])
        print(f"  {i}. {opt['name']}{status}")
        print(f"     {opt['desc']}")
        print()

    while True:
        choice = input("请输入序号 (1-7，或 q 取消): ").strip()

        if choice.lower() == 'q':
            if show_welcome:
                print("已取消")
                sys.exit(0)
            else:
                print("已取消切换")
                return ""

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(PROVIDER_OPTIONS):
                selected = PROVIDER_OPTIONS[idx]
                provider_id = selected["id"]

                # 保存选择到 .env
                save_api_key_to_env("LLM_PROVIDER", provider_id)
                print(f"\n已选择: {selected['name']}")

                return provider_id
            else:
                print("无效的序号，请重新输入")
        except ValueError:
            print("请输入有效的数字")


from lifee.providers import (
    LLMProvider,
    Message,
    MessageRole,
    ClaudeProvider,
    SyntheticProvider,
    QwenPortalProvider,
    QwenProvider,
    OllamaProvider,
    OpenCodeZenProvider,
    GeminiProvider,
    read_clawdbot_qwen_credentials,
    read_clawdbot_synthetic_credentials,
)
from lifee.sessions import Session, SessionStore


def reload_settings():
    """重新加载配置"""
    from importlib import reload
    import sys
    # 获取实际的模块对象
    settings_module = sys.modules.get('lifee.config.settings')
    if settings_module is not None:
        reload(settings_module)
    # 更新全局 settings 引用
    global settings
    from lifee.config.settings import settings as new_settings
    settings = new_settings
    return new_settings


def create_provider(provider_name: str = None) -> LLMProvider:
    """根据配置创建 LLM Provider

    Args:
        provider_name: 指定的 Provider 名称，如果为 None 则从配置读取
    """
    if provider_name is None:
        provider_name = settings.llm_provider.lower()
    else:
        provider_name = provider_name.lower()

    if provider_name == "claude":
        api_key = settings.get_anthropic_api_key()
        if not api_key:
            print("\n错误: 未找到 Claude 认证凭据")
            print("解决方法:")
            print("  1. 运行 'claude login' 登录 Claude Code")
            print("  2. 或设置环境变量 ANTHROPIC_API_KEY")
            sys.exit(1)
        return ClaudeProvider(api_key=api_key, model=settings.claude_model)

    elif provider_name == "synthetic":
        # 尝试从环境变量或 clawdbot 获取 API Key
        api_key = settings.synthetic_api_key
        if not api_key:
            # 尝试从 clawdbot 获取
            api_key = read_clawdbot_synthetic_credentials()
        if not api_key:
            api_key = prompt_for_api_key(
                "Synthetic (免费大模型代理)",
                "SYNTHETIC_API_KEY",
                "https://synthetic.new/"
            )
        return SyntheticProvider(
            api_key=api_key,
            model=settings.synthetic_model,
        )

    elif provider_name == "qwen":
        api_key = settings.qwen_api_key
        if not api_key:
            api_key = prompt_for_api_key(
                "Qwen (通义千问)",
                "QWEN_API_KEY",
                "https://dashscope.console.aliyun.com/"
            )
        return QwenProvider(api_key=api_key, model=settings.qwen_model)

    elif provider_name == "gemini":
        api_key = settings.google_api_key
        if not api_key:
            api_key = prompt_for_api_key(
                "Google Gemini",
                "GOOGLE_API_KEY",
                "https://aistudio.google.com/apikey"
            )
        return GeminiProvider(api_key=api_key, model=settings.gemini_model)

    elif provider_name == "ollama":
        # 检查是否需要选择模型（首次使用或模型未设置）
        model = settings.ollama_model
        if not model or model == "qwen2.5":
            # 检查是否有已安装的模型
            installed_models = get_ollama_models()
            if installed_models and model not in installed_models:
                # 当前配置的模型未安装，让用户选择
                model = select_ollama_model()
                reload_settings()
                model = settings.ollama_model

        return OllamaProvider(
            model=model,
            base_url=settings.ollama_base_url,
        )

    elif provider_name == "opencode":
        api_key = settings.opencode_api_key
        if not api_key:
            api_key = prompt_for_api_key(
                "OpenCode Zen (GLM-4.7 免费)",
                "OPENCODE_API_KEY",
                "https://opencode.ai/"
            )
        return OpenCodeZenProvider(
            api_key=api_key,
            model=settings.opencode_model,
        )

    else:
        print(f"\n错误: 未知的 Provider: {provider_name}")
        print("支持的 Provider: claude, synthetic, qwen, gemini, ollama, opencode")
        sys.exit(1)


async def chat_loop(provider: LLMProvider, session: Session) -> str:
    """主对话循环

    Returns:
        "" - 正常退出
        provider_id - 需要切换到的新 Provider
    """
    print("\n" + "=" * 50)
    print("LIFEE - 辩论式 AI 决策助手")
    print("=" * 50)
    print(f"当前: {provider.name} ({provider.model})")
    print("输入 /help 查看帮助，/quit 退出")
    print("=" * 50 + "\n")

    while True:
        try:
            # 获取用户输入
            user_input = input("你: ").strip()

            if not user_input:
                continue

            # 处理命令
            if user_input.startswith("/"):
                cmd = user_input.lower()
                if cmd == "/quit" or cmd == "/exit":
                    print("\n再见！")
                    return ""
                elif cmd == "/help":
                    print("\n命令列表:")
                    print("  /help    - 显示帮助")
                    print("  /history - 显示对话历史")
                    print("  /clear   - 清空对话历史")
                    print("  /config  - 切换 LLM Provider")
                    print("  /model   - 切换当前 Provider 的模型")
                    print("  /quit    - 退出程序")
                    print()
                    continue
                elif cmd == "/config":
                    new_provider_id = select_provider_interactive(show_welcome=False)
                    if new_provider_id:
                        return new_provider_id  # 返回新 Provider ID，触发切换
                    continue
                elif cmd == "/model":
                    # 获取当前 Provider ID
                    provider_id = settings.llm_provider.lower()
                    current_model = provider.model

                    # 检查是否支持模型切换
                    if provider_id == "qwen-portal":
                        print("\nQwen Portal 不支持模型切换")
                        print("可选模型固定为: coder-model, vision-model\n")
                        continue

                    new_model = select_model_for_provider(provider_id, current_model)
                    if new_model:
                        return provider_id  # 触发重新加载
                    continue
                elif cmd == "/history":
                    if not session.history:
                        print("\n[对话历史为空]\n")
                    else:
                        print("\n--- 对话历史 ---")
                        for i, msg in enumerate(session.history, 1):
                            role = "你" if msg.role == MessageRole.USER else "AI"
                            content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
                            print(f"{i}. [{role}] {content}")
                        print("--- 共 {} 条消息 ---\n".format(len(session.history)))
                    continue
                elif cmd == "/clear":
                    session.clear_history()
                    print("\n[对话历史已清空]\n")
                    continue
                else:
                    print(f"\n未知命令: {cmd}，输入 /help 查看帮助\n")
                    continue

            # 添加用户消息到历史
            session.add_user_message(user_input)

            # 准备消息列表
            messages = session.get_messages()

            # 系统提示词（简单版本）
            system_prompt = """你是 LIFEE 的 AI 助手，一个辩论式决策助手。
你的职责是帮助用户思考人生决策问题，提供多角度的观点和建议。
保持友好、专业的态度，用中文回复。"""

            # 流式输出
            print("\nAI: ", end="", flush=True)
            full_response = ""

            async for chunk in provider.stream(
                messages=messages,
                system=system_prompt,
                temperature=0.7,
            ):
                print(chunk, end="", flush=True)
                full_response += chunk

            print("\n")

            # 添加助手消息到历史
            session.add_assistant_message(full_response)

        except KeyboardInterrupt:
            print("\n\n[中断] 再见！")
            return ""
        except Exception as e:
            print(f"\n[错误] {e}\n")
            if settings.debug:
                import traceback
                traceback.print_exc()

    return ""


def check_first_run() -> bool:
    """检查是否是首次运行（没有配置 .env）"""
    env_path = Path(".env")
    if not env_path.exists():
        return True

    # 检查 LLM_PROVIDER 是否有值
    content = env_path.read_text(encoding="utf-8")
    for line in content.split("\n"):
        if line.startswith("LLM_PROVIDER="):
            value = line.split("=", 1)[1].strip()
            # 如果是默认值 claude 且没有 API key，也算首次
            if value and value != "claude":
                return False
            # claude 需要检查是否有认证
            if value == "claude":
                from lifee.config.settings import settings
                if settings.get_anthropic_api_key():
                    return False
    return True


async def main():
    """主函数"""
    # 检查是否首次运行，显示交互式选择
    if check_first_run():
        select_provider_interactive()
        reload_settings()

    # 初始化会话存储（Phase 1 使用内存存储）
    store = SessionStore(storage_dir=None)

    # 创建新会话
    session = store.create()

    # 当前 Provider ID（用于切换检测）
    current_provider_id = None

    # 主循环：支持热切换 Provider
    while True:
        # 重新加载配置以获取最新的 Provider 设置
        reload_settings()

        # 创建 Provider
        provider = create_provider()
        current_provider_id = settings.llm_provider.lower()

        # 启动对话循环
        result = await chat_loop(provider, session)

        if not result:
            # 用户退出
            break
        else:
            # 用户切换了 Provider，重新加载
            print(f"\n正在切换到 {result}...")
            continue


if __name__ == "__main__":
    asyncio.run(main())
