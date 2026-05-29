> **Dynamic SubAgent** 🐾
> **Version:** 0.6.4
> **Author:** maomaosamaqwq
> **Type:** AstrBot Plugin
> **Desc:** 具备权限隔离与嵌套深度限制的子 Agent 系统
>
> **特性:**
> 🧠 动态创建 spawn/transfer
> 🔒 三级权限 safe/medium/full
> 🛡 子 Agent 不可再 spawn
> 💾 persistent 持久化记忆
>
> **安装:**
> `AstrBot 插件市场 → dynamic_subagent`

---

**🌐 其他语言 / Other Languages:**

[English](translations/en.md) | [日本語](translations/ja.md) | [한국어](translations/ko.md) | [Español](translations/es.md) | [Français](translations/fr.md) | [Deutsch](translations/de.md) | [Русский](translations/ru.md) | [العربية](translations/ar.md) | [Português](translations/pt.md)

> 📖 更多语言翻译？使用 [Google Translate](https://translate.google.com/translate?sl=zh-CN&tl=en&u=https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/README.md) 自动翻译本页

---

# 🐾 Dynamic SubAgent

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

让 AI 主 Agent 动态创建和管理子 Agent 的 AstrBot 插件，具备**权限隔离**与**嵌套深度限制**的安全体系。

## ✨ 特性

| 特性 | 说明 |
|------|------|
| 🧠 动态创建 | `spawn_agent` 按需创建子 Agent，支持指定权限/模型/持久化 |
| 🔄 任务移交 | `transfer_to_agent` 将任务交给已有子 Agent 执行 |
| 🔒 权限隔离 | `safe` / `medium` / `full` 三级权限，子 Agent 不可越级 |
| 🛡 深度限制 | 子 Agent 无权再创建子 Agent，杜绝无限繁殖链 |
| 💾 持久化记忆 | persistent Agent 跨重启保留 + 上下文历史注入 |
| 🕵️ 协作追踪 | 完整的 spawn/transfer 链路追踪报告 |

## ⚙️ 权限体系

| 权限 | 内置工具 | 插件工具 | 可 spawn | 说明 |
|:----:|:--------:|:--------:|:--------:|------|
| `safe` | ❌ | 白名单 | ❌ | 仅搜索+管理工具 |
| `medium` | 文件读写 | 黑名单过滤 | ❌ | 不含 shell/python |
| `full` | ✅ 全部 | ✅ 全部 | ❌ | 与主 Agent 一致 |

> 子 Agent 永远无法使用 Python/IPython 执行器，且无法创建子 Agent。

## 📦 安装

在 AstrBot 插件市场搜索 `dynamic_subagent` 安装，或手动克隆：

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 快速开始

```python
# 1. 创建子 Agent（带任务立即执行）
spawn_agent(
    name="code_reviewer",
    description="代码审查助手",
    permission_level="medium",
    task="请审查以下代码：..."
)

# 2. 创建持久化子 Agent，后续移交任务
spawn_agent(
    name="memory_bot",
    description="记忆型助手，会记住之前的对话",
    persistent=true
)

transfer_to_agent(
    name="memory_bot",
    task="继续之前的话题..."
)

# 3. 查看协作报告
show_collaboration_report()
```

## ⚙️ 配置

| 配置项 | 默认值 | 说明 |
|--------|:------:|------|
| `max_spawns_per_event` | `10` | 全局子 Agent 创建上限 |
| `max_handoffs_per_event` | `20` | 全局任务移交上限 |
| `max_context_turns` | `20` | persistent Agent 保留的上下文轮数 |
| `trace_enabled` | `true` | 是否启用协作追踪 |
| `model_blacklist` | `[]` | 禁止使用的模型列表 |
| `model_filter_mode` | `blacklist` | 模型过滤模式（blacklist/whitelist） |
| `allowed_models` | `[]` | 白名单模式时的允许模型列表 |

## 🏗 架构

```
主 Agent (depth=0, full)
 └─ spawn_agent() → 子 Agent (depth=1, safe/medium/full)
     └─ transfer_to_agent() → 子 Agent 执行任务
         └─ ❌ 无权再 spawn（depth>=1 拦截）
```

- **嵌套深度**：主 Agent depth=0，子 Agent depth=1 — 无法继续嵌套
- **权限传递**：子 Agent 创建者权限 ≥ 目标权限（medium 不能创建 full）
- **工具隔离**：子 Agent 工具集在 `_build_sub_tools` 中构建，深度≥1 自动移除 spawn/delete

## 📋 可用工具

| 工具 | 说明 |
|------|------|
| `spawn_agent` | 创建子 Agent（仅主 Agent） |
| `transfer_to_agent` | 移交任务给已有子 Agent |
| `list_agents` | 列出所有活跃子 Agent |
| `delete_agent` | 销毁子 Agent（仅主 Agent） |
| `clear_agent_context` | 清空子 Agent 对话历史（仅主 Agent） |
| `show_collaboration_report` | 查看协作追踪报告（仅主 Agent） |
| `get_sub_agent_results` | 查询子 Agent 历史执行结果 |

## 📝 License

MIT
