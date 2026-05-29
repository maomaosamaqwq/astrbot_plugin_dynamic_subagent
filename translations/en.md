# 🐾 Dynamic SubAgent — English

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

An AstrBot plugin that enables the main AI Agent to dynamically create and manage sub-Agents, featuring **permission isolation** and **nesting depth limits** for a secure multi-agent system.

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🧠 Dynamic Creation | `spawn_agent` creates sub-Agents on demand with configurable permissions/models/persistence |
| 🔄 Task Transfer | `transfer_to_agent` delegates tasks to existing sub-Agents |
| 🔒 Permission Isolation | Three-tier permissions: `safe` / `medium` / `full` — sub-Agents cannot escalate |
| 🛡 Depth Limiting | Sub-Agents cannot spawn further sub-Agents, preventing infinite chains |
| 💾 Persistent Memory | Persistent Agents retain context across restarts + history injection |
| 🕵️ Collaboration Tracing | Full spawn/transfer chain tracking and reporting |

## ⚙️ Permission System

| Level | Built-in Tools | Plugin Tools | Can Spawn | Description |
|:-----:|:--------------:|:------------:|:---------:|-------------|
| `safe` | ❌ | Whitelist | ❌ | Search + management only |
| `medium` | File R/W | Blacklist filter | ❌ | No shell/python |
| `full` | ✅ All | ✅ All | ❌ | Same as main Agent |

> Sub-Agents can never use Python/IPython executors and cannot create sub-Agents.

## 📦 Installation

Search `dynamic_subagent` in the AstrBot Plugin Marketplace, or clone manually:

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 Quick Start

```python
# 1. Create a sub-Agent with immediate task
spawn_agent(
    name="code_reviewer",
    description="Code review assistant",
    permission_level="medium",
    task="Please review the following code: ..."
)

# 2. Create a persistent sub-Agent for later task transfer
spawn_agent(
    name="memory_bot",
    description="Memory-enabled assistant that remembers conversations",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="Continue our previous topic..."
)

# 3. View collaboration report
show_collaboration_report()
```

## ⚙️ Configuration

| Config | Default | Description |
|--------|:-------:|-------------|
| `max_spawns_per_event` | `10` | Global sub-Agent creation limit |
| `max_handoffs_per_event` | `20` | Global task transfer limit |
| `max_context_turns` | `20` | Context turns retained by persistent Agents |
| `trace_enabled` | `true` | Enable collaboration tracing |
| `model_blacklist` | `[]` | Blocked model list |
| `model_filter_mode` | `blacklist` | Model filter mode (blacklist/whitelist) |
| `allowed_models` | `[]` | Allowed models in whitelist mode |

## 🏗 Architecture

```
Main Agent (depth=0, full)
 └─ spawn_agent() → Sub-Agent (depth=1, safe/medium/full)
     └─ transfer_to_agent() → Sub-Agent executes task
         └─ ❌ Cannot spawn (depth>=1 blocked)
```

- **Nesting Depth**: Main Agent depth=0, sub-Agents depth=1 — no further nesting
- **Permission Inheritance**: Creator permission ≥ target permission (medium can't create full)
- **Tool Isolation**: Sub-Agent tools built in `_build_sub_tools`, spawn/delete auto-removed at depth≥1

## 📋 Available Tools

| Tool | Description |
|------|-------------|
| `spawn_agent` | Create a sub-Agent (main Agent only) |
| `transfer_to_agent` | Transfer task to an existing sub-Agent |
| `list_agents` | List all active sub-Agents |
| `delete_agent` | Destroy a sub-Agent (main Agent only) |
| `clear_agent_context` | Clear sub-Agent conversation history (main Agent only) |
| `show_collaboration_report` | View collaboration tracing report (main Agent only) |
| `get_sub_agent_results` | Query sub-Agent execution history |

## 📝 License

MIT

---
*This introduction is written in English.*
