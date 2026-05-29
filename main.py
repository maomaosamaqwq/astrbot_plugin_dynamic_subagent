from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, PluginKVStoreMixin, register
from astrbot.core.agent.agent import Agent
from astrbot.core.agent.handoff import HandoffTool
from astrbot.core.provider.register import llm_tools
from astrbot.core import logger

# ══════════════════════════════════════════════
# Constants (defaults — overridable by config)
# ══════════════════════════════════════════════

_HANDOFF_COUNT_KEY = "_dynamic_subagent_handoff_count"
_AGENT_SPAWN_COUNT_KEY = "_dynamic_subagent_spawn_count"
_TRACE_MAX_LEN = 50  # per unified_msg_origin

_DEFAULT_MAX_HANDOFFS = 20
_DEFAULT_MAX_SPAWNS = 10
_DEFAULT_MAX_DEPTH = 3
_DEFAULT_MAX_PER_EVENT = 5
_DEFAULT_AGENT_TIMEOUT = 120.0

# ══════════════════════════════════════════════
# Data models
# ══════════════════════════════════════════════


@dataclass
class SubAgentConfig:
    """单个子 Agent 的完整定义"""

    name: str
    system_prompt: str = ""
    provider_id: str | None = None
    permission_level: str = "safe"  # safe | medium | full
    lifecycle: str = "transient"  # transient | persistent
    tools: list[str] | None = None  # None = 继承主 Agent 工具
    max_depth: int = _DEFAULT_MAX_DEPTH
    max_per_event: int = _DEFAULT_MAX_PER_EVENT
    timeout: float = _DEFAULT_AGENT_TIMEOUT
    created_at: str = ""
    agent_id: str = ""
    tool_name: str = ""

    def __post_init__(self):
        if not self.agent_id:
            self.agent_id = uuid.uuid4().hex[:12]
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if not self.tool_name:
            self.tool_name = f"transfer_to_{self.name}"

    def validate(self) -> str | None:
        """返回 None 表示有效，返回字符串表示错误信息"""
        import re

        if not self.name or not self.name.strip():
            return "name 不能为空"
        if not re.match(r"^[\w\u4e00-\u9fff\-]+$", self.name):
            return "name 只能包含字母、数字、中文、下划线和连字符"
        if self.permission_level not in ("safe", "medium", "full"):
            return "permission_level 必须是 safe / medium / full"
        if self.lifecycle not in ("transient", "persistent"):
            return "lifecycle 必须是 transient / persistent"
        if self.max_depth < 1 or self.max_depth > 10:
            return "max_depth 必须在 1-10 之间"
        if self.max_per_event < 1 or self.max_per_event > 50:
            return "max_per_event 必须在 1-50 之间"
        if self.timeout < 5 or self.timeout > 600:
            return "timeout 必须在 5-600 秒之间"
        if self.provider_id and len(self.provider_id) > 100:
            return "provider_id 过长"
        if self.system_prompt and len(self.system_prompt) > 4000:
            return "system_prompt 过长（限 4000 字符）"
        return None


@dataclass
class SubAgentStore:
    """持久化的子 Agent 存储格式"""

    agents: dict[str, SubAgentConfig] = field(default_factory=dict)


# ──────────────────────────────────────────────
# Permission level -> tool name filtering
# ──────────────────────────────────────────────

_PERMISSION_TOOLS: dict[str, list[str] | None] = {
    "safe": ["web_search", "send_message_to_user", "fetch_url"],
    "medium": None,
    "full": None,
}


def _resolve_tool_names(cfg: SubAgentConfig) -> list[str] | None:
    """根据 permission_level 和 tools 参数解析最终的工具名列表"""
    if cfg.tools is not None:
        return cfg.tools
    return _PERMISSION_TOOLS.get(cfg.permission_level)


