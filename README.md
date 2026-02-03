# LIFEE - Let Them Argue

**Multi-perspective life decision assistant.**

LIFEE 是一个基于 FastAPI + Vue.js 的辩论式 AI 决策助手，支持多智能体辩论、角色系统、知识库 RAG 等功能。

## 🏗️ 项目架构

```
LIFEE/
├── backend/          # FastAPI 后端服务
│   ├── app.py       # FastAPI 应用入口
│   ├── config/      # 配置管理
│   ├── providers/   # LLM 提供商 (Claude, Gemini, Qwen, Ollama, SiliconFlow...)
│   ├── sessions/     # 会话管理
│   ├── roles/       # 角色系统
│   ├── memory/      # 知识库/RAG
│   └── debate/      # 多智能体辩论
├── frontend/         # Vue.js + Vite 前端
│   └── src/
│       └── App.vue  # 主应用组件
└── test/            # 测试工具
    └── backend_chat_cli.py  # CLI 测试客户端
```

## 🚀 快速开始

### 1. 后端设置

#### 安装依赖

```bash
cd backend
pip install -r requirements.txt
```

#### 配置环境变量

在 `backend/` 目录下创建 `.env` 文件：

```bash
# 选择 LLM Provider
LLM_PROVIDER=siliconflow  # 或 claude, synthetic, qwen, gemini, ollama, opencode

# SiliconFlow (推荐，OpenAI 兼容)
SILICONFLOW_API_KEY=your-api-key
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_MODEL=Qwen/Qwen2.5-7B-Instruct
SILICONFLOW_EMBEDDING_MODEL=BAAI/bge-large-zh-v1.5

# 备用 Provider (可选，逗号分隔)
LLM_FALLBACK=qwen,ollama

# Gemini (用于向量嵌入，如果使用 Gemini Embedding)
GOOGLE_API_KEY=your-api-key

# 其他 Provider 配置...
# ANTHROPIC_API_KEY=...
# QWEN_API_KEY=...
# OPENAI_API_KEY=...
```

#### 启动后端服务

```bash
# 从项目根目录运行
uvicorn backend.app:app --reload

# 或从 backend 目录运行
cd backend
uvicorn app:app --reload
```

后端将在 `http://127.0.0.1:8000` 启动。

### 2. 前端设置

#### 安装依赖

```bash
cd frontend
npm install
```

#### 启动开发服务器

```bash
npm run dev
```

前端将在 `http://localhost:5173` 启动。

### 3. 访问应用

打开浏览器访问 `http://localhost:5173`，即可使用 LIFEE 应用。

## 📖 使用指南

### 基本流程

1. **输入情境**：在首页输入你的问题或情境描述
2. **选择角色**：从后端加载的角色中选择至少 2 个角色参与辩论
3. **开始辩论**：点击 "Commence Dialogue" 开始多智能体辩论
4. **交互**：查看各角色的观点，选择建议选项或输入新内容继续讨论

### 角色系统

角色定义在 `backend/roles/` 目录下，每个角色包含：

```
backend/roles/<role_name>/
├── SOUL.md           # 核心人格（必需）
├── IDENTITY.md       # 身份信息（可选，包含 Name、Emoji 等）
└── knowledge/        # 专属知识库（可选）
    └── *.md          # Markdown 文档
```

**SOUL.md**：定义角色的核心人格、价值观、说话风格、行为边界

**IDENTITY.md**：角色的元信息，例如：
```markdown
- **Name:** 角色显示名称
- **Emoji:** 🤖
```

