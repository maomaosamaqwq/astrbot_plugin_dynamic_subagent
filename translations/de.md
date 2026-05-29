# 🐾 Dynamic SubAgent — Deutsch

[![Version](https://img.shields.io/github/v/release/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/releases)
[![Stars](https://img.shields.io/github/stars/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent)
[![License](https://img.shields.io/github/license/maomaosamaqwq/astrbot_plugin_dynamic_subagent)](https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent/blob/master/LICENSE)

Ein AstrBot-Plugin, das es dem Haupt-Agent ermöglicht, dynamisch Unter-Agenten zu erstellen und zu verwalten, mit **Berechtigungsisolierung** und **Verschachtelungstiefenbegrenzungen** für ein sicheres Multi-Agent-System.

## ✨ Funktionen

| Funktion | Beschreibung |
|----------|-------------|
| 🧠 Dynamische Erstellung | `spawn_agent` erstellt Unter-Agenten nach Bedarf mit konfigurierbaren Berechtigungen/Modellen/Persistenz |
| 🔄 Aufgabenübertragung | `transfer_to_agent` delegiert Aufgaben an bestehende Unter-Agenten |
| 🔒 Berechtigungsisolierung | Drei Stufen: `safe` / `medium` / `full` — Unter-Agenten können nicht eskalieren |
| 🛡 Tiefenbegrenzung | Unter-Agenten können keine weiteren Unter-Agenten erstellen, verhindert unendliche Ketten |
| 💾 Persistenter Speicher | Persistente Agenten behalten Kontext nach Neustarts + Verlaufsinjektion |
| 🕥 Kollaborationstracking | Vollständiges spawn/transfer-Ketten-Tracking und Berichte |

## 📦 Installation

Suche `dynamic_subagent` im AstrBot Plugin Marketplace, oder klone manuell:

```bash
git clone https://github.com/maomaosamaqwq/astrbot_plugin_dynamic_subagent.git
```

## 🚀 Schnellstart

```python
# 1. Unter-Agent mit sofortiger Aufgabe erstellen
spawn_agent(
    name="code_reviewer",
    description="Code-Review-Assistent",
    permission_level="medium",
    task="Bitte überprüfen Sie den folgenden Code: ..."
)

# 2. Persistenter Unter-Agent für spätere Aufgabenübertragung
spawn_agent(
    name="memory_bot",
    description="Gedächtnis-Assistent, der sich an Gespräche erinnert",
    persistent=True
)

transfer_to_agent(
    name="memory_bot",
    task="Setzen wir unser vorheriges Thema fort..."
)

# 3. Kollaborationsbericht anzeigen
show_collaboration_report()
```

## 📝 Lizenz

MIT

---
*Diese Einführung ist auf Deutsch verfasst.*
