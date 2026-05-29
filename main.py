from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

from astrbot.api.star import Context, Star, register
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.provider import LLMResponse, ProviderRequest

logger = logging.getLogger("astrbot")

# ──────────────────────────────────────────────
# Data models
# ──────────────────────────────────────────────


@dataclass
class SubAgentConfig:
    """单个子 Agent 的完整定义"""

    name: str
    system_prompt: str = ""
    provider_id: str | None = None
    permission_level: str = "safe"  # safe | medium | full
    lifecycle: str = "transient"  # transient | persistent
    tools: list[str] | None = None  # None = 继承主 Agent 工具
    created_at: str = ""
    agent_id: str = ""

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()


@dataclass
class SubAgentStore:
    """持久化的子 Agent 存储格式"""

    agents: dict[str, SubAgentConfig] = field(default_factory=dict)


# ──────────────────────────────────────────────
# Main Plugin
# ──────────────────────────────────────────────


@register(
    name="DynamicSubAgent",
    author="maomaosamaqwq",
    desc="让 AI 可以通过 tool call 动态创建和管理子 Agent",
    version="0.1.0",
    repo="https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent",
)
class DynamicSubAgentPlugin(Star):
    """Dynamic SubAgent 插件 — 让 AI 动态创建和管理子 Agent"""

    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        self._config = config or {}
        self._model_blacklist = set(self._config.get("model_blacklist", []))
        self._model_filter_mode = self._config.get("model_filter_mode", "blacklist")
        self._allowed_models = set(self._config.get("allowed_models", []))

        # 运行时状态: transient agent 存在这里
        self._runtime_agents: dict[str, SubAgentConfig] = {}

        # 持久化存储层 (通过 PluginKVStoreMixin)
        self._persist_key = "dynamic_subagent_store"
        self._store = self._load_store()

    # ──────────────────────────────────────────
    # Persistence helpers
    # ──────────────────────────────────────────

    def _load_store(self) -> SubAgentStore:
        try:
            raw = self.get(self._persist_key)
            if raw:
                data = json.loads(raw)
                agents = {}
                for aid, cfg in data.get("agents", {}).items():
                    agents[aid] = SubAgentConfig(**cfg)
                return SubAgentStore(agents=agents)
        except Exception as e:
            logger.warning(f"Failed to load subagent store: {e}")
        return SubAgentStore()

    def _save_store(self):
        try:
            data = {
                "agents": {
                    aid: asdict(cfg)
                    for aid, cfg in self._store.agents.items()
                }
            }
            self.put(self._persist_key, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to save subagent store: {e}")

    # ──────────────────────────────────────────
    # Model filter
    # ──────────────────────────────────────────

    def _is_model_allowed(self, model_id: str) -> bool:
        """检查模型是否在允许范围内"""
        if self._model_filter_mode == "blacklist":
            return model_id not in self._model_blacklist
        elif self._model_filter_mode == "whitelist":
            return model_id in self._allowed_models
        return True

    # ──────────────────────────────────────────
    # Tools
    # ──────────────────────────────────────────

    @filter.llm_tool(
        name="spawn_agent",
        description="创建一个新的子 Agent。子 Agent 可以独立执行任务。创建后会返回 agent_id 用于后续交互。",
    )
    async def spawn_agent(
        self,
        event: AstrMessageEvent,
        name: str,
        system_prompt: str = "",
        provider_id: str = "",
        permission_level: str = "safe",
        lifecycle: str = "transient",
        tools: list[str] | None = None,
    ):
        """
        创建一个子 Agent。

        Args:
            name(string): 子 Agent 的名称
            system_prompt(string): 系统提示词，定义子 Agent 的角色和行为
            provider_id(string): 使用的模型/Provider ID，为空则使用主 Agent 的模型
            permission_level(string): 权限级别 (safe|medium|full)
            lifecycle(string): 生命周期 (transient|persistent)
            tools(array[string]|null): 可用的工具列表，None 表示继承主 Agent 的工具
        """
        # 验证模型
        if provider_id and not self._is_model_allowed(provider_id):
            return f"模型 `{provider_id}` 当前在{'黑名单' if self._model_filter_mode == 'blacklist' else '白名单过滤'}中，不允许使用。请选择其他模型。"

        cfg = SubAgentConfig(
            name=name,
            system_prompt=system_prompt,
            provider_id=provider_id or None,
            permission_level=permission_level,
            lifecycle=lifecycle,
            tools=tools,
        )

        if lifecycle == "persistent":
            self._store.agents[cfg.agent_id] = cfg
            self._save_store()
        else:
            self._runtime_agents[cfg.agent_id] = cfg

        return (
            f"子 Agent `{name}` 创建成功！\n"
            f"agent_id: {cfg.agent_id}\n"
            f"生命周期: {lifecycle}\n"
            f"权限级别: {permission_level}\n"
            f"模型: {provider_id or '继承主 Agent'}\n\n"
            f"可以使用 `send_to_agent(agent_id=\"{cfg.agent_id}\", message=...)` 向该子 Agent 分配任务。"
        )

    @filter.llm_tool(
        name="list_agents",
        description="查看当前所有活跃的子 Agent 列表（包括 transient 和 persistent）",
    )
    async def list_agents(self, event: AstrMessageEvent):
        """列出所有活跃的子 Agent"""
        agents = []
        agents.extend(self._runtime_agents.values())
        agents.extend(self._store.agents.values())

        if not agents:
            return "当前没有任何活跃的子 Agent。"

        lines = ["## 活跃子 Agent 列表\n"]
        for a in agents:
            lines.append(
                f"- **{a.name}** (`{a.agent_id}`)\n"
                f"  - 生命周期: {a.lifecycle} | 权限: {a.permission_level}\n"
                f"  - 模型: {a.provider_id or '继承主 Agent'}\n"
                f"  - 创建于: {a.created_at}\n"
            )
        return "\n".join(lines)

    @filter.llm_tool(
        name="send_to_agent",
        description="向指定的子 Agent 发送消息/分配任务",
    )
    async def send_to_agent(
        self,
        event: AstrMessageEvent,
        agent_id: str,
        message: str,
    ):
        """
        向子 Agent 发送消息。

        Args:
            agent_id(string): 子 Agent 的 ID
            message(string): 要发送的消息/任务描述
        """
        cfg = self._runtime_agents.get(agent_id) or self._store.agents.get(agent_id)
        if not cfg:
            return f"未找到 agent_id `{agent_id}` 对应的子 Agent，请先创建或检查 ID。"
        return (
            f"已将任务分配给子 Agent `{cfg.name}`。\n"
            f"子 Agent 的系统提示:\n{cfg.system_prompt}\n\n"
            f"你的消息:\n{message}\n\n"
            f"（子 Agent 执行完成后会返回结果）"
        )

    @filter.llm_tool(
        name="delete_agent",
        description="销毁一个子 Agent，释放资源",
    )
    async def delete_agent(
        self,
        event: AstrMessageEvent,
        agent_id: str,
    ):
        """
        销毁子 Agent。

        Args:
            agent_id(string): 要销毁的子 Agent ID
        """
        if agent_id in self._runtime_agents:
            name = self._runtime_agents[agent_id].name
            del self._runtime_agents[agent_id]
            return f"子 Agent `{name}` (`{agent_id}`) 已销毁。"

        if agent_id in self._store.agents:
            name = self._store.agents[agent_id].name
            del self._store.agents[agent_id]
            self._save_store()
            return f"持久化子 Agent `{name}` (`{agent_id}`) 已销毁。"

        return f"未找到 agent_id `{agent_id}` 对应的子 Agent。"

    # ──────────────────────────────────────────
    # Lifecycle hooks
    # ──────────────────────────────────────────

    async def terminate(self):
        """插件卸载时清理 transient agent"""
        self._runtime_agents.clear()
        logger.info("DynamicSubAgent: cleaned up transient agents")
