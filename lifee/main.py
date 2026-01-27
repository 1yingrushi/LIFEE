"""LIFEE CLI 入口"""
import asyncio
import sys

# Windows 控制台 UTF-8 编码支持
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stdin.reconfigure(encoding="utf-8")

from lifee.config.settings import settings
from lifee.providers import (
    LLMProvider,
    Message,
    MessageRole,
    ClaudeProvider,
    QwenProvider,
    OllamaProvider,
    OpenCodeZenProvider,
    GeminiProvider,
)
from lifee.sessions import Session, SessionStore


def create_provider() -> LLMProvider:
    """根据配置创建 LLM Provider"""
    provider_name = settings.llm_provider.lower()

    if provider_name == "claude":
        api_key = settings.get_anthropic_api_key()
        if not api_key:
            print("\n错误: 未找到 Claude 认证凭据")
            print("解决方法:")
            print("  1. 运行 'claude login' 登录 Claude Code")
            print("  2. 或设置环境变量 ANTHROPIC_API_KEY")
            sys.exit(1)
        return ClaudeProvider(api_key=api_key, model=settings.claude_model)

    elif provider_name == "qwen":
        if not settings.qwen_api_key:
            print("\n错误: 未找到 Qwen API Key")
            print("解决方法:")
            print("  在 .env 文件中设置 QWEN_API_KEY")
            print("  获取地址: https://dashscope.console.aliyun.com/")
            sys.exit(1)
        return QwenProvider(api_key=settings.qwen_api_key, model=settings.qwen_model)

    elif provider_name == "gemini":
        if not settings.google_api_key:
            print("\n错误: 未找到 Google API Key")
            print("解决方法:")
            print("  在 .env 文件中设置 GOOGLE_API_KEY")
            print("  获取地址: https://aistudio.google.com/apikey")
            sys.exit(1)
        return GeminiProvider(api_key=settings.google_api_key, model=settings.gemini_model)

    elif provider_name == "ollama":
        return OllamaProvider(
            model=settings.ollama_model,
            base_url=settings.ollama_base_url,
        )

    elif provider_name == "opencode":
        if not settings.opencode_api_key:
            print("\n错误: 未找到 OpenCode API Key")
            print("解决方法:")
            print("  在 .env 文件中设置 OPENCODE_API_KEY")
            sys.exit(1)
        return OpenCodeZenProvider(
            api_key=settings.opencode_api_key,
            model=settings.opencode_model,
        )

    else:
        print(f"\n错误: 未知的 Provider: {provider_name}")
        print("支持的 Provider: claude, qwen, gemini, ollama, opencode")
        sys.exit(1)


async def chat_loop(provider: LLMProvider, session: Session):
    """主对话循环"""
    print("\n" + "=" * 50)
    print("LIFEE - 辩论式 AI 决策助手")
    print("=" * 50)
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
                    break
                elif cmd == "/help":
                    print("\n命令列表:")
                    print("  /help    - 显示帮助")
                    print("  /history - 显示对话历史")
                    print("  /clear   - 清空对话历史")
                    print("  /quit    - 退出程序")
                    print()
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
            break
        except Exception as e:
            print(f"\n[错误] {e}\n")
            if settings.debug:
                import traceback
                traceback.print_exc()


async def main():
    """主函数"""
    # 创建 Provider
    provider = create_provider()

    # 显示模型信息
    print(f"\n[Provider] {provider.name}")
    print(f"[模型] {provider.model}")

    # 初始化会话存储（Phase 1 使用内存存储）
    store = SessionStore(storage_dir=None)

    # 创建新会话
    session = store.create()

    # 启动对话循环
    await chat_loop(provider, session)


if __name__ == "__main__":
    asyncio.run(main())