**knowledge/**：角色的专属知识库，Markdown 文件会被自动索引，对话时通过语义搜索注入相关内容

### 知识库工作原理

1. **索引阶段**（首次运行或文件更新时）
   - 文档 → 分块（~400 token/块）→ 嵌入向量 → 存入 `knowledge.db`

2. **对话阶段**
   - 用户输入 → 生成查询向量 → 搜索最相似的分块 → 注入到 system prompt → AI 回答

3. **搜索算法**：混合搜索 = 70% 向量相似度 + 30% 关键词匹配

### API 端点

#### 角色相关

- `GET /roles/info` - 获取所有角色信息
- `GET /roles/info/{role_name}` - 获取特定角色信息

#### 对话相关

- `POST /chat` - 单智能体对话
  ```json
  {
    "message": "用户消息",
    "role": "角色名称（可选）"
  }
  ```

#### 辩论相关

- `POST /debate/round` - 多智能体辩论一轮
  ```json
  {
    "user_input": "用户输入（可为空）",
    "role_names": ["role1", "role2"],
    "situation": "情境描述（可选）"
  }
  ```

## 🔧 支持的 LLM Provider

| Provider | 说明 | 配置项 |
|----------|------|--------|
| **SiliconFlow** | 硅基流动（OpenAI 兼容） | `SILICONFLOW_API_KEY`, `SILICONFLOW_BASE_URL`, `SILICONFLOW_MODEL` |
| **Claude** | Anthropic Claude | `ANTHROPIC_API_KEY` |
| **Gemini** | Google Gemini | `GOOGLE_API_KEY` |
| **Qwen** | 阿里通义千问 | `QWEN_API_KEY` |
| **Ollama** | 本地运行 | `OLLAMA_BASE_URL` (默认 http://localhost:11434) |
| **OpenCode Zen** | OpenCode 平台 | `OPENCODE_API_KEY` |
| **Synthetic** | Synthetic 平台 | `SYNTHETIC_API_KEY` |

### 备用 Provider

支持配置备用 Provider，当主 Provider 失败时自动切换：

```bash
LLM_PROVIDER=siliconflow
LLM_FALLBACK=qwen,ollama  # 逗号分隔，按优先级排序
```

## 🧪 测试

### CLI 测试客户端

使用 `test/backend_chat_cli.py` 测试后端 API：

```bash
python -m test.backend_chat_cli
```

支持单智能体对话和多智能体辩论模式。

## 📁 项目结构

```
backend/
├── app.py              # FastAPI 应用入口
├── config/
│   └── settings.py     # 配置管理（从 backend/.env 读取）
├── providers/          # LLM 提供商
│   ├── base.py         # 基础接口
│   ├── claude.py       # Claude Provider
│   ├── gemini.py       # Gemini Provider
│   ├── qwen.py         # Qwen Provider
│   ├── ollama.py       # Ollama Provider
│   ├── siliconflow.py # SiliconFlow Provider
│   ├── fallback.py     # 备用 Provider
│   └── ...
├── sessions/           # 会话管理
├── roles/              # 角色系统
│   └── <role_name>/
│       ├── SOUL.md
│       ├── IDENTITY.md
│       └── knowledge/
├── memory/             # 知识库/RAG
│   ├── manager.py      # 索引管理
│   ├── embeddings.py   # 嵌入提供者
│   ├── search.py       # 混合搜索
│   └── chunker.py      # 文档分块
└── debate/              # 多智能体辩论
    ├── moderator.py     # 主持者
    ├── participant.py   # 参与者
    └── context.py       # 辩论上下文

frontend/
├── src/
│   ├── App.vue         # 主应用组件
│   └── style.css       # 全局样式
├── package.json
└── vite.config.js

test/
└── backend_chat_cli.py # CLI 测试客户端
```

## 🔒 环境变量说明

所有环境变量配置在 `backend/.env` 文件中。主要配置项：

- `LLM_PROVIDER`: 主 LLM Provider
- `LLM_FALLBACK`: 备用 Provider 列表（逗号分隔）
- `SILICONFLOW_API_KEY`: SiliconFlow API Key
- `GOOGLE_API_KEY`: Google API Key（用于 Gemini Embedding）
- `OPENAI_API_KEY`: OpenAI API Key（用于 OpenAI Embedding）
- 其他 Provider 的 API Key...

## 📝 开发说明

### 添加新角色

1. 在 `backend/roles/` 下创建目录，如 `backend/roles/my_role/`
2. 编写 `SOUL.md` 描述人格
3. （可选）添加 `IDENTITY.md` 设置显示名称和 emoji
4. （可选）在 `knowledge/` 下添加知识文档
5. 重启后端服务，角色会自动加载

### 添加新 LLM Provider

1. 在 `backend/providers/` 下创建新的 Provider 类，继承 `LLMProvider`
2. 实现 `chat()` 和 `stream()` 方法
3. 在 `backend/providers/__init__.py` 中导出
4. 在 `backend/config/settings.py` 中添加配置项
5. 在 `backend/app.py` 的 `create_provider_for_api()` 中添加创建逻辑

## 🐛 故障排除

### 后端无法启动

- 检查 `backend/.env` 文件是否存在
- 检查 Python 依赖是否安装完整：`pip install -r backend/requirements.txt`
- 检查端口 8000 是否被占用

### 前端无法连接后端

- 检查后端是否运行在 `http://127.0.0.1:8000`
- 检查 CORS 配置（后端已配置允许 `localhost:5173`）
- 检查浏览器控制台的错误信息

### 角色未显示

- 检查 `backend/roles/` 目录下是否有角色的 `SOUL.md` 文件
- 检查后端日志是否有错误信息
- 使用 `GET /roles/info` API 测试

### 知识库索引失败

- 检查 Embedding Provider 的 API Key 是否正确配置
- 检查知识库文件格式（支持 `.md` 和 `.txt`）
- 查看后端启动日志中的错误信息

## 📄 许可证

MIT License

## 🙏 致谢

- FastAPI - 现代、快速的 Web 框架
- Vue.js - 渐进式 JavaScript 框架
- SiliconFlow - 提供 OpenAI 兼容的 LLM API
- 所有贡献者
