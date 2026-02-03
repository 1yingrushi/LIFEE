"""命令行前端，通过 API 调用 backend FastAPI 服务

实现与 backend/main.py 完全相同的交互式功能，但所有操作都通过 HTTP API 调用。

用法（在项目根目录执行）:
    python -m test.backend_chat_cli

要求:
    - 后端已启动: uvicorn backend.app:app --reload
    - 已在 backend/.env 配置好 LLM_PROVIDER、API Key 等
"""

import json
import sys
from pathlib import Path
from typing import Optional

import requests


API_BASE = "http://127.0.0.1:8000"


class BackendAPIClient:
    """后端 API 客户端封装"""

    def __init__(self, base_url: str = API_BASE):
        self.base_url = base_url
        self.session = requests.Session()
        self.current_role: str = ""

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        """GET 请求"""
        resp = self.session.get(f"{self.base_url}{path}", params=params, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json_data: Optional[dict] = None) -> dict:
        """POST 请求"""
        resp = self.session.post(f"{self.base_url}{path}", json=json_data, timeout=120)
        resp.raise_for_status()
        return resp.json()

    def get_info(self) -> dict:
        """获取后端基本信息"""
        return self._get("/")

    def list_roles(self) -> list[dict]:
        """获取角色列表（带详细信息）"""
        data = self._get("/roles/info")
        return data["roles"]

    def get_history(self) -> list[dict]:
        """获取对话历史"""
        data = self._get("/history")
        return data["messages"]

    def clear_history(self):
        """清空对话历史"""
        self._post("/clear")

    def get_memory_status(self, role: Optional[str] = None) -> dict:
        """获取知识库状态"""
        params = {}
        if role:
            params["role"] = role
        return self._get("/memory/status", params=params)

    def search_memory(self, query: str, role: Optional[str] = None, max_results: int = 5) -> list[dict]:
        """搜索知识库"""
        payload = {"query": query, "max_results": max_results}
        if role:
            payload["role"] = role
        data = self._post("/memory/search", json_data=payload)
        return data["results"]

    def chat(self, message: str, role: Optional[str] = None) -> dict:
        """发送对话消息"""
        payload = {"message": message}
        if role:
            payload["role"] = role
        return self._post("/chat", json_data=payload)

    def debate_round(
        self,
        user_input: str,
        role_names: Optional[list[str]] = None,
    ) -> dict:
        """多智能体辩论一轮"""
        payload = {"user_input": user_input}
        if role_names:
            payload["role_names"] = role_names
        return self._post("/debate/round", json_data=payload)


def run_debate_mode(client: BackendAPIClient):
    """运行多智能体辩论模式"""
    print("\n" + "=" * 50)
    print("多智能体辩论模式")
    print("=" * 50)
    print("提示: 输入 /debate quit 退出辩论模式")
    print("提示: 输入 /debate next 继续下一轮（不输入用户内容）")
    print("提示: 输入数字选择选项，或直接输入文本作为用户输入")
    print("=" * 50 + "\n")

    # 获取可用角色列表
    try:
        roles_info = client.list_roles()
        if not roles_info:
            print("\n[错误] 没有可用的角色，请在 backend/roles/ 下创建角色\n")
            return
        
        if len(roles_info) < 2:
            print(f"\n[错误] 只有 {len(roles_info)} 个角色，辩论需要至少 2 个角色\n")
            return
        
        # 显示可用角色
        print("可用角色:")
        for i, role_info in enumerate(roles_info, 1):
            role_name = role_info["name"]
            display_name = role_info.get("display_name") or role_name
            print(f"  {i}. {role_name} ({display_name})")
        print()
        
        # 选择角色（默认使用所有角色）
        choice = input("选择参与辩论的角色（输入数字，多个用逗号分隔，或直接回车使用所有角色）: ").strip()
        selected_role_names = []
        if choice:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(",")]
                selected_role_names = [roles_info[i]["name"] for i in indices if 0 <= i < len(roles_info)]
            except (ValueError, IndexError):
                print("\n[错误] 无效的选择，使用所有角色\n")
                selected_role_names = [r["name"] for r in roles_info]
        else:
            selected_role_names = [r["name"] for r in roles_info]
        
        if len(selected_role_names) < 2:
            print("\n[错误] 至少需要选择 2 个角色\n")
            return
        
        print(f"\n已选择角色: {', '.join(selected_role_names)}\n")
    except Exception as e:
        print(f"\n[错误] 获取角色列表失败: {e}\n")
        return

    round_num = 0
    current_user_input = None

    while True:
        try:
            # 显示当前轮次
            round_num += 1
            print(f"\n--- 第 {round_num} 轮辩论 ---\n")

            # 第一轮需要用户输入
            if round_num == 1 and current_user_input is None:
                print("请输入你的问题或话题:")
                user_input = input().strip()
                if not user_input:
                    print("\n[取消] 输入不能为空，退出辩论模式\n")
                    return
                current_user_input = user_input

            # 调用辩论 API
            try:
                resp = client.debate_round(
                    user_input=current_user_input or "",
                    role_names=selected_role_names,
                )
            except requests.HTTPError as e:
                if e.response.status_code == 502:
                    try:
                        error_data = e.response.json()
                        detail = error_data.get("detail", str(e))
                        print(f"\n[错误] {detail}\n")
                    except Exception:
                        print(f"\n[错误] 模型返回格式错误: {e}\n")
                else:
                    print(f"\n[错误] HTTP {e.response.status_code}: {e}\n")
                return
            except Exception as e:
                print(f"\n[错误] 请求失败: {e}\n")
                return

            # 显示每个角色的发言
            messages = resp.get("messages", [])
            if not messages:
                print("[警告] 本轮没有收到任何发言\n")
            else:
                for msg in messages:
                    role_name = msg.get("persona_id", "")
                    text = msg.get("text", "")
                    # 获取角色的显示名称
                    role_info = next((r for r in roles_info if r["name"] == role_name), None)
                    display_name = role_info.get("display_name") if role_info else role_name
                    emoji = role_info.get("emoji", "") if role_info else ""
                    print(f"{emoji} [{display_name}]: {text}\n")

            # 显示选项
            options = resp.get("options", [])
            if options:
                print("--- 可选行动 ---")
                for i, opt in enumerate(options, 1):
                    print(f"  {i}. {opt}")
                print()

            # 获取用户输入
            user_input = input("你的选择（输入数字选择选项，或输入文本，或 /debate next 继续，/debate quit 退出）: ").strip()

            if not user_input:
                continue

            # 处理命令
            if user_input.lower() == "/debate quit":
                print("\n退出辩论模式\n")
                return
            elif user_input.lower() == "/debate next":
                # 继续下一轮，使用空用户输入
                current_user_input = ""
                continue
            elif user_input.isdigit():
                # 选择选项
                idx = int(user_input)
                if 1 <= idx <= len(options):
                    selected_option = options[idx - 1]
                    current_user_input = selected_option
                    print(f"\n已选择: {selected_option}\n")
                else:
                    print(f"\n[错误] 无效选项编号，请输入 1-{len(options)}\n")
                    continue
            else:
                # 自定义用户输入
                current_user_input = user_input

        except KeyboardInterrupt:
            print("\n\n[中断] 退出辩论模式\n")
            return
        except EOFError:
            print("\n[退出] 退出辩论模式\n")
            return


