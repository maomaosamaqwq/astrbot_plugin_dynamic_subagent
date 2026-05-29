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

# ── Permission mapping ──

_PERMISSION_TOOLS = {
    "safe": None,
    "medium": None,
    "full": None,
}

# ── Safety Limits ──

_MAX_SPAWN = 10
_MAX_TRACE = 50


@register(name="dynamic_subagent", desc="让 AI 动态创建和管理子 Agent", author="maomaosamaqwq", version="0.5.6")
class DynamicSubAgentPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self._ctx = context
        self._cfg = config or {}
        self._store = SubAgentStore()
        # Bug #5 fix: 改用 set 记录已创建的 agent id，删除时同步移除
        self._spawned_ids: set[str] = set()
        self._traces: dict[str, list[dict]] = {}
        # Bug #2 fix: 持久化子 Agent 执行结果，供主 Agent 回溯
        self._sub_results: dict[str, list[dict]] = {}

        self._load_store()

    # ── Lifecycle ──

    async def initialize(self):
        logger.info("DynamicSubAgent v0.5.6 已初始化")

    async def terminate(self):
        logger.info("DynamicSubAgent 已停止")

    # ── Persistence ──

    def _store_path(self) -> str:
        d = os.path.join(os.path.dirname(__file__), "data")
        os.makedirs(d, exist_ok=True)
        return os.path.join(d, "subagent_store.json")

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

    def _save_store(self):
        try:
            data = {"agents": {aid: asdict(cfg) for aid, cfg in self._store.agents.items()}}
            with open(self._store_path(), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"DynamicSubAgent: 保存持久化失败: {e}")

    # ── Helper: 查找 agent ──

    def _find_agent_by_name(self, name: str) -> str | None:
        for aid, cfg in self._store.agents.items():
            if cfg.name == name:
                return aid
        return None

    # ── Helper: 构建子 Agent 工具集 ──

    def _build_sub_tools(self, permission_level: str) -> ToolSet:
        sub_tools = ToolSet()
        full_mgr = self.context.provider_manager.llm_tools
        if permission_level == "safe":
            for t in full_mgr.func_list:
                if t.name in ("astrbot_web_search", "brave_web_search", "tavily_web_search", "bocha_web_search", "spawn_agent", "list_agents"):
                    sub_tools.add_tool(t)
        elif permission_level == "medium":
            for t in full_mgr.func_list:
                if t.name not in ("shell_exec", "local_python_exec", "execute_shell", "run_python"):
                    sub_tools.add_tool(t)
        else:
            for t in full_mgr.func_list:
                sub_tools.add_tool(t)
        return sub_tools

    # ── Helper: 执行子 Agent 任务 ──

    async def _execute_sub_agent(self, event: AstrMessageEvent, cfg: SubAgentConfig, task: str) -> str:
        prov_id = cfg.provider_id or await self.context.get_current_chat_provider_id(
            event.unified_msg_origin
        )
        sub_tools = self._build_sub_tools(cfg.permission_level)
        system_prompt = (
            f"你是子 Agent [{cfg.name}]。\n"
            f"描述: {cfg.description}\n"
            f"指令: {cfg.instruction}\n"
            f"请根据任务使用合适的工具完成工作。"
        )
        llm_resp = await self.context.tool_loop_agent(
            event=event,
            chat_provider_id=prov_id,
            prompt=task,
            system_prompt=system_prompt,
            tools=sub_tools,
        )
        return llm_resp.completion_text if llm_resp else "(无返回结果)"

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

        建议传 task 一步到位，让子 Agent 创建后立即执行。

        Args:
            name(string): 子 Agent 名称（英文/数字/下划线，用作标识）
            description(string): 子 Agent 的功能描述
            instruction(string): 子 Agent 的系统指令/行为约束
            task(string): 交给子 Agent 的任务内容。如果提供，创建后立即执行
            permission_level(string): 权限级别 (safe/medium/full)，默认 safe
            provider_id(string): 使用的 provider ID，不传则继承主 Agent
            model(string): 使用的模型名，不传则继承主 Agent
            persistent(boolean): 是否持久化（跨重启），默认 false
        """
        if len(self._spawned_ids) >= _MAX_SPAWN:
            return f"已达到子 Agent 创建上限（{_MAX_SPAWN}），无法创建"

        if not name or not name.isidentifier():
            return "name 必须是合法标识符（英文/数字/下划线，不能以数字开头）"

        if permission_level not in _PERMISSION_TOOLS:
            return "permission_level 必须为 safe/medium/full"

        if self._find_agent_by_name(name):
            return f"已有同名子 Agent [{name}]，请使用不同的名称"

        if isinstance(persistent, str):
            persistent = persistent.lower() in ("true", "1", "yes")

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

        self._traces.setdefault(event.unified_msg_origin, []).append({
            "agent_name": name, "agent_id": agent_id,
            "action": "spawn", "task": task or "(无任务)",
            "status": "created",
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        })

        # ── 如果有 task，立即执行 ──
        if task:
            try:
                result_text = await self._execute_sub_agent(event, cfg, task)
                self._traces[event.unified_msg_origin][-1]["status"] = "completed"

                # 持久化结果
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

        调用前请确保子 Agent 已通过 spawn_agent 创建。

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

        # 追踪
        self._traces.setdefault(event.unified_msg_origin, []).append({
            "agent_name": name, "agent_id": cfg.id,
            "action": "transfer", "task": task,
            "status": "running",
            "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
        })

        try:
            result_text = await self._execute_sub_agent(event, cfg, task)

            # 更新追踪
            self._traces[event.unified_msg_origin][-1]["status"] = "completed"

            # 持久化结果
            self._sub_results.setdefault(event.unified_msg_origin, []).append({
                "agent_name": name, "agent_id": cfg.id,
                "task": task, "result": result_text,
                "timestamp": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            })

            return (
                f"子 Agent [{name}] 执行完成。\n"
                f"任务: {task}\n"
                f"结果:\n{result_text}"
            )
        except Exception as e:
            logger.error(f"DynamicSubAgent: transfer_to_agent({name}) 执行失败: {e}")
            self._traces[event.unified_msg_origin][-1]["status"] = f"failed: {e}"
            return f"子 Agent [{name}] 执行任务时出错: {e}"

    @filter.llm_tool()
    async def list_agents(self, event: AstrMessageEvent):
        """列出当前所有活跃的子 Agent 及其状态。"""
        if not self._store.agents:
            return "当前没有活跃的子 Agent"

        lines = ["当前活跃的子 Agent:"]
        for aid, cfg in self._store.agents.items():
            lines.append(
                f"  [{cfg.name}] 权限:{cfg.permission_level} "
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
        销毁指定的子 Agent。

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
        self._save_store()
        return f"子 Agent [{name}] 已销毁，创建配额已归还"

    @filter.llm_tool()
    async def show_collaboration_report(self, event: AstrMessageEvent):
        """查看当前会话的子 Agent 协作追踪报告。"""
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
