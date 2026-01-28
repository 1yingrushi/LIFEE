# LIFEE - 辩论式 AI 决策助手

Google Hackathon 2025 项目

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 选择 LLM Provider

支持多种 LLM 提供商，编辑 `.env` 文件选择：

| Provider | 免费额度 | 说明 |
|----------|---------|------|
| **Gemini** | 免费 | Google AI，推荐使用 |
| **Qwen** | 2000次/天 | 阿里通义千问 DashScope API |
| **Qwen Portal** | 2000次/天 | 通过 clawdbot OAuth 登录 |
| **Ollama** | 完全免费 | 本地运行，需安装 Ollama |
| **OpenCode** | $20 起 | 需绑定支付方式 |
| **Claude** | 需付费 | Anthropic Claude API |

### 3. 配置

复制配置文件：

```bash
cp .env.example .env
```

编辑 `.env`，设置 Provider 和对应的 API Key：

```bash
# 选择 Provider
LLM_PROVIDER=gemini

# Gemini (推荐)
GOOGLE_API_KEY=your-api-key

# 或者 Qwen
# LLM_PROVIDER=qwen
# QWEN_API_KEY=your-api-key

# 或者 Ollama (本地)
# LLM_PROVIDER=ollama
# ollama pull qwen2.5
```

### 4. 运行对话

```bash
python -m lifee.main
```

首次运行会让你选择具体模型。

### 5. 使用命令

```
/help    - 显示帮助
/history - 显示对话历史
/clear   - 清空对话历史
/model   - 切换模型
/quit    - 退出程序
```

## 支持的模型

### Gemini
- `gemini-3-flash-preview` - Gemini 3 快速
- `gemini-3-pro-preview` - Gemini 3 最强
- `gemini-2.5-pro` - 2.5 最强
- `gemini-2.5-flash` - 2.5 快速
- `gemini-2.0-flash` - 2.0 推荐

### Qwen
- `qwen-plus` - 通用增强
- `qwen-turbo` - 快速
- `qwen-max` - 最强

### Ollama
- `qwen2.5:latest` - 推荐
- `llama3.3:latest`
- `deepseek-r1:latest`

## 项目结构

```
lifee/
├── config/         # 配置管理
├── providers/      # LLM 提供商 (多 Provider 支持)
├── sessions/       # 会话管理
├── agents/         # AI 智能体 (待实现)
├── memory/         # 知识库/RAG (待实现)
├── context/        # 上下文注入 (待实现)
└── main.py         # CLI 入口
```

## 开发进度

- [x] Phase 1: 基础对话
- [x] 多 LLM Provider 支持
- [ ] Phase 2: 上下文注入
- [ ] Phase 3: 知识库/RAG
- [ ] Phase 4: 多智能体辩论
