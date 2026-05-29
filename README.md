# Dynamic SubAgent Plugin / 动态子代理插件

让 AI 可以通过 **tool call 动态创建和管理子 Agent**，支持跨调用上下文保留、权限分级、协作追踪。

## 功能

- **动态创建** — AI 调用 `spawn_agent` 创建子 Agent，即刻可用
- **统一转交** — 通过 `transfer_to_agent(name, task)` 向任意子 Agent 分配任务
- **上下文保留** — persistent Agent 的对话历史跨调用保留，Agent 能记住之前的事
- **双生命周期** — transient（内存级，用完即焚）/ persistent（持久化，重启恢复）
- **权限分级** — safe（只读工具）/ medium（排除 shell）/ full（全部工具）
- **模型过滤** — 黑名单/白名单，防止 AI 选到昂贵或不稳定的模型
- **协作追踪** — 记录子 Agent 调用链路，可查看协作报告
- **安全熔断** — spawn 上限、参数校验

## 安装

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

在 AstrBot WebUI → 插件管理 → 加载插件。

## 前置条件

- AstrBot **v3.5.19+**

## AI 可用工具

| 工具 | 描述 |
|------|------|
| `spawn_agent` | 创建子 Agent，可选立即执行任务 |
| `transfer_to_agent` | 向已创建的子 Agent 转交任务 |
| `list_agents` | 查看所有活跃的子 Agent |
| `delete_agent` | 销毁子 Agent 并清理上下文 |
| `clear_agent_context` | 清空 Agent 对话历史（不销毁 Agent） |
| `show_collaboration_report` | 查看协作追踪报告 |
| `get_sub_agent_results` | 查询子 Agent 历史执行结果 |

### spawn_agent 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | - | **必填**。子 Agent 名称（英文/数字/下划线） |
| `description` | string | "" | 功能描述 |
| `instruction` | string | "" | 系统指令/行为约束 |
| `task` | string | "" | 任务内容，提供则创建后立即执行 |
| `permission_level` | string | "safe" | `safe` / `medium` / `full` |
| `provider_id` | string | "" | Provider ID，留空继承主 Agent |
| `model` | string | "" | 模型名，留空继承主 Agent |
| `persistent` | bool | false | 是否持久化（跨重启 + 上下文保留） |

### transfer_to_agent 参数

| 参数 | 类型 | 说明 |
|------|------|------|
| `name` | string | **必填**。子 Agent 名称 |
| `task` | string | **必填**。任务描述 |

## 使用示例

```
用户: 创建一个翻译助手，帮我翻译内容

AI: spawn_agent(name="translator", description="中英翻译", instruction="你是专业翻译", task="翻译：Hello World")
→ 子 Agent [translator] 创建并执行任务完成！结果: "你好世界"

用户: 再帮翻译一句

AI: transfer_to_agent(name="translator", task="翻译：Good morning")
→ 子 Agent [translator] 执行完成。（Agent 已有 1 轮历史上下文）
```

### persistent Agent 示例

```
AI: spawn_agent(name="memory_bot", persistent=true, task="记住暗号：大漠孤烟直")
→ Agent 确认存储

AI: transfer_to_agent(name="memory_bot", task="暗号是什么？")
→ Agent: "暗号是大漠孤烟直"  ← 因为上下文已保留
```

## 权限分级

| 权限 | 可用工具 |
|------|---------|
| safe | 搜索工具 + spawn_agent + list_agents + get_sub_agent_results |
| medium | 除 shell/python 外的所有工具 |
| full | 全部工具 |

## 配置

在 AstrBot WebUI 插件配置中设置：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `model_blacklist` | list | [] | 模型黑名单 |
| `model_filter_mode` | string | "blacklist" | 过滤模式：blacklist / whitelist |
| `allowed_models` | list | [] | 白名单（whitelist 模式生效） |
| `max_spawns_per_event` | int | 10 | 最大子 Agent 数量 |
| `max_handoffs_per_event` | int | 20 | handoff 转交次数上限 |
| `max_context_turns` | int | 20 | 每个 Agent 最大历史轮数 |
| `trace_enabled` | bool | true | 是否启用协作追踪 |

## 版本历史

- **v0.6.1** — 配置项接入、代码清理、README 更新
- **v0.6.0** — Bug #2 修复：persistent Agent 上下文跨调用保留
- **v0.5.6** — Bug #1 修复：统一 transfer_to_agent 入口
- **v0.5.5** — transfer_to handler 实际执行（已被 v0.5.6 替代）
- **v0.5.4** — Bug #3/#4/#5 修复
- **v0.3.0** — 安全熔断、参数校验、协作追踪
- **v0.2.0** — HandoffTool 集成 + WebUI
- **v0.1.0** — 基础 CRUD + 双生命周期

## License

MIT