def select_role_interactive(client: BackendAPIClient) -> str:
    """交互式选择角色"""
    try:
        roles = client.list_roles()
    except Exception as e:
        print(f"\n[错误] 无法获取角色列表: {e}\n")
        return client.current_role

    if not roles:
        print("\n没有可用的角色")
        print("创建角色: 在 backend/roles/ 下创建目录，添加 SOUL.md 文件")
        print("参考模板: backend/roles/_template/\n")
        return client.current_role

    print("\n可用角色:\n")
    print(f"  0. [无角色] (默认对话模式)")
    for i, role_info in enumerate(roles, 1):
        role_name = role_info["name"]
        display_name = role_info.get("display_name") or role_name
        has_knowledge = role_info.get("has_knowledge", False)
        current = " (当前)" if role_name == client.current_role else ""
        knowledge_mark = " [有知识库]" if has_knowledge else ""
        print(f"  {i}. {role_name}{current}{knowledge_mark}")
        if display_name != role_name:
            print(f"     名字: {display_name}")

    print()

    while True:
        choice = input(f"请选择角色 (0-{len(roles)}，或 q 取消): ").strip()

        if choice.lower() == 'q':
            print("已取消")
            return client.current_role

        try:
            idx = int(choice)
            if idx == 0:
                print("\n已切换到: [无角色]")
                return ""
            if 1 <= idx <= len(roles):
                selected = roles[idx - 1]["name"]
                print(f"\n已切换到: {selected}")
                return selected
        except ValueError:
            pass

        print("无效选择，请重新输入")


