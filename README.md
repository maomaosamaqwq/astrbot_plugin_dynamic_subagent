# Dynamic SubAgent for AstrBot

让 AstrBot 的 AI **通过 Tool Call 动态创建子 Agent**，并将其注册为可调用的 `HandoffTool`。

## 核心能力

- 🧬 **动态生成** — AI 调用 `spawn_agent` 实时创建子 Agent，自动注册为 HandoffTool
- 🔄 **一键 Handoff** — 创建后主 AI 直接调用 `transfer_to_<name>` 转交任务，子 Agent 独立执行
- 🔥 **用完即焚 / 持久化** — transient（对话级）和 persistent（跨对话）双生命周期
- 🛡️ **权限分级** — safe / medium / full 三级工具访问权限
- 🤖 **多模型支持** — 子 Agent 可指定不同的 provider
- 🚫 **模型黑名单/白名单** — 防止 AI 选择昂贵或不稳定的模型

## 工作流程

```
用户: "帮我写一个数据分析脚本"

AI 调用 spawn_agent("代码专家", prompt="你精通Python数据分析...")
  → 插件创建 Agent + 注册 HandoffTool

AI 看到多了个 transfer_to_代码专家 tool
  → 调用 transfer_to_代码专家("分析这个数据...")
  → Handoff：控制权转交给子 Agent

代码专家（子 Agent）:
  → 自己的 system_prompt + 工具
  → 独立执行任务
  → 返回结果

AI 收到结果，总结回复用户
```

## 安装

将插件目录放入 AstrBot 的 `addons` 目录，或在管理面板中搜索安装。

## 配置

编辑 `astrbot_plugin_dynamic_subagent.yaml`：

```yaml
model_blacklist:
  - "openai/gpt-4o"
  - "anthropic/claude-sonnet-4"

model_filter_mode: blacklist  # blacklist | whitelist

allowed_models:
  - "deepseek/deepseek-chat"
  - "openai/gpt-4o-mini"
```

## Tool 列表

| Tool | 说明 |
|------|------|
| `spawn_agent` | 创建子 Agent + 注册为 HandoffTool |
| `list_agents` | 查看所有活跃子 Agent 及其状态 |
| `delete_agent` | 销毁子 Agent，移除对应的 tool |
| `transfer_to_<name>` | （自动生成）向指定子 Agent handoff 任务 |

## 示例对话

```
🧑 帮我查一下最新的 AI 新闻，然后翻译成中文

🤖 我来创建一个搜索专家子 Agent 来处理。
    (spawn_agent → 创建 "搜索助手")
    搜索助手已就绪，我来 handoff 给它。
    (transfer_to_搜索助手 → 子 Agent 搜索 + 整理)
    根据搜索专家返回的结果：
    1. GPT-5 发布...
    2. ...
```

## 插件开发

```python
# 创建子 Agent
result = await spawn_agent(
    name="翻译专家",
    system_prompt="你是一个精通多国语言的翻译专家...",
    provider_id="openai/gpt-4o",
    permission_level="safe",
    lifecycle="transient"
)

# 查看活跃子 Agent
agents = await list_agents()

# 销毁
await delete_agent(agent_id="xxx")
```

## 许可证

MIT
