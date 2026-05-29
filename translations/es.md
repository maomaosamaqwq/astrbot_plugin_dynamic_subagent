# 🐾 Dynamic SubAgent — Español

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

Un plugin de AstrBot que permite al agente principal crear y gestionar dinámicamente sub-agentes, con **aislamiento de permisos** y **límites de profundidad de anidamiento** para un sistema multi-agente seguro.

## ✨ Características

| Característica | Descripción |
|----------------|-------------|
| 🧠 Creación dinámica | `spawn_agent` crea sub-agentes bajo demanda con permisos/modelos/persistentancia configurables |
| 🔄 Transferencia de tareas | `transfer_to_agent` delega tareas a sub-agentes existentes |
| 🔒 Aislamiento de permisos | Tres niveles: `safe` / `medium` / `full` — los sub-agentes no pueden escalar |
| 🛡 Límite de profundidad | Los sub-agentes no pueden crear más sub-agentes, previniendo cadenas infinitas |
| 💾 Memoria persistente | Los agentes persistentes retienen contexto tras reinicios + inyección de historial |
| 🕥 Trazado de colaboración | Seguimiento completo de cadenas spawn/transfer e informes |

## ⚙️ Sistema de permisos

| Nivel | Herramientas integradas | Herramientas plugin | Puede spawn | Descripción |
|:-----:|:-----------------------:|:-------------------:|:-----------:|-------------|
| `safe` | ❌ | Lista blanca | ❌ | Solo búsqueda + gestión |
| `medium` | Archivo R/W | Lista negra | ❌ | Sin shell/python |
| `full` | ✅ Todas | ✅ Todas | ❌ | Igual que el agente principal |

> Los sub-agentes nunca pueden usar ejecutores de Python/IPython ni crear sub-agentes.

## 📦 Instalación

Busca `dynamic_subagent` en el Marketplace de plugins de AstrBot, o clona manualmente:

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 Inicio rápido

```python
# 1. Crear sub-agente con tarea inmediata
spawn_agent(
    name="code_reviewer",
    description="Asistente de revisión de código",
    permission_level="medium",
    task="Por favor revisa el siguiente código: ..."
)

# 2. Crear sub-agente persistente para transferencia posterior
spawn_agent(
    name="memory_bot",
    description="Asistente con memoria que recuerda conversaciones",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="Continúa nuestro tema anterior..."
)

# 3. Ver informe de colaboración
show_collaboration_report()
```

## 📝 Licencia

MIT

---
*Esta introducción está escrita en español.*
