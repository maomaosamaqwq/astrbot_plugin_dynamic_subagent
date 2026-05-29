from __future__ import annotations

import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.provider.register import llm_tools
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


@register(name="dynamic_subagent", desc="让 AI 动态创建和管理子 Agent", author="maomaosamaqwq", version="0.5.2")
class DynamicSubAgentPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self._ctx = context
        self._cfg = config or {}
        self._store = SubAgentStore()
        self._spawn_count = 0
        self._traces: dict[str, list[dict]] = {}

        self._load_store()
        self._restore_agents()

    # ── Lifecycle ──

    async def initialize(self):
        logger.info("DynamicSubAgent v0.5.2 已初始化")

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

    def _restore_agents(self):
        """启动时恢复 persistent agent 的 tool 注册"""
        restored = 0
        for aid, cfg in list(self._store.agents.items()):
            self._register_handoff_tool(cfg)
            restored += 1
        if restored:
            logger.info(f"DynamicSubAgent: 已恢复 {restored} 个持久化子 Agent")

    # ── Handoff Tool Registration ──

    def _register_handoff_tool(self, cfg: SubAgentConfig):
        tool_name = f"transfer_to_{cfg.name}"
        # 通过 self.context 注册工具，确保 handler_module_path 被正确设置
        tool_mgr = self.context.provider_manager.llm_tools
        tool_mgr.add_func(
            tool_name,
            [
                {"name": "task", "type": "string",
                 "description": f"交给子 Agent [{cfg.name}] 的任务描述，应包含完整的上下文和指令。"},
            ],
            f"将任务转交给子 Agent [{cfg.name}] 处理。{cfg.description or '无描述'}",
            self._make_handoff_handler(cfg),
        )
        # 给工具打上 handler_module_path 标记，确保插件工具可见性判断通过
        tool = tool_mgr.get_func(tool_name)
        if tool:
            # AstrBot add_llm_tools 会从 __module__ 提取 "plugins.<name>.main" 格式
            # 我们的闭包 handler.__module__ 是 __name__（即 "main"），解析不对
            # 直接设为 self.__module__，让 add_llm_tools 的逻辑能正确匹配到插件
            tool.handler_module_path = __name__

    def _unregister_handoff_tool(self, name: str):
        tool_mgr = self.context.provider_manager.llm_tools
        tool_mgr.remove_func(f"transfer_to_{name}")

    def _make_handoff_handler(self, cfg: SubAgentConfig):
        async def handler(task: str):
            return (
                f"任务已转交给 [{cfg.name}]。\n"
                f"子 Agent 指令: {cfg.instruction}\n"
                f"任务: {task}\n"
                f"请等待任务完成后返回结果。"
            )
        handler.__name__ = f"handoff_{cfg.name}"
        handler.__module__ = __name__
        return handler

    # ── Helper: 查找 agent ──

    def _find_agent_by_name(self, name: str) -> str | None:
        for aid, cfg in self._store.agents.items():
            if cfg.name == name:
                return aid
        return None

    # ── LLM Tools ──

    @filter.llm_tool()
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
        动态创建一个子 Agent，并注册为 handoff tool。

        如果同时传入 task 参数，创建后会自动让子 Agent 执行该任务并返回结果。
        如果不传 task，则仅注册，可在下一轮对话中通过 transfer_to_{name}
        手动调用。

        建议传 task 一步到位，让子 Agent 创建后立即执行。

        Args:
            name(string): 子 Agent 名称（英文/数字/下划线，用作 handoff tool 命名）
            description(string): 子 Agent 的功能描述
            instruction(string): 子 Agent 的系统指令/行为约束
            task(string): 交给子 Agent 的任务内容。如果提供，创建后立即执行
            permission_level(string): 权限级别 (safe/medium/full)，默认 safe
            provider_id(string): 使用的 provider ID，不传则继承主 Agent
            model(string): 使用的模型名，不传则继承主 Agent
            persistent(boolean): 是否持久化（跨重启），默认 false
        """
        if self._spawn_count >= _MAX_SPAWN:
            return f"已达到子 Agent 创建上限（{_MAX_SPAWN}），无法创建"

        if not name or not name.isidentifier():
            return "name 必须是合法标识符（英文/数字/下划线，不能以数字开头）"

        if permission_level not in _PERMISSION_TOOLS:
            return f"permission_level 必须为 safe/medium/full"

        # name 去重
        if self._find_agent_by_name(name):
            return f"已有同名子 Agent [{name}]，请使用不同的名称"

        # 字符串转布尔（LLM tool 传入的 persistent 可能是 "true"/"false" 字符串）
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

        self._register_handoff_tool(cfg)
        self._store.agents[agent_id] = cfg

        if persistent:
            self._save_store()

        self._spawn_count += 1

        # ── 如果有 task，立即让子 Agent 执行 ──
        if task:
            try:
                # 获取 provider
                prov_id = provider_id or await self.context.get_current_chat_provider_id(
                    event.unified_msg_origin
                )
                
                # 构建子 Agent 的工具集
                sub_tools = ToolSet()
                
                # 获取所有可用工具
                full_mgr = self.context.provider_manager.llm_tools
                if permission_level == "safe":
                    # safe 只加 web search 类
                    for t in full_mgr.func_list:
                        if t.name in ("astrbot_web_search", "brave_web_search", "tavily_web_search", "bocha_web_search"):
                            sub_tools.add_tool(t)
                elif permission_level == "medium":
                    # medium 排除 shell/Python
                    for t in full_mgr.func_list:
                        if t.name not in ("shell_exec", "local_python_exec", "execute_shell", "run_python") and not t.name.startswith("transfer_to_"):
                            sub_tools.add_tool(t)
                else:
                    # full 全量
                    for t in full_mgr.func_list:
                        if not t.name.startswith("transfer_to_"):
                            sub_tools.add_tool(t)
                
                system_prompt = (
                    f"你是子 Agent [{name}]。\n"
                    f"描述: {description}\n"
                    f"指令: {instruction}\n"
                    f"请根据任务使用合适的工具完成工作。"
                )
                
                llm_resp = await self.context.tool_loop_agent(
                    event=event,
                    chat_provider_id=prov_id,
                    prompt=task,
                    system_prompt=system_prompt,
                    tools=sub_tools,
                )
                result_text = llm_resp.completion_text if llm_resp else "(无返回结果)"
                
                return (
                    f"子 Agent [{name}] 创建并执行任务完成！\n"
                    f"任务: {task}\n"
                    f"结果:\n{result_text}"
                )
            except Exception as e:
                logger.error(f"DynamicSubAgent: 子 Agent [{name}] 执行任务失败: {e}")
                return (
                    f"子 Agent [{name}] 创建成功，但执行任务时出错: {e}\n"
                    f"可通过 transfer_to_{name} 重新尝试。"
                )

        return (
            f"子 Agent [{name}] 创建成功！\n"
            f"  类型: {'persistent' if persistent else 'transient'}\n"
            f"  权限: {permission_level}\n"
            f"  描述: {description}\n"
            f"  handoff tool: transfer_to_{name}\n"
            f"创建已完成。请告知用户子 Agent 已就绪，用户在下一轮消息中可使用 transfer_to_{name} 来调用它。"
        )

    @filter.llm_tool()
    async def list_agents(self, event: AstrMessageEvent):
        """列出当前所有活跃的子 Agent 及其状态。"""
        if not self._store.agents:
            return "当前没有活跃的子 Agent"

        tool_mgr = self.context.provider_manager.llm_tools
        lines = ["当前活跃的子 Agent:"]
        for aid, cfg in self._store.agents.items():
            registered = any(
                t.name == f"transfer_to_{cfg.name}" for t in tool_mgr.func_list
            )
            status_mark = "[可用]" if registered else "[未注册]"
            lines.append(
                f"  [{cfg.name}] 权限:{cfg.permission_level} "
                f"{status_mark}"
            )
        lines.append(f"\n总共: {len(self._store.agents)} 个")
        return "\n".join(lines)

    @filter.llm_tool()
    async def delete_agent(
        self,
        event: AstrMessageEvent,
        name: str = "",
    ):
        """
        销毁指定的子 Agent，同时注销其 handoff tool。

        Args:
            name(string): 要销毁的子 Agent 名称
        """
        if not name:
            return "请指定要销毁的子 Agent 名称"

        found = self._find_agent_by_name(name)
        if not found:
            return f"未找到名为 [{name}] 的子 Agent"

        del self._store.agents[found]
        self._unregister_handoff_tool(name)
        self._save_store()
        return f"子 Agent [{name}] 已销毁并注销 handoff tool"

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
                f"task: {t.get('task','?')} | "
                f"status: {t.get('status','?')} | "
                f"{t.get('timestamp','?')}"
            )
        lines.append(f"  └─ 总计: {len(traces)} 条")
        return "\n".join(lines)
