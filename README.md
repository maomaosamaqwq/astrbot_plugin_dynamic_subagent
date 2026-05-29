# Dynamic SubAgent for AstrBot

让 AstrBot 的 AI 可以通过 Tool Call 动态创建和管理子 Agent。

## 功能

- 🧬 **动态生成** — AI 通过 `spawn_agent` tool 实时创建子 Agent
- 🔥 **用完即焚 / 持久化** — 支持 transient 和 persistent 两种生命周期
- 🛡️ **权限分级** — safe / medium / full 三级工具访问权限
- 🤖 **多模型支持** — 子 Agent 可指定不同的 provider
- 🖥️ **WebUI 管理** — 可视化查看和管理子 Agent
- 🚫 **模型黑名单** — 防止 AI 选择昂贵或不稳定的模型

## 快速开始

### 安装

```bash
pip install astrbot_plugin_dynamic_subagent
```

或者手动将插件目录放入 AstrBot 的 `addons` 目录。

### 配置

在 AstrBot 管理面板中配置插件，或编辑 `astrbot_plugin_dynamic_subagent.yaml`：

```yaml
model_blacklist:
  - "openai/gpt-4o"
  - "anthropic/claude-sonnet-4"

model_filter_mode: blacklist  # blacklist | whitelist
```

## Tool 列表

| Tool | 说明 |
|------|------|
| `spawn_agent` | 创建子 Agent |
| `list_agents` | 查看活跃子 Agent |
| `send_to_agent` | 向子 Agent 发送任务 |
| `delete_agent` | 销毁子 Agent |

## 示例

```
用户: 帮我写一个数据分析脚本

AI: 我来创建一个数据分析专家子 Agent 来处理这个任务。
     (调用 spawn_agent)
     (创建成功后 handoff 给子 Agent)
     (子 Agent 完成后返回结果)
```

## 许可证

MIT
