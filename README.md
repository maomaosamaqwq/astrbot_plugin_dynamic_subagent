# Dynamic SubAgent Plugin / 动态子代理插件

让 AI 可以通过 **tool call 动态创建子 Agent**，每个子 Agent 自动注册为 HandoffTool，主 AI 可直接 handoff 任务给它。
支持 transient（用完即焚）和 persistent（跨对话持久化）双生命周期。

## 功能

- **动态创建** — AI 调用 `spawn_agent` 创建子 Agent，即刻可用
- **Handoff 转交** — 每个子 Agent 生成 `transfer_to_<name>` 工具，主 AI 可直接 handoff
- **双生命周期** — transient（内存级，用完即焚）/ persistent（KVStore 持久化，重启恢复）
- **权限分级** — safe（只读）/ medium（含 Python/Shell）/ full（全部工具）
- **模型过滤** — 黑名单/白名单，防止 AI 选到昂贵或不稳定的模型
- **WebUI 管理** — 可视化查看/创建/销毁子 Agent
- **安全熔断** — handoff 次数上限、spawn 次数上限、参数校验、嵌套深度限制
- **协作追踪** — 记录子 Agent 调用链路，可生成图片报告

> 💡 这是 **Handoff 流派** 的实现。另有一个 **委派流派** 的姊妹插件 [astrbot_plugin_subagent_worktogether](https://github.com/ScarletAugus/astrbot_plugin_subagent_worktogether) 支持链式委派和追踪报告。

## 安装

```bash
# 通过 AstrBot 插件市场安装 (待上线)
# 或手动克隆
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

然后在 AstrBot WebUI → 插件管理 → 加载插件。

## 前置条件

- AstrBot **v3.5.19+**（自动发现继承 `Star` 的类）

## AI 可用工具

| 工具 | 描述 |
|------|------|
| `spawn_agent` | 创建一个子 Agent，自动注册 HandoffTool |
| `list_agents` | 查看所有活跃的子 Agent |
| `delete_agent` | 按 agent_id 销毁子 Agent |
| `show_collaboration_report` | 生成子 Agent 协作追踪图片报告 |

### spawn_agent 参数

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `name` | string | - | **必填**。子 Agent 名称，会生成 `transfer_to_<name>` 工具 |
| `system_prompt` | string | "" | 系统提示词，定义角色和行为 |
| `provider_id` | string | "" | 使用的模型/Provider ID，留空继承主 Agent |
| `permission_level` | string | "safe" | `safe` / `medium` / `full` |
| `lifecycle` | string | "transient" | `transient` / `persistent` |
| `tools` | array | null | 工具列表，null 继承主 Agent |
| `max_depth` | int | 3 | 最大 handoff 嵌套深度 (1-10) |
| `max_per_event` | int | 5 | 单次对话最大创建次数 (1-50) |
| `timeout` | float | 120 | 子 Agent 超时秒数 (5-600) |

### 使用示例

1. 用户说："创建一个翻译助手"
2. AI 调用 `spawn_agent(name="翻译助手", system_prompt="你是一个专业中英翻译")`
3. 插件返回：`transfer_to_翻译助手` 工具已注册
4. AI 调用 `transfer_to_翻译助手` 转交翻译任务
5. 翻译助手处理完成后，控制权回到主 AI
6. AI 调用 `show_collaboration_report` 生成协作报告

## 安全机制

| 防护层 | 说明 |
|--------|------|
| Handoff 熔断 | 单次对话 handoff 超过 **20 次** 自动移除所有 HandoffTool |
| Spawn 上限 | 单次对话最多创建 **10 个** 子 Agent |
| 参数校验 | name/权限/深度/超时等参数严格校验 |
| 模型过滤 | 黑名单/白名单双重模式 |
| 嵌套深度 | 子 Agent 可配置最大嵌套深度 |

## WebUI

插件注册了 `/plugin/subagent/dashboard` 页面，可在 AstrBot 管理面板查看：
- 所有子 Agent 列表（在线/离线状态）
- 手动创建/销毁子 Agent
- 协作追踪记录

## 配置

在 `metadata.yaml` 中配置：

```yaml
model_blacklist:
  - "gpt-5-turbo"
  - "claude-4-opus"
model_filter_mode: "blacklist"  # blacklist | whitelist
allowed_models: []              # whitelist 模式下有效
max_handoffs_per_event: 20      # handoff 熔断阈值
max_spawns_per_event: 10        # spawn 上限
default_max_depth: 3            # 默认嵌套深度
default_timeout: 120.0          # 默认超时(秒)
trace_enabled: true             # 协作追踪开关
```

## 版本历史

- **v0.3.0** — 安全熔断（handoff/spawn 上限）、参数校验、协作追踪报告
- **v0.2.0** — HandoffTool 集成 + WebUI 管理页面
- **v0.1.0** — 4 个 Tool + 双生命周期

## 与其他插件的关系

- [astrbot_plugin_subagent_worktogether](https://github.com/ScarletAugus/astrbot_plugin_subagent_worktogether) — 同一作者的不同思路，**委派流派**，支持链式委派、追踪报告和安全熔断。两个插件可以并存互补。

## License

MIT
