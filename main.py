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
from astrbot.core.agent.agent import Agent
from astrbot.core.agent.handoff import HandoffTool
from astrbot.core.astr_agent_context import AstrAgentContext
from astrbot.core.provider.register import llm_tools
from astrbot.core import logger

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
    tool_name: str = ""  # 注册到 llm_tools 后的 tool 名称，如 transfer_to_xxx

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.tool_name:
            self.tool_name = f"transfer_to_{self.name}"


@dataclass
class SubAgentStore:
    """持久化的子 Agent 存储格式"""

    agents: dict[str, SubAgentConfig] = field(default_factory=dict)


# ──────────────────────────────────────────────
# Helper: map permission_level -> tool access
# ──────────────────────────────────────────────

_PERMISSION_TOOLS: dict[str, list[str] | None] = {
    "safe": ["web_search", "send_message_to_user"],
    "medium": None,  # None = 全部工具
    "full": None,
}


def _check_permission_tools(level: str, tools: list[str] | None) -> list[str] | None:
    """根据权限级别确定子 Agent 可用的工具"""
    if tools is not None:
        return tools
    return _PERMISSION_TOOLS.get(level, None)


# ──────────────────────────────────────────────
# Main Plugin
# ──────────────────────────────────────────────


@register(
    name="DynamicSubAgent",
    author="maomaosamaqwq",
    desc="让 AI 可以通过 tool call 动态创建和管理子 Agent",
    version="0.2.0",
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

        # 启动时恢复持久化的 agent 注册
        self._restore_persistent_agents()
        self._cleanup_stale_tools()

        # 注册 WebUI API 路由
        self._register_web_apis()

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
                    aid: asdict(cfg) for aid, cfg in self._store.agents.items()
                }
            }
            self.put(self._persist_key, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error(f"Failed to save subagent store: {e}")

    # ──────────────────────────────────────────
    # HandoffTool registration
    # ──────────────────────────────────────────

    def _register_handoff_tool(self, cfg: SubAgentConfig):
        """为子 Agent 创建并注册 HandoffTool"""
        tools = _check_permission_tools(cfg.permission_level, cfg.tools)
        agent = Agent[AstrAgentContext](
            name=cfg.name,
            instructions=cfg.system_prompt,
            tools=tools,
        )

        # 如果指定了 provider_id，传给 HandoffTool
        handoff = HandoffTool(
            agent=agent,
            tool_description=f"将任务转交给 {cfg.name}（{cfg.permission_level} 权限）处理",
        )
        if cfg.provider_id:
            handoff.provider_id = cfg.provider_id

        # 移除旧的同名 tool（如果有）
        self._remove_handoff_tool(cfg.tool_name)

        # 注册到全局 llm_tools
        llm_tools.func_list.append(handoff)
        logger.info(f"Registered handoff tool: {cfg.tool_name} ({cfg.name})")

    def _remove_handoff_tool(self, tool_name: str):
        """从 llm_tools 中移除 HandoffTool"""
        for i, f in enumerate(llm_tools.func_list):
            if isinstance(f, HandoffTool) and f.name == tool_name:
                llm_tools.func_list.pop(i)
                logger.info(f"Removed handoff tool: {tool_name}")
                return

    def _restore_persistent_agents(self):
        """启动时恢复持久化 agent 的 HandoffTool 注册"""
        for cfg in self._store.agents.values():
            try:
                self._register_handoff_tool(cfg)
            except Exception as e:
                logger.error(f"Failed to restore agent {cfg.name}: {e}")

    def _cleanup_stale_tools(self):
        """清理死掉的 HandoffTool（持久化中已删除但还在列表里的）"""
        valid_tool_names = {cfg.tool_name for cfg in self._store.agents.values()}
        valid_tool_names.update(
            cfg.tool_name for cfg in self._runtime_agents.values()
        )
        i = 0
        while i < len(llm_tools.func_list):
            f = llm_tools.func_list[i]
            if isinstance(f, HandoffTool) and f.name not in valid_tool_names:
                llm_tools.func_list.pop(i)
                logger.info(f"Cleaned up stale handoff tool: {f.name}")
            else:
                i += 1

    # ──────────────────────────────────────────
    # Model filter
    # ──────────────────────────────────────────

    def _is_model_allowed(self, model_id: str) -> bool:
        if self._model_filter_mode == "blacklist":
            return model_id not in self._model_blacklist
        elif self._model_filter_mode == "whitelist":
            return model_id in self._allowed_models
        return True

    # ──────────────────────────────────────────
    # WebUI API routes
    # ──────────────────────────────────────────

    def _serialize(self, cfg: SubAgentConfig, registered: bool = True) -> dict:
        return {
            "agent_id": cfg.agent_id,
            "name": cfg.name,
            "system_prompt": cfg.system_prompt,
            "provider_id": cfg.provider_id,
            "permission_level": cfg.permission_level,
            "lifecycle": cfg.lifecycle,
            "tools": cfg.tools,
            "tool_name": cfg.tool_name,
            "registered": registered,
            "created_at": cfg.created_at,
        }

    def _register_web_apis(self):
        """注册 Web API 路由供前端调用"""
        try:
            ctx = getattr(self, "context", None)
            if ctx is None or not hasattr(ctx, "register_web_api"):
                return

            # GET /plugin/subagent/list
            async def list_api():
                agents = []
                for cfg in self._runtime_agents.values():
                    agents.append(self._serialize(cfg, True))
                for cfg in self._store.agents.values():
                    registered = any(
                        isinstance(f, HandoffTool) and f.name == cfg.tool_name
                        for f in llm_tools.func_list
                    )
                    agents.append(self._serialize(cfg, registered))
                return {"status": "ok", "data": agents}

            # POST /plugin/subagent/create
            async def create_api(
                name: str = "",
                system_prompt: str = "",
                provider_id: str = "",
                permission_level: str = "safe",
                lifecycle: str = "transient",
                tools: list[str] | None = None,
            ):
                if not name:
                    return {"status": "error", "message": "名称不能为空"}
                if provider_id and not self._is_model_allowed(provider_id):
                    return {
                        "status": "error",
                        "message": f"模型 {provider_id} 被禁止",
                    }
                cfg = SubAgentConfig(
                    name=name,
                    system_prompt=system_prompt,
                    provider_id=provider_id or None,
                    permission_level=permission_level,
                    lifecycle=lifecycle,
                    tools=tools,
                )
                self._register_handoff_tool(cfg)
                if lifecycle == "persistent":
                    self._store.agents[cfg.agent_id] = cfg
                    self._save_store()
                else:
                    self._runtime_agents[cfg.agent_id] = cfg
                return {
                    "status": "ok",
                    "data": self._serialize(cfg, True),
                    "message": f"子 Agent {name} 创建成功",
                }

            # POST /plugin/subagent/delete
            async def delete_api(agent_id: str = ""):
                if not agent_id:
                    return {"status": "error", "message": "agent_id 不能为空"}
                if agent_id in self._runtime_agents:
                    cfg = self._runtime_agents[agent_id]
                    self._remove_handoff_tool(cfg.tool_name)
                    del self._runtime_agents[agent_id]
                    return {"status": "ok", "message": f"子 Agent {cfg.name} 已销毁"}
                if agent_id in self._store.agents:
                    cfg = self._store.agents[agent_id]
                    self._remove_handoff_tool(cfg.tool_name)
                    del self._store.agents[agent_id]
                    self._save_store()
                    return {
                        "status": "ok",
                        "message": f"持久化子 Agent {cfg.name} 已销毁",
                    }
                return {"status": "error", "message": "未找到该子 Agent"}

            ctx.register_web_api(
                "/plugin/subagent/list", list_api, ["GET"], "获取子 Agent 列表"
            )
            ctx.register_web_api(
                "/plugin/subagent/create",
                create_api,
                ["POST"],
                "创建子 Agent",
            )
            ctx.register_web_api(
                "/plugin/subagent/delete",
                delete_api,
                ["POST"],
                "删除子 Agent",
            )
            logger.info("DynamicSubAgent: registered 3 WebUI API routes")
        except Exception as e:
            logger.error(f"DynamicSubAgent: failed to register WebUI routes: {e}")

    # ──────────────────────────────────────────
    # AI Tools
    # ──────────────────────────────────────────

    @filter.llm_tool(
        name="spawn_agent",
        description="创建一个新的子 Agent。子 Agent 创建后会立即注册为可调用的 tool，主 AI 可以通过 transfer_to_<name> 转交任务给它。",
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

        # 注册 HandoffTool
        self._register_handoff_tool(cfg)

        # 存储
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
            f"现在你可以直接调用 `{cfg.tool_name}` 工具将任务转交给该子 Agent 处理。"
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
            # 检查 tool 是否真正注册了
            tool_registered = any(
                isinstance(f, HandoffTool) and f.name == a.tool_name
                for f in llm_tools.func_list
            )
            status = "🟢 可用" if tool_registered else "🔴 未注册"
            lines.append(
                f"- **{a.name}** (`{a.agent_id}`) {status}\n"
                f"  - 生命周期: {a.lifecycle} | 权限: {a.permission_level}\n"
                f"  - 模型: {a.provider_id or '继承主 Agent'}\n"
                f"  - Tool: `{a.tool_name}`\n"
                f"  - 创建于: {a.created_at}\n"
            )
        return "\n".join(lines)

    @filter.llm_tool(
        name="delete_agent",
        description="销毁一个子 Agent，释放资源并从 tool 列表中移除",
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
        # 从 transient 中找
        if agent_id in self._runtime_agents:
            cfg = self._runtime_agents[agent_id]
            self._remove_handoff_tool(cfg.tool_name)
            del self._runtime_agents[agent_id]
            return f"子 Agent `{cfg.name}` (`{agent_id}`) 已销毁，对应的 tool `{cfg.tool_name}` 已移除。"

        # 从 persistent 中找
        if agent_id in self._store.agents:
            cfg = self._store.agents[agent_id]
            self._remove_handoff_tool(cfg.tool_name)
            del self._store.agents[agent_id]
            self._save_store()
            return f"持久化子 Agent `{cfg.name}` (`{agent_id}`) 已销毁，对应的 tool `{cfg.tool_name}` 已移除。"

        return f"未找到 agent_id `{agent_id}` 对应的子 Agent。"

    # ──────────────────────────────────────────
    # Lifecycle hooks
    # ──────────────────────────────────────────

    async def terminate(self):
        """插件卸载时清理所有动态注册的 HandoffTool"""
        for cfg in list(self._runtime_agents.values()):
            self._remove_handoff_tool(cfg.tool_name)
        for cfg in list(self._store.agents.values()):
            self._remove_handoff_tool(cfg.tool_name)
        self._runtime_agents.clear()
        logger.info("DynamicSubAgent: cleaned up all handoff tools and transient agents")
