# 🐾 Dynamic SubAgent — Português

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

Um plugin AstrBot que permite ao agente principal criar e gerenciar dinamicamente sub-agentes, com **isolamento de permissões** e **limites de profundidade de aninhamento** para um sistema multi-agente seguro.

## ✨ Recursos

| Recurso | Descrição |
|---------|-----------|
| 🧠 Criação dinâmica | `spawn_agent` cria sub-agentes sob demanda com permissões/modelos/persistentância configuráveis |
| 🔄 Transferência de tarefas | `transfer_to_agent` delega tarefas a sub-agentes existentes |
| 🔒 Isolamento de permissões | Três níveis: `safe` / `medium` / `full` — sub-agentes não podem escalar |
| 🛡 Limite de profundidade | Sub-agentes não podem criar outros sub-agentes, prevenindo cadeias infinitas |
| 💾 Memória persistente | Agentes persistentes retêm contexto após reinicializações + injeção de histórico |
| 🕥 Rastreamento de colaboração | Rastreamento completo de cadeias spawn/transfer e relatórios |

## 📦 Instalação

Pesquise `dynamic_subagent` no AstrBot Plugin Marketplace, ou clone manualmente:

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 Início rápido

```python
# 1. Criar sub-agente com tarefa imediata
spawn_agent(
    name="code_reviewer",
    description="Assistente de revisão de código",
    permission_level="medium",
    task="Por favor, revise o seguinte código: ..."
)

# 2. Criar sub-agente persistente para transferência posterior
spawn_agent(
    name="memory_bot",
    description="Assistente com memória que lembra conversas",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="Continuemos nosso tópico anterior..."
)

# 3. Ver relatório de colaboração
show_collaboration_report()
```

## 📝 Licença

MIT

---
*Esta introdução está escrita em português.*
