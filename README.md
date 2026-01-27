# LIFEE - 辩论式 AI 决策助手

Google Hackathon 2025 项目

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置认证 (二选一)

**方式 A: Claude Code OAuth (推荐)**

如果你已安装 Claude Code CLI，直接登录即可：

```bash
claude login
```

程序会自动读取 `~/.claude/.credentials.json` 中的凭据。

**方式 B: API Key**

创建 `.env` 文件：

```bash
cp .env.example .env
```

编辑 `.env`，填入你的 API Key：

```
ANTHROPIC_API_KEY=sk-ant-api-xxxxx
```

### 3. 运行对话

```bash
python -m lifee.main
```

### 4. 使用命令

```
/help    - 显示帮助
/history - 显示对话历史
/clear   - 清空对话历史
/quit    - 退出程序
```

## 项目结构

```
lifee/
├── config/         # 配置管理
├── providers/      # LLM 提供商 (Claude API)
├── sessions/       # 会话管理
├── agents/         # AI 智能体 (待实现)
├── memory/         # 知识库/RAG (待实现)
├── context/        # 上下文注入 (待实现)
└── main.py         # CLI 入口
```

## 开发进度

- [x] Phase 1: 基础对话
- [ ] Phase 2: 上下文注入
- [ ] Phase 3: 知识库/RAG
- [ ] Phase 4: 多智能体辩论