def _build_handoff_tool(cfg: SubAgentConfig) -> HandoffTool:
    """为子 Agent 创建 HandoffTool（无泛型语法，兼容 Python 3.8+）"""
    tool_names = _resolve_tool_names(cfg)

    # 从全局 llm_tools 注册表中查找对应的 FunctionTool
    tool_list = None
    if tool_names is not None:
        tool_list = []
        for name in tool_names:
            ft = llm_tools.get_func(name)
            if ft and ft.active:
                tool_list.append(ft)

    agent = Agent(
        name=cfg.name,
        instructions=cfg.system_prompt,
        tools=tool_list,
    )
    handoff = HandoffTool(
        agent=agent,
        tool_description=f"将任务转交给 {cfg.name} 处理",
    )
    if cfg.provider_id:
        handoff.provider_id = cfg.provider_id

    return handoff


# ──────────────────────────────────────────────
# Trace rendering（纯文本，不依赖图片渲染）
# ──────────────────────────────────────────────


def _format_trace_text(trace: list[dict]) -> str:
    """追踪报告纯文本格式"""
    lines = ["===== Sub-Agent Collaboration Report =====\n"]
    for i, entry in enumerate(trace, 1):
        ts = datetime.fromtimestamp(entry.get("timestamp", 0)).strftime("%H:%M:%S")
        label = "OK" if entry.get("status") == "success" else "ERROR"
        lines.append(
            f"[Step {i}] {ts} | {label}\n"
            f"  Agent: {entry.get('agent_name', '?')}\n"
            f"  Task: {entry.get('task', '')[:200]}\n"
            f"  Response: {entry.get('response', '')[:300]}\n"
        )
    lines.append(f"\nTotal steps: {len(trace)}")
    return "\n".join(lines)


# ══════════════════════════════════════════════
# Main Plugin
# ══════════════════════════════════════════════


