from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.agent.tool import ToolSet
from astrbot import logger

# ── Data Models ──────────────────────────

@dataclass
class SubAgentConfig:
    id: str
    name: str
    description: str = ""
    instruction: str = ""
    permission_level: str = "safe"
    provider_id: str = ""
    model: str = ""
    created_at: float = 0.0
    updated_at: float = 0.0

@dataclass
class SubAgentStore:
    agents: dict = field(default_factory=dict)

# ── Constants ──

_VALID_PERMISSIONS = {"safe", "medium", "full"}

# safe 权限允许的工具白名单
_SAFE_TOOLS = frozenset({
    "astrbot_web_search", "brave_web_search", "tavily_web_search", "bocha_web_search",
    "spawn_agent", "list_agents", "get_sub_agent_results",
})

# medium 权限排除的工具黑名单
_MEDIUM_BLOCKED = frozenset({
    "astrbot_execute_shell",
    "astrbot_execute_ipython",
    "astrbot_execute_python",
})


@register(name="dynamic_subagent", desc="让 AI 动态创建和管理子 Agent", author="maomaosamaqwq", version="0.6.2")
class DynamicSubAgentPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self._cfg = config or {}

        # 从配置读取参数，带默认值
        self._max_spawn: int = int(self._cfg.get("max_spawns_per_event", 10))
        self._max_handoffs: int = int(self._cfg.get("max_handoffs_per_event", 20))
        self._max_context_turns: int = int(self._cfg.get("max_context_turns", 20))
        self._trace_enabled: bool = bool(self._cfg.get("trace_enabled", True))
        self._model_blacklist: list[str] = self._cfg.get("model_blacklist", [])
        self._model_filter_mode: str = self._cfg.get("model_filter_mode", "blacklist")
        self._allowed_models: list[str] = self._cfg.get("allowed_models", [])

        self._store = SubAgentStore()
        self._spawned_ids: set[str] = set()
        self._traces: dict[str, list[dict]] = {}
        self._sub_results: dict[str, list[dict]] = {}
        self._agent_contexts: dict[str, list[dict]] = {}

        self._load_store()

    # ── Lifecycle ──

    async def initialize(self):
        logger.info("DynamicSubAgent v0.6.2 已初始化")

    async def terminate(self):
        self._save_all_contexts()
        logger.info("DynamicSubAgent 已停止")

    # ── Persistence ──

    def _store_path(self) -> str:
        d = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "subagent_store.json")

    def _context_path(self) -> str:
        d = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "subagent_contexts.json")

    def _load_store(self):
        try:
            p = self._store_path()
            if os.path.exists(p):
                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                agents = {}
                for aid, cfg in data.get("agents", {}).items():
                    agents[aid] = SubAgentConfig(**cfg)
                self._store = SubAgentStore(agents=agents)
        except Exception as e:
            logger.warning(f"DynamicSubAgent: 加载持久化失败: {e}")

        try:
            cp = self._context_path()
            if os.path.exists(cp):
                with open(cp, "r", encoding="utf-8") as f:
                    self._agent_contexts = json.load(f)
                logger.info(f"DynamicSubAgent: 已加载 {len(self._agent_contexts)} 个 Agent 上下文")
        except Exception as e:
            logger.warning(f"DynamicSubAgent: 加载上下文失败: {e}")

    def _save_store(self):
        try:
            data = {"agents": {aid: asdict(cfg) for aid, cfg in self._store.agents.items()}}
            with open(self._store_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"DynamicSubAgent: 保存持久化失败: {e}")

    def _save_context(self, agent_id: str):
        """保存单个 Agent 的上下文到文件（增量写入）"""
        try:
            cp = self._context_path()
            existing = {}
            if os.path.exists(cp):
                with open(cp, "r", encoding="utf-8") as f:
                    existing = json.load(f)
            if agent_id in self._agent_contexts:
                existing[agent_id] = self._agent_contexts[agent_id]
            else:
                existing.pop(agent_id, None)
            with open(cp, "w", encoding="utf-8") as f:
                json.dump(existing, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"DynamicSubAgent: 保存上下文失败: {e}")

    def _save_all_contexts(self):
        try:
            with open(self._context_path(), "w", encoding="utf-8") as f:
                json.dump(self._agent_contexts, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"DynamicSubAgent: 保存全部上下文失败: {e}")

    # ── Helpers ──

    def _find_agent_by_name(self, name: str) -> str | None:
        for aid, cfg in self._store.agents.items():
            if cfg.name == name:
                return aid
        return None

    def _check_model_allowed(self, model: str) -> bool:
        """检查模型是否被允许使用"""
        if not model:
            return True
        if self._model_filter_mode == "whitelist":
            return model in self._allowed_models
        return model not in self._model_blacklist

    def _trace(self, umo: str, entry: dict):
        """记录追踪（如果启用）"""
        if self._trace_enabled:
            self._traces.setdefault(umo, []).append(entry)

    def _get_caller_permission(self, event: AstrMessageEvent) -> str | None:
        """获取调用者所在工具集的权限级别，优先从 session 状态判断"""
        umo = event.unified_msg_origin
        # 检查是否来自已注册的子 Agent 调用
        for aid, cfg in self._store.agents.items():
            if cfg.name and cfg.name in umo:
                return cfg.permission_level
        # 主 Agent 调用：full 权限
        return "full"

        def _build_sub_tools(self, permission_level: str) -> ToolSet:
        sub_tools = ToolSet()
        full_mgr = self.context.provider_manager.llm_tools
        
        # 调试：打印所有可用工具名（含内置工具）
        plugin_mcp_names = [t.name for t in full_mgr.func_list]
        builtin_tools = full_mgr.iter_builtin_tools()
        builtin_names = [t.name for t in builtin_tools]
        logger.info(f"DynamicSubAgent: 插件/MCP工具 ({len(plugin_mcp_names)}个): {plugin_mcp_names}")
        logger.info(f"DynamicSubAgent: 内置工具 ({len(builtin_names)}个): {builtin_names}")
        
        # 所有人的基础工具：来自 func_list（插件注册 + MCP）
        if permission_level == "safe":
            for t in full_mgr.func_list:
                if t.name in _SAFE_TOOLS:
                    sub_tools.add_tool(t)
        elif permission_level == "medium":
            for t in full_mgr.func_list:
                if t.name not in _MEDIUM_BLOCKED:
                    sub_tools.add_tool(t)
            # medium 追加文件操作类内置工具
            for t in builtin_tools:
                if t.name not in _MEDIUM_BLOCKED:
                    sub_tools.add_tool(t)
        else:
            for t in full_mgr.func_list:
                sub_tools.add_tool(t)
            # full 追加全部内置工具
            for t in builtin_tools:
                sub_tools.add_tool(t)
        
        selected_names = [t.name for t in sub_tools.func_list]
        logger.info(f"DynamicSubAgent: [{permission_level}] 已选工具 ({len(selected_names)}个): {selected_names}")
        
        return sub_tools

    async def _execute_sub_agent(self, event: AstrMessageEvent, cfg: SubAgentConfig, task: str) -> str:
        prov_id = cfg.provider_id or await self.context.get_current_chat_provider_id(
            event.unified_msg_origin
        )
        sub_tools = self._build_sub_tools(cfg.permission_level)

        # 构建 system prompt，注入上下文历史
        system_parts = [
            f"你是子 Agent [{cfg.name}]。",
            f"描述: {cfg.description}",
            f"指令: {cfg.instruction}",
        ]

        ctx_history = self._agent_contexts.get(cfg.id, [])
        if ctx_history:
            history_lines = ["以下是你之前的对话历史，请参考上下文回答："]
            for i, turn in enumerate(ctx_history, 1):
                result_preview = turn['result'][:500] + ("..." if len(turn['result']) > 500 else "")
                history_lines.append(f"[轮次 {i}] 任务: {turn['task']}")
                history_lines.append(f"[轮次 {i}] 结果: {result_preview}")
            system_parts.append("\n".join(history_lines))

        system_parts.append("请根据任务使用合适的工具完成工作。")
        system_prompt = "\n\n".join(system_parts)

        llm_resp = await self.context.tool_loop_agent(
            event=event,
            chat_provider_id=prov_id,
            prompt=task,
            system_prompt=system_prompt,
            tools=sub_tools,
        )
        result_text = llm_resp.completion_text if llm_resp else "(无返回结果)"

        # 保存到上下文历史
        if cfg.id not in self._agent_contexts:
            self._agent_contexts[cfg.id] = []
        self._agent_contexts[cfg.id].append({
            "task": task,
            "result": result_text,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        # 截断过长历史
        if len(self._agent_contexts[cfg.id]) > self._max_context_turns:
            self._agent_contexts[cfg.id] = self._agent_contexts[cfg.id][-self._max_context_turns:]

        # persistent agent 持久化上下文
        if cfg.id in self._store.agents:
            self._save_context(cfg.id)

        return result_text

    # ── LLM Tools ──

    @filter.llm_tool()
    async def spawn_agent(
        self,
        event: AstrMessageEvent,
        name: str = "",
        description: str = "",
        instruction: str = "",
        task: str = "",
        permission_level: str = "safe",
        provider_id: str = "",
        model: str = "",
        persistent: bool = False,
    ):
        """
        动态创建一个子 Agent。

        如果同时传入 task 参数，创建后会自动让子 Agent 执行该任务并返回结果。
        如果不传 task，则仅注册，后续可通过 transfer_to_agent(name="xxx", task="...") 调用。

        persistent=true 时，Agent 的对话历史会跨调用保留。

        Args:
            name(string): 子 Agent 名称（英文/数字/下划线，用作标识）
            description(string): 子 Agent 的功能描述
            instruction(string): 子 Agent 的系统指令/行为约束
            task(string): 交给子 Agent 的任务内容。如果提供，创建后立即执行
            permission_level(string): 权限级别 (safe/medium/full)，默认 safe
            provider_id(string): 使用的 provider ID，不传则继承主 Agent
            model(string): 使用的模型名，不传则继承主 Agent
            persistent(boolean): 是否持久化（跨重启 + 上下文保留），默认 false
        """
        if len(self._spawned_ids) >= self._max_spawn:
            return f"已达到子 Agent 创建上限（{self._max_spawn}），无法创建"

        if not name or not name.isidentifier():
            return "name 必须是合法标识符（英文/数字/下划线，不能以数字开头）"

        if permission_level not in _VALID_PERMISSIONS:
            return "permission_level 必须为 safe/medium/full"

        # 权限越级检查：调用者不能创建比自己权限更高的子 Agent
        caller_perm = self._get_caller_permission(event)
        perm_rank = {"safe": 0, "medium": 1, "full": 2}
        if perm_rank.get(permission_level, 0) > perm_rank.get(caller_perm, 0):
            return f"权限不足：无法创建 {permission_level} 权限的子 Agent（当前权限: {caller_perm}）"

        if self._find_agent_by_name(name):
            return f"已有同名子 Agent [{name}]，请使用不同的名称"

        if isinstance(persistent, str):
            persistent = persistent.lower() in ("true", "1", "yes")

        # 模型过滤
        if model and not self._check_model_allowed(model):
            return f"模型 [{model}] 不在允许范围内（过滤模式: {self._model_filter_mode}）"

        agent_id = uuid.uuid4().hex[:12]
        now = time.time()
        cfg = SubAgentConfig(
            id=agent_id, name=name, description=description,
            instruction=instruction, permission_level=permission_level,
            provider_id=provider_id, model=model,
            created_at=now, updated_at=now,
        )

        self._store.agents[agent_id] = cfg
        self._spawned_ids.add(agent_id)

        if persistent:
            self._save_store()

        self._trace(event.unified_msg_origin, {
            "agent_name": name, "agent_id": agent_id,
            "action": "spawn", "task": task or "(无任务)",
            "status": "created",
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        })

        if task:
            try:
                result_text = await self._execute_sub_agent(event, cfg, task)
                self._traces.get(event.unified_msg_origin, [{}])[-1]["status"] = "completed"
                self._sub_results.setdefault(event.unified_msg_origin, []).append({
                    "agent_name": name, "agent_id": agent_id,
                    "task": task, "result": result_text,
                    "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
                })
                return (
                    f"子 Agent [{name}] 创建并执行任务完成！\n"
                    f"任务: {task}\n"
                    f"结果:\n{result_text}"
                )
            except Exception as e:
                logger.error(f"DynamicSubAgent: 子 Agent [{name}] 执行任务失败: {e}")
                if self._traces.get(event.unified_msg_origin):
                    self._traces[event.unified_msg_origin][-1]["status"] = f"failed: {e}"
                return (
                    f"子 Agent [{name}] 创建成功，但执行任务时出错: {e}\n"
                    f"可通过 transfer_to_agent(name=\"{name}\", task=\"...\") 重新尝试。"
                )

        return (
            f"子 Agent [{name}] 创建成功！\n"
            f"  类型: {'persistent' if persistent else 'transient'}\n"
            f"  权限: {permission_level}\n"
            f"  描述: {description}\n"
            f"调用方式: transfer_to_agent(name=\"{name}\", task=\"你的任务描述\")"
        )

    @filter.llm_tool()
    async def transfer_to_agent(
        self,
        event: AstrMessageEvent,
        name: str = "",
        task: str = "",
    ):
        """
        将任务转交给已创建的子 Agent 执行。

        对于 persistent Agent，会自动注入之前的对话历史作为上下文。

        Args:
            name(string): 子 Agent 名称（需与 spawn_agent 时的 name 一致）
            task(string): 要交给子 Agent 的任务描述，应包含完整上下文和指令
        """
        if not name:
            return "请指定子 Agent 名称（name 参数）"
        if not task:
            return "请提供任务内容（task 参数）"

        aid = self._find_agent_by_name(name)
        if not aid:
            available = [cfg.name for cfg in self._store.agents.values()]
            hint = f"，可用的子 Agent: {available}" if available else "，当前无活跃子 Agent"
            return f"未找到名为 [{name}] 的子 Agent{hint}"

        cfg = self._store.agents[aid]

        self._trace(event.unified_msg_origin, {
            "agent_name": name, "agent_id": cfg.id,
            "action": "transfer", "task": task,
            "status": "running",
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        })

        try:
            result_text = await self._execute_sub_agent(event, cfg, task)

            if self._traces.get(event.unified_msg_origin):
                self._traces[event.unified_msg_origin][-1]["status"] = "completed"
            self._sub_results.setdefault(event.unified_msg_origin, []).append({
                "agent_name": name, "agent_id": cfg.id,
                "task": task, "result": result_text,
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            })

            ctx_count = len(self._agent_contexts.get(cfg.id, []))
            ctx_hint = f"\n（Agent 已有 {ctx_count} 轮历史上下文）" if ctx_count > 1 else ""

            return (
                f"子 Agent [{name}] 执行完成。{ctx_hint}\n"
                f"任务: {task}\n"
                f"结果:\n{result_text}"
            )
        except Exception as e:
            logger.error(f"DynamicSubAgent: transfer_to_agent({name}) 执行失败: {e}")
            if self._traces.get(event.unified_msg_origin):
                self._traces[event.unified_msg_origin][-1]["status"] = f"failed: {e}"
            return f"子 Agent [{name}] 执行任务时出错: {e}"

    @filter.llm_tool()
    async def list_agents(self, event: AstrMessageEvent):
        """列出当前所有活跃的子 Agent 及其状态。"""
        if not self._store.agents:
            return "当前没有活跃的子 Agent"

        lines = ["当前活跃的子 Agent:"]
        for aid, cfg in self._store.agents.items():
            ctx_count = len(self._agent_contexts.get(aid, []))
            ctx_info = f" 历史:{ctx_count}轮" if ctx_count > 0 else ""
            lines.append(
                f"  [{cfg.name}] 权限:{cfg.permission_level}{ctx_info} "
                f"描述:{cfg.description or '无'}"
            )
        lines.append(f"\n总共: {len(self._store.agents)} 个")
        lines.append("\n调用方式: transfer_to_agent(name=\"Agent名称\", task=\"任务描述\")")
        return "\n".join(lines)

    @filter.llm_tool()
    async def delete_agent(
        self,
        event: AstrMessageEvent,
        name: str = "",
    ):
        """
        销毁指定的子 Agent，同时清理其上下文历史。

        Args:
            name(string): 要销毁的子 Agent 名称
        """
        if not name:
            return "请指定要销毁的子 Agent 名称"

        found = self._find_agent_by_name(name)
        if not found:
            return f"未找到名为 [{name}] 的子 Agent"

        self._spawned_ids.discard(found)
        del self._store.agents[found]
        self._agent_contexts.pop(found, None)
        self._save_store()
        self._save_context(found)
        return f"子 Agent [{name}] 已销毁（含上下文清理），创建配额已归还"

    @filter.llm_tool()
    async def clear_agent_context(
        self,
        event: AstrMessageEvent,
        name: str = "",
    ):
        """
        清空指定 Agent 的对话历史（不销毁 Agent 本身）。

        Args:
            name(string): 子 Agent 名称
        """
        if not name:
            return "请指定子 Agent 名称"

        aid = self._find_agent_by_name(name)
        if not aid:
            return f"未找到名为 [{name}] 的子 Agent"

        old_count = len(self._agent_contexts.get(aid, []))
        self._agent_contexts.pop(aid, None)
        self._save_context(aid)
        return f"子 Agent [{name}] 的 {old_count} 轮对话历史已清空"

    @filter.llm_tool()
    async def show_collaboration_report(self, event: AstrMessageEvent):
        """查看当前会话的子 Agent 协作追踪报告。"""
        if not self._trace_enabled:
            return "协作追踪已禁用（配置 trace_enabled=false）"

        umo = event.unified_msg_origin
        traces = self._traces.get(umo, [])

        if not traces:
            return "当前会话无协作记录"

        lines = ["┌─ 子 Agent 协作追踪报告 ─────"]
        for t in traces:
            lines.append(
                f"  ├ [{t.get('agent_name','?')}] "
                f"action: {t.get('action','?')} | "
                f"task: {t.get('task','?')} | "
                f"status: {t.get('status','?')} | "
                f"{t.get('timestamp','?')}"
            )
        lines.append(f"  └─ 总计: {len(traces)} 条")
        return "\n".join(lines)

    @filter.llm_tool()
    async def get_sub_agent_results(
        self,
        event: AstrMessageEvent,
        name: str = "",
        limit: int = 5,
    ):
        """
        查询子 Agent 的历史执行结果。

        Args:
            name(string): 子 Agent 名称，不传则返回所有子 Agent 的结果
            limit(int): 返回最近几条结果，默认 5
        """
        umo = event.unified_msg_origin
        results = self._sub_results.get(umo, [])

        if name:
            results = [r for r in results if r["agent_name"] == name]

        if not results:
            return f"未找到子 Agent {'[' + name + '] ' if name else ''}的执行记录"

        recent = results[-limit:]
        lines = [f"子 Agent {'[' + name + '] ' if name else ''}最近 {len(recent)} 条执行结果:"]
        for r in recent:
            lines.append(
                f"\n  [{r['agent_name']}] {r['timestamp']}\n"
                f"  任务: {r['task']}\n"
                f"  结果: {r['result'][:500]}{'...' if len(r['result']) > 500 else ''}"
            )
        return "\n".join(lines)