def main():
    """主函数"""
    # Windows 控制台 UTF-8 编码支持
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stdin.reconfigure(encoding="utf-8")

    client = BackendAPIClient()

    # 检查后端连接
    try:
        info = client.get_info()
    except Exception as e:
        print("=" * 50)
        print("无法连接到后端服务")
        print("=" * 50)
        print(f"错误: {e}")
        print("\n请确保后端已启动:")
        print("  uvicorn backend.app:app --reload")
        sys.exit(1)

    # 显示欢迎信息
    print("\n" + "=" * 50)
    print("LIFEE - 辩论式 AI 决策助手 (API 模式)")
    print("=" * 50)
    print(f"Provider: {info.get('provider', 'unknown')}")
    if client.current_role:
        roles = client.list_roles()
        role_info = next((r for r in roles if r["name"] == client.current_role), None)
        if role_info:
            display_name = role_info.get("display_name") or client.current_role
            print(f"角色: {display_name}")
            if role_info.get("has_knowledge"):
                print(f"知识库: 已启用")
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
                    print("  /role    - 切换角色")
                    print("  /memory  - 显示知识库状态")
                    print("  /memory search <query> - 搜索知识库")
                    print("  /debate  - 启动多智能体辩论模式")
                    print("  /quit    - 退出程序")
                    print()
                    continue
                elif cmd == "/history":
                    try:
                        messages = client.get_history()
                        if not messages:
                            print("\n[对话历史为空]\n")
                        else:
                            print("\n--- 对话历史 ---")
                            for i, msg in enumerate(messages, 1):
                                role = "你" if msg["role"] == "user" else "AI"
                                content = msg["content"]
                                preview = content[:100] + "..." if len(content) > 100 else content
                                print(f"{i}. [{role}] {preview}")
                            print(f"--- 共 {len(messages)} 条消息 ---\n")
                    except Exception as e:
                        print(f"\n[错误] 获取历史失败: {e}\n")
                    continue
                elif cmd == "/clear":
                    try:
                        client.clear_history()
                        print("\n[对话历史已清空]\n")
                    except Exception as e:
                        print(f"\n[错误] 清空历史失败: {e}\n")
                    continue
                elif cmd == "/role":
                    new_role = select_role_interactive(client)
                    if new_role != client.current_role:
                        client.current_role = new_role
                        # 如果切换了角色，显示更新后的状态
                        if new_role:
                            roles = client.list_roles()
                            role_info = next((r for r in roles if r["name"] == new_role), None)
                            if role_info and role_info.get("has_knowledge"):
                                print(f"提示: 角色 {new_role} 有知识库，对话时会自动检索相关内容")
                    continue
                elif cmd == "/memory" or cmd.startswith("/memory "):
                    if not client.current_role:
                        print("\n当前没有选择角色")
                        print("使用方法: 先用 /role 选择一个有知识库的角色\n")
                        continue
                    # /memory status
                    if cmd == "/memory":
                        try:
                            status = client.get_memory_status(client.current_role)
                            if not status.get("enabled"):
                                print("\n当前角色没有知识库")
                                print("创建方法: 在角色目录下创建 knowledge/ 目录，添加 .md 文件\n")
                            else:
                                print("\n知识库状态:")
                                print(f"  文件数: {status['file_count']}")
                                print(f"  分块数: {status['chunk_count']}")
                                print(f"  嵌入模型: {status['embedding_provider']}/{status['embedding_model']}")
                                print()
                        except Exception as e:
                            print(f"\n[错误] 获取知识库状态失败: {e}\n")
                        continue
                    # /memory search <query>
                    if cmd.startswith("/memory search "):
                        query = user_input[15:].strip()
                        if not query:
                            print("\n用法: /memory search <查询内容>\n")
                            continue
                        try:
                            print(f"\n搜索: {query}")
                            results = client.search_memory(query, role=client.current_role, max_results=5)
                            if not results:
                                print("没有找到相关内容\n")
                            else:
                                print(f"找到 {len(results)} 条结果:\n")
                                for i, r in enumerate(results, 1):
                                    filename = Path(r["path"]).name
                                    print(f"[{i}] {filename}:{r['start_line']}-{r['end_line']} (分数: {r['score']:.2f})")
                                    preview = r["text"][:100].replace("\n", " ")
                                    print(f"    {preview}...")
                                    print()
                        except Exception as e:
                            print(f"\n[错误] 搜索失败: {e}\n")
                        continue
                    print("\n未知的 /memory 子命令")
                    print("用法:")
                    print("  /memory         - 显示知识库状态")
                    print("  /memory search <query> - 搜索知识库\n")
                    continue
                elif cmd == "/debate":
                    try:
                        run_debate_mode(client)
                    except Exception as e:
                        print(f"\n[错误] 辩论模式失败: {e}\n")
                    continue
                else:
                    print(f"\n未知命令: {cmd}，输入 /help 查看帮助\n")
                    continue

            # 普通对话
            try:
                resp = client.chat(user_input, role=client.current_role if client.current_role else None)
                reply = resp.get("reply") or resp.get("content") or ""
                provider = resp.get("provider")
                model = resp.get("model")

                meta = []
                if provider:
                    meta.append(f"provider={provider}")
                if model:
                    meta.append(f"model={model}")
                if client.current_role:
                    meta.append(f"role={client.current_role}")

                meta_str = f" ({', '.join(meta)})" if meta else ""
                print(f"\nAI{meta_str}: {reply}\n")
            except requests.HTTPError as e:
                if e.response.status_code == 500:
                    try:
                        error_data = e.response.json()
                        detail = error_data.get("detail", str(e))
                        print(f"\n[错误] {detail}\n")
                    except Exception:
                        print(f"\n[错误] 后端服务错误: {e}\n")
                else:
                    print(f"\n[错误] HTTP {e.response.status_code}: {e}\n")
            except Exception as e:
                print(f"\n[错误] 请求失败: {e}\n")

        except KeyboardInterrupt:
            print("\n\n[中断] 再见！")
            break
        except EOFError:
            print("\n[退出]")
            break


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
