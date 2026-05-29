# 🐾 Dynamic SubAgent — Русский

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

Плагин AstrBot, позволяющий основному ИИ-агенту динамически создавать и управлять подагентами, с **изоляцией прав доступа** и **ограничением глубины вложенности** для безопасной мультиагентной системы.

## ✨ Возможности

| Возможность | Описание |
|-------------|----------|
| 🧠 Динамическое создание | `spawn_agent` создаёт подагентов по запросу с настраиваемыми правами/моделями/персистентностью |
| 🔄 Передача задач | `transfer_to_agent` делегирует задачи существующим подагентам |
| 🔒 Изоляция прав | Три уровня: `safe` / `medium` / `full` — подагенты не могут повышать уровень |
| 🛡 Ограничение глубины | Подагенты не могут создавать других подагентов, предотвращая бесконечные цепочки |
| 💾 Персистентная память | Персистентные агенты сохраняют контекст после перезапусков + инъекция истории |
| 🕥 Трассировка сотрудничества | Полное отслеживание цепочек spawn/transfer и отчёты |

## 📦 Установка

Найдите `dynamic_subagent` в AstrBot Plugin Marketplace или клонируйте вручную:

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 Быстрый старт

```python
# 1. Создание подагента с немедленной задачей
spawn_agent(
    name="code_reviewer",
    description="Ассистент для ревью кода",
    permission_level="medium",
    task="Пожалуйста, проверьте следующий код: ..."
)

# 2. Создание персистентного подагента для последующей передачи задач
spawn_agent(
    name="memory_bot",
    description="Ассистент с памятью, запоминающий разговоры",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="Продолжим нашу предыдущую тему..."
)

# 3. Просмотр отчёта о сотрудничестве
show_collaboration_report()
```

## 📝 Лицензия

MIT

---
*Это введение написано на русском языке.*