@register(
    "DynamicSubAgent",
    "maomaosamaqwq",
    "让 AI 可以通过 tool call 动态创建和管理子 Agent",
    "0.3.0",
    "https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent",
)
class DynamicSubAgentPlugin(Star, PluginKVStoreMixin):
    """Dynamic SubAgent 插件 — 让 AI 动态创建和管理子 Agent"""

    def __init__(self, context: Context, config: dict | None = None):
        super().__init__(context, config)
        self._config = config or {}
        self._model_blacklist = set(self._config.get("model_blacklist", []))
        self._model_filter_mode = self._config.get("model_filter_mode", "blacklist")
        self._allowed_models = set(self._config.get("allowed_models", []))

        # 从配置读取阈值
        self._max_handoffs = int(
            self._config.get("max_handoffs_per_event", _DEFAULT_MAX_HANDOFFS)
        )
        self._max_spawns = int(
            self._config.get("max_spawns_per_event", _DEFAULT_MAX_SPAWNS)
        )
        self._trace_enabled = bool(self._config.get("trace_enabled", True))

        # 运行时状态
        self._runtime_agents: dict[str, SubAgentConfig] = {}
        self._persist_key = "dynamic_subagent_store"
        self._store: SubAgentStore = SubAgentStore()

        # handoff 追踪（按 unified_msg_origin 分桶）
        self._last_traces: dict[str, list[dict]] = {}

    # ── Lifecycle ──────────────────────────────

    async def initialize(self):
        """插件初始化：加载持久化 + 恢复注册 + 清理 + 注册 API"""
        self._store = self._load_store()
        self._restore_persistent_agents()
        self._cleanup_stale_tools()
        self._register_web_apis()
        logger.info(
            "DynamicSubAgent initialized: %d persistent + %d runtime agents, "
            "max_handoffs=%d max_spawns=%d trace=%s",
            len(self._store.agents),
            len(self._runtime_agents),
            self._max_handoffs,
            self._max_spawns,
            self._trace_enabled,
        )

    async def terminate(self):
        """插件卸载时清理所有动态注册的 HandoffTool"""
        for cfg in list(self._runtime_agents.values()):
            self._remove_handoff_tool(cfg.tool_name)
        for cfg in list(self._store.agents.values()):
            self._remove_handoff_tool(cfg.tool_name)
        self._runtime_agents.clear()
        logger.info("DynamicSubAgent: terminated, all handoff tools removed")

    # ── Persistence ────────────────────────────

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
            logger.warning("DynamicSubAgent: failed to load store: %s", e)
        return SubAgentStore()

    def _save_store(self):
        try:
            data = {
                "agents": {aid: asdict(cfg) for aid, cfg in self._store.agents.items()}
            }
            self.put(self._persist_key, json.dumps(data, ensure_ascii=False))
        except Exception as e:
            logger.error("DynamicSubAgent: failed to save store: %s", e)

    # ── HandoffTool management ─────────────────

    def _register_handoff_tool(self, cfg: SubAgentConfig):
        """为子 Agent 创建并注册 HandoffTool"""
        self._remove_handoff_tool(cfg.tool_name)

        handoff = _build_handoff_tool(cfg)
        llm_tools.func_list.append(handoff)
        logger.info(
            "DynamicSubAgent: registered %s (%s) depth=%d timeout=%.0fs",
            cfg.tool_name,
            cfg.name,
            cfg.max_depth,
            cfg.timeout,
        )

    def _remove_handoff_tool(self, tool_name: str):
        for i, f in enumerate(llm_tools.func_list):
            if isinstance(f, HandoffTool) and f.name == tool_name:
                llm_tools.func_list.pop(i)
                return

    def _restore_persistent_agents(self):
        for cfg in self._store.agents.values():
            try:
                self._register_handoff_tool(cfg)
            except Exception as e:
                logger.error("Failed to restore agent %s: %s", cfg.name, e)

    def _cleanup_stale_tools(self):
        valid = {cfg.tool_name for cfg in self._store.agents.values()}
        valid.update(cfg.tool_name for cfg in self._runtime_agents.values())
        i = 0
        while i < len(llm_tools.func_list):
            f = llm_tools.func_list[i]
            if isinstance(f, HandoffTool) and f.name not in valid:
                llm_tools.func_list.pop(i)
            else:
                i += 1

    # ── Model filter ───────────────────────────

    def _is_model_allowed(self, model_id: str) -> bool:
        if not model_id:
            return True
        if self._model_filter_mode == "blacklist":
            return model_id not in self._model_blacklist
        elif self._model_filter_mode == "whitelist":
            return model_id in self._allowed_models
        return True

    # ── Security: handoff circuit breaker ──────

    @filter.on_llm_request()
    async def _on_llm_request(self, event: AstrMessageEvent, request) -> None:
        """在 LLM 请求前，如果 handoff 熔断触发则移除所有 HandoffTools"""
        if not hasattr(request, "func_tool") or not request.func_tool:
            return

        count = event.get_extra(_HANDOFF_COUNT_KEY, 0)
        if count >= self._max_handoffs:
            tools = getattr(request.func_tool, "tools", None)
            if isinstance(tools, list):
                request.func_tool.tools = [
                    t for t in tools if not isinstance(t, HandoffTool)
                ]
                logger.warning(
                    "DynamicSubAgent: handoff circuit breaker triggered "
                    "(%d/%d), HandoffTools removed",
                    count,
                    self._max_handoffs,
                )

    def _count_handoff(self, event: AstrMessageEvent) -> int:
        """递增 handoff 计数，返回新计数"""
        count = event.get_extra(_HANDOFF_COUNT_KEY, 0) + 1
        event.set_extra(_HANDOFF_COUNT_KEY, count)
        return count

    def _count_spawn(self, event: AstrMessageEvent) -> int:
        """递增 spawn 计数，返回新计数"""
        count = event.get_extra(_AGENT_SPAWN_COUNT_KEY, 0) + 1
        event.set_extra(_AGENT_SPAWN_COUNT_KEY, count)
        return count

    # ── Trace recording ────────────────────────

    def _record_handoff_trace(
        self,
        event: AstrMessageEvent,
        agent_name: str,
        task: str,
        response: str,
        status: str = "success",
    ):
        """记录一次 handoff 调用到追踪列表"""
        if not self._trace_enabled:
            return
        umo = event.unified_msg_origin
        traces = self._last_traces.get(umo, [])
        traces.append(
            {
                "agent_name": str(agent_name)[:100],
                "task": str(task)[:500],
                "response": str(response)[:500],
                "status": status,
                "timestamp": time.time(),
            }
        )
        # 限制单桶大小，防内存泄漏
        if len(traces) > _TRACE_MAX_LEN:
            traces = traces[-_TRACE_MAX_LEN:]
        self._last_traces[umo] = traces

    # ── WebUI API routes ───────────────────────

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
            "max_depth": cfg.max_depth,
            "max_per_event": cfg.max_per_event,
            "timeout": cfg.timeout,
            "registered": registered,
            "created_at": cfg.created_at,
        }

    def _register_web_apis(self):
        """注册 Web API 路由供前端调用"""
        try:
            ctx = getattr(self, "context", None)
            if ctx is None or not hasattr(ctx, "register_web_api"):
                logger.warning("DynamicSubAgent: context.register_web_api not available")
                return

            from quart import request as q_request

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

            async def create_api():
                body = await q_request.get_json(silent=True) or {}
                name = body.get("name", "")
                if not name:
                    return {"status": "error", "message": "名称不能为空"}
                cfg = SubAgentConfig(
                    name=name,
                    system_prompt=body.get("system_prompt", ""),
                    provider_id=body.get("provider_id") or None,
                    permission_level=body.get("permission_level", "safe"),
                    lifecycle=body.get("lifecycle", "transient"),
                    tools=body.get("tools"),
                    max_depth=int(body.get("max_depth", _DEFAULT_MAX_DEPTH)),
                    max_per_event=int(body.get("max_per_event", _DEFAULT_MAX_PER_EVENT)),
                    timeout=float(body.get("timeout", _DEFAULT_AGENT_TIMEOUT)),
                )
                err = cfg.validate()
                if err:
                    return {"status": "error", "message": err}
                if cfg.provider_id and not self._is_model_allowed(cfg.provider_id):
                    return {"status": "error", "message": f"模型 {cfg.provider_id} 被禁止"}
                self._register_handoff_tool(cfg)
                if cfg.lifecycle == "persistent":
                    self._store.agents[cfg.agent_id] = cfg
                    self._save_store()
                else:
                    self._runtime_agents[cfg.agent_id] = cfg
                return {
                    "status": "ok",
                    "data": self._serialize(cfg, True),
                    "message": f"子 Agent {name} 创建成功",
                }

            async def delete_api():
                body = await q_request.get_json(silent=True) or {}
                agent_id = body.get("agent_id", "")
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
                    return {"status": "ok", "message": f"持久化子 Agent {cfg.name} 已销毁"}
                return {"status": "error", "message": "未找到该子 Agent"}

            async def trace_api():
                umo = q_request.args.get("umo", "")
                trace = self._last_traces.get(umo, [])
                return {"status": "ok", "data": trace}

            ctx.register_web_api(
                "/plugin/subagent/list", list_api, ["GET"], "获取子 Agent 列表"
            )
            ctx.register_web_api(
                "/plugin/subagent/create", create_api, ["POST"], "创建子 Agent"
            )
            ctx.register_web_api(
                "/plugin/subagent/delete", delete_api, ["POST"], "删除子 Agent"
            )
            ctx.register_web_api(
                "/plugin/subagent/trace", trace_api, ["GET"], "获取协作追踪记录"
            )
            logger.info("DynamicSubAgent: registered 4 WebUI API routes")
        except Exception as e:
            logger.error("DynamicSubAgent: failed to register WebUI routes: %s", e)

    # ── LLM Tools ──────────────────────────────

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
        max_depth: int = _DEFAULT_MAX_DEPTH,
        max_per_event: int = _DEFAULT_MAX_PER_EVENT,
        timeout: float = _DEFAULT_AGENT_TIMEOUT,
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
            max_depth(int): 该子 Agent 最大 handoff 嵌套深度 (1-10)
            max_per_event(int): 单次对话中该子 Agent 最大创建次数 (1-50)
            timeout(float): 子 Agent 超时时间，秒 (5-600)
        """
        spawn_count = self._count_spawn(event)
        if spawn_count > self._max_spawns:
            return (
                f"[AGENT_ERROR] 本对话中已创建 {spawn_count - 1} 个子 Agent "
                f"(上限: {self._max_spawns})，请使用已有 Agent 或删除不再需要的。"
            )

        cfg = SubAgentConfig(
            name=name,
            system_prompt=system_prompt,
            provider_id=provider_id or None,
            permission_level=permission_level,
            lifecycle=lifecycle,
            tools=tools,
            max_depth=max_depth,
            max_per_event=max_per_event,
            timeout=timeout,
        )

        err = cfg.validate()
        if err:
            return f"[AGENT_ERROR] 参数验证失败: {err}"

        if cfg.provider_id and not self._is_model_allowed(cfg.provider_id):
            return f"模型 `{cfg.provider_id}` 被禁止"

        self._register_handoff_tool(cfg)

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
            f"模型: {provider_id or '继承主 Agent'}\n"
            f"最大嵌套深度: {max_depth}\n"
            f"超时: {timeout}s\n\n"
            f"现在你可以直接调用 `{cfg.tool_name}` 工具将任务转交给该子 Agent 处理。"
        )

    @filter.llm_tool(
        name="list_agents",
        description="查看当前所有活跃的子 Agent 列表（包括 transient 和 persistent）",
    )
    async def list_agents(self, event: AstrMessageEvent):
        """列出所有活跃的子 Agent"""
        agents = list(self._runtime_agents.values()) + list(self._store.agents.values())

        if not agents:
            return "当前没有任何活跃的子 Agent。"

        lines = ["## 活跃子 Agent 列表\n"]
        for a in agents:
            tool_registered = any(
                isinstance(f, HandoffTool) and f.name == a.tool_name
                for f in llm_tools.func_list
            )
            status = "[可用]" if tool_registered else "[未注册]"
            lines.append(
                f"- **{a.name}** (`{a.agent_id}`) {status}\n"
                f"  - 生命周期: {a.lifecycle} | 权限: {a.permission_level}\n"
                f"  - 模型: {a.provider_id or '继承主 Agent'}\n"
                f"  - 嵌套深度: {a.max_depth} | 超时: {a.timeout}s\n"
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
        if agent_id in self._runtime_agents:
            cfg = self._runtime_agents[agent_id]
            self._remove_handoff_tool(cfg.tool_name)
            del self._runtime_agents[agent_id]
            return f"子 Agent `{cfg.name}` (`{agent_id}`) 已销毁，对应的 tool `{cfg.tool_name}` 已移除。"

        if agent_id in self._store.agents:
            cfg = self._store.agents[agent_id]
            self._remove_handoff_tool(cfg.tool_name)
            del self._store.agents[agent_id]
            self._save_store()
            return f"持久化子 Agent `{cfg.name}` (`{agent_id}`) 已销毁，对应的 tool `{cfg.tool_name}` 已移除。"

        return f"未找到 agent_id `{agent_id}` 对应的子 Agent。"

    @filter.llm_tool(
        name="show_collaboration_report",
        description="以文本形式展示当前对话的子 Agent 协作追踪报告。仅在所有 handoff 完成后调用一次。",
    )
    async def show_collaboration_report(self, event: AstrMessageEvent):
        """展示子 Agent 协作追踪报告（纯文本，无图片依赖）"""
        umo = event.unified_msg_origin
        trace = self._last_traces.get(umo, [])
        if not trace:
            return "本次对话中尚无子 Agent 协作记录。"
        return _format_trace_text(trace)
